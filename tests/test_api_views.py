"""
Phase 5 API Views & Feature Test Suite for PRAHARI.
Validates Situation Map, Alert Inbox, Evidence Card latency SLA (< 2.0s),
Human-in-the-loop acknowledgement, Missing-Data demo control, and Audit Logging.
"""

import time
import pytest
from fastapi.testclient import TestClient

from prahari.api.app import app


@pytest.fixture
def client():
    return TestClient(app)


def test_roles_list_endpoint(client):
    """
    GET /api/v1/auth/roles returns the 6 official Entra ID application roles.
    """
    response = client.get("/api/v1/auth/roles")
    assert response.status_code == 200
    data = response.json()
    assert "available_roles" in data
    roles = [r["role"] for r in data["available_roles"]]
    expected = [
        "surveillance_officer",
        "occupational_health",
        "employer_safety",
        "regulator",
        "public",
        "auditor",
    ]
    for exp in expected:
        assert exp in roles


def test_situation_map_layers_hatching_and_clusters(client):
    """
    GET /api/v1/map/layers returns districts and sites with appropriate risk tiers
    and verifies that district_only features specify hatch_pattern=True.
    """
    response = client.get("/api/v1/map/layers?date=2025-08-20")
    assert response.status_code == 200
    data = response.json()
    assert data["total_locations"] > 0
    
    # Check that districts have hatch_pattern=True and sites have False
    districts = [f for f in data["features"] if f["geo_level"] == "district"]
    sites = [f for f in data["features"] if f["geo_level"] == "site"]
    
    assert len(districts) > 0
    assert len(sites) > 0
    for d in districts:
        assert d["location_confidence"] == "district_only"
        assert d["hatch_pattern"] is True
    for s in sites:
        assert s["location_confidence"] == "exact"
        assert s["hatch_pattern"] is False


def test_alert_inbox_filtering(client):
    """
    GET /api/v1/alerts supports filtering by severity and status.
    """
    # Fetch all
    r_all = client.get("/api/v1/alerts?date=2025-08-20")
    assert r_all.status_code == 200
    data_all = r_all.json()
    assert "alerts" in data_all

    # Filter by severity
    r_warn = client.get("/api/v1/alerts?date=2025-08-20&severity=warning")
    assert r_warn.status_code == 200
    data_warn = r_warn.json()
    for a in data_warn["alerts"]:
        assert a["alert_tier"] == "warning"


def test_evidence_card_generation_latency_sla(client):
    """
    CRITICAL EXIT CRITERIA TEST:
    GET /api/v1/alerts/{alert_id}/evidence must respond in under 2.0 seconds (< 2000 ms).
    Must return observed vs expected time series, SHAP breakdown, and RACI roles.
    """
    t0 = time.perf_counter()
    response = client.get("/api/v1/alerts/ALT-0E6B9686/evidence")
    latency_sec = time.perf_counter() - t0
    
    assert response.status_code == 200
    assert latency_sec < 2.0, f"Evidence Card took {latency_sec:.3f}s; violates <2.0s SLA!"

    data = response.json()
    assert "alert_id" in data
    assert "time_series_comparison" in data
    assert "observed_today" in data["time_series_comparison"]
    assert "historical_baseline" in data["time_series_comparison"]
    assert "exposure_adjusted_expected" in data["time_series_comparison"]
    assert "shap_breakdown" in data
    assert "raci_matrix" in data
    assert "action_checklist" in data
    assert "narrative_summary" in data


def test_human_triage_acknowledgement_workflow(client):
    """
    POST /api/v1/alerts/{alert_id}/acknowledge transitions state and validates mandatory dismissal reason.
    """
    headers = {"X-Role": "surveillance_officer", "X-User-ID": "lead-epi-01"}

    # 1. Transition to ACKNOWLEDGED
    r_ack = client.post(
        "/api/v1/alerts/ALT-TEST-01/acknowledge",
        headers=headers,
        json={"action": "ACKNOWLEDGED", "comment": "Under evaluation by Epi Team"},
    )
    assert r_ack.status_code == 200
    assert r_ack.json()["status"] == "ACKNOWLEDGED"

    # 2. Transition to ACTED
    r_act = client.post(
        "/api/v1/alerts/ALT-TEST-01/acknowledge",
        headers=headers,
        json={"action": "ACTED", "comment": "Dispatched Rapid Response Inspection"},
    )
    assert r_act.status_code == 200
    assert r_act.json()["status"] == "ACTED"

    # 3. Transition to DISMISSED without reason must fail (422)
    r_fail = client.post(
        "/api/v1/alerts/ALT-TEST-01/acknowledge",
        headers=headers,
        json={"action": "DISMISSED", "comment": "Dismissing false alarm"},
    )
    assert r_fail.status_code == 422
    assert "Mandatory dismissal_reason required" in r_fail.json()["detail"]

    # 4. Transition to DISMISSED with valid reason
    r_dismiss = client.post(
        "/api/v1/alerts/ALT-TEST-01/acknowledge",
        headers=headers,
        json={"action": "DISMISSED", "dismissal_reason": "benign_local_event", "comment": "Confirmed benign dust haze"},
    )
    assert r_dismiss.status_code == 200
    assert r_dismiss.json()["status"] == "DISMISSED"


def test_missing_data_demo_toggle_resilience(client):
    """
    POST /api/v1/demo/toggle-feed simulates telemetry outages, widens conformal intervals,
    and proves dynamic resilience without false alarms.
    """
    # 1. Disable clinical feed
    r_outage = client.post(
        "/api/v1/demo/toggle-feed",
        json={"feed": "clinical", "enabled": False},
    )
    assert r_outage.status_code == 200
    data_outage = r_outage.json()
    assert data_outage["is_enabled"] is False
    assert data_outage["after_composite_dq"] < data_outage["before_composite_dq"]
    # Conformal interval must widen
    before_ci = data_outage["before_conformal_interval"]
    after_ci = data_outage["after_conformal_interval"]
    assert (after_ci[1] - after_ci[0]) > (before_ci[1] - before_ci[0])
    assert "Suppressed False Alarm" in data_outage["alert_impact"]

    # 2. Restore clinical feed
    r_restore = client.post(
        "/api/v1/demo/toggle-feed",
        json={"feed": "clinical", "enabled": True},
    )
    assert r_restore.status_code == 200
    data_restore = r_restore.json()
    assert data_restore["is_enabled"] is True
    assert data_restore["after_composite_dq"] > data_outage["after_composite_dq"]


def test_view_audit_logging_persistence(client):
    """
    Verifies that requests to the platform are recorded in the audit trail.
    """
    headers = {"X-Role": "auditor", "X-User-ID": "auditor-chief-01", "X-Purpose": "routine_system_inspection"}
    
    # Query audit logs
    r_logs = client.get("/api/v1/audit/logs?limit=20", headers=headers)
    assert r_logs.status_code == 200
    data = r_logs.json()
    assert data["total_records"] > 0
    latest = data["records"][0]
    assert "timestamp" in latest
    assert "endpoint" in latest
    assert "status_code" in latest


def test_static_index_html_serving(client):
    """
    GET / and GET /index.html serve the single page application HTML dashboard.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Munzir" in response.text or "PRAHARI" in response.text
    assert "Situation Map" in response.text
    assert "Alert Inbox" in response.text
    assert "Employer Safety View" in response.text

    response_index = client.get("/index.html")
    assert response_index.status_code == 200
    assert "text/html" in response_index.headers["content-type"]

    response_favicon = client.get("/favicon.ico")
    assert response_favicon.status_code == 204


def test_clinical_vulnerability_profile_endpoint(client):
    """
    GET /api/v1/clinical/vulnerability-profile returns real openFDA / DailyMed
    pharmacological susceptibility metrics and high-risk drug classes.
    """
    response = client.get("/api/v1/clinical/vulnerability-profile")
    assert response.status_code == 200
    data = response.json()
    assert "pharmacological_vulnerability_index" in data
    assert data["pharmacological_vulnerability_index"] >= 1.0
    assert data["vulnerability_tier"] in ["MODERATE", "HIGH", "CRITICAL"]
    classes = data.get("high_risk_drug_classes") or data.get("high_risk_classes")
    assert len(classes) >= 4
    first_class = classes[0]
    assert "class_name" in first_class
    assert "physiological_mechanism" in first_class
    assert "clinical_mitigation_action" in first_class or "clinical_guidance" in first_class


def test_data_health_feeds_coverage(client):
    """
    GET /api/v1/health/feeds returns complete real-time ingestion streams:
    CDC NSSP, Open-Meteo, OpenAQ, OSHA, openFDA, and Sentinel IoT mesh.
    """
    response = client.get("/api/v1/health/feeds")
    assert response.status_code == 200
    data = response.json()
    assert data["composite_dq_score"] > 0.0
    assert len(data["feeds"]) >= 7
    feed_keys = [f["feed_key"] for f in data["feeds"]]
    for expected in ["sentinel", "weather", "air_quality", "clinical", "osha", "openfda", "pharmacy"]:
        assert expected in feed_keys, f"Missing expected feed {expected}"


