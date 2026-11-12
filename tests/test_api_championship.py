"""
Integration tests for Championship API Endpoints (Phases 14, 15, 16, 17):
Renal Biomarkers, Spatio-Temporal Deconvolution, Municipal Dispatch, and Inception 42 Jais.
"""

import pytest
from fastapi.testclient import TestClient
from prahari.api.app import app

client = TestClient(app)


def test_api_renal_screening_authorized():
    """Verifies that surveillance officer can inspect cohort renal biomarker panels."""
    response = client.get(
        "/api/v1/renal/screening?site_id=SITE-JA-01&cumulative_wbgt_hours=65.0",
        headers={"X-Role": "surveillance_officer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "cohort_summary" in data
    assert "coupling_alert" in data

    summary = data["cohort_summary"]
    assert summary["site_id"] == "SITE-JA-01"
    assert summary["mean_egfr_ml_min"] > 0
    assert summary["pct_dehydrated"] > 0

    alert = data["coupling_alert"]
    assert alert["alert_tier"] in ("Watch", "Warning", "Normal")
    assert alert["estimated_lead_time_days"] >= 10.0


def test_api_renal_screening_public_forbidden():
    """Verifies that public role cannot inspect sensitive clinical laboratory panels."""
    response = client.get(
        "/api/v1/renal/screening?site_id=SITE-JA-01",
        headers={"X-Role": "public"},
    )
    assert response.status_code == 403
    assert "Access Denied" in response.json()["detail"]


def test_api_spatial_deconvolution():
    """Verifies that clinical seeking clusters in residential areas are back-projected."""
    response = client.get(
        "/api/v1/spatial/deconvolve?clinic_district=Muhaisnah&case_count=45&mean_lag_hours=6.5",
        headers={"X-Role": "surveillance_officer"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["primary_source_site_id"] == "SITE-JA-01"
    assert len(data["candidates"]) >= 2
    assert "confidence_ellipse" in data
    assert data["confidence_ellipse"]["semi_major_km"] > 0
    assert "Jebel Ali" in data["explanation"]


def test_api_municipal_dispatch_optimization():
    """Verifies automated municipal cooling fleet and ambulance standby optimization."""
    response = client.get(
        "/api/v1/dispatch/optimize?site_id=SITE-JA-01&workforce_size=1200&predicted_wbgt=33.8&risk_tier=Warning",
        headers={"X-Role": "surveillance_officer"},
    )
    assert response.status_code == 200
    data = response.json()

    assert data["total_cooling_buses"] >= 4
    assert data["total_misting_trailers"] >= 10
    assert data["total_water_tons"] >= 4.0
    assert data["dcas_ambulance_standby"] is True
    assert "fhir_r4_task" in data
    assert data["fhir_r4_task"]["resourceType"] == "Task"
    assert "markdown_brief" in data


def test_api_jais_multilingual_dispatch():
    """Verifies Inception 42 Jais bilingual and multilingual safety dispatch."""
    response = client.get(
        "/api/v1/jais/dispatch?site_id=SITE-JA-01&tier=Warning&wbgt=33.4&calibrated_p=0.833",
        headers={"X-Role": "surveillance_officer"},
    )
    assert response.status_code == 200
    data = response.json()

    assert "Jais-3-0.9B" in data["model_id"]
    assert data["passed_fenced_gate"] is True

    card = data["card"]
    assert "منصة مُنذِر" in card["arabic"]
    assert "MUNZIR EARLY WARNING" in card["english"]
    assert "منذر پیشگی وارننگ" in card["urdu"]
    assert "मुन्ज़िर अर्ली वार्निंग" in card["hindi"]
    assert "ar" in card["audio_scripts"]
    assert "en" in card["audio_scripts"]
    assert "[ACKNOWLEDGE & START 15M BREAK]" in card["whatsapp_preview"]


def test_api_renal_screening_privacy_suppression_under_50():
    """Verifies that small cohort sizes (< 50) trigger automatic privacy suppression."""
    response = client.get(
        "/api/v1/renal/screening?site_id=SITE-JA-01&cohort_size=35",
        headers={"X-Role": "surveillance_officer"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["cohort_summary"]["suppressed"] is True
    assert data["cohort_summary"]["total_screened"] == 35
    assert data["cohort_summary"]["mean_egfr_ml_min"] == 0.0
    assert data["coupling_alert"]["alert_tier"] == "Normal"


def test_api_validation_bounds_rejected():
    """Verifies that invalid or out-of-bound inputs are rejected with 422 Unprocessable Entity."""
    # Negative / zero case count
    res_deconv = client.get(
        "/api/v1/spatial/deconvolve?clinic_district=Muhaisnah&case_count=-5",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res_deconv.status_code == 422

    # Negative workforce
    res_disp = client.get(
        "/api/v1/dispatch/optimize?site_id=SITE-JA-01&workforce_size=0",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res_disp.status_code == 422


def test_api_health_probes():
    """Verifies that universal container and Kubernetes liveness/readiness probes succeed."""
    res_health = client.get("/health")
    assert res_health.status_code == 200
    assert res_health.json()["status"] == "healthy"

    res_healthz = client.get("/healthz")
    assert res_healthz.status_code == 200
    assert res_healthz.json()["status"] == "healthy"


def test_api_index_html_served():
    """Verifies that web application root / serves the single page application HTML."""
    res = client.get("/")
    assert res.status_code == 200
    assert "text/html" in res.headers.get("content-type", "")
    assert "MUNZIR" in res.text


def test_api_live_telemetry_verification():
    """Verifies that the live telemetry provenance probe returns verified atmospheric data."""
    res = client.get("/api/v1/telemetry/live-verify")
    assert res.status_code == 200
    data = res.json()
    assert "status" in data
    assert "telemetry" in data
    assert "audit_seal_sha256" in data
    assert "zero_mock_certificate" in data
    assert data["telemetry"]["live_calculated_wbgt_c"] > 0


def test_api_causal_demix_endpoint():
    """Verifies the Bayesian Causal De-Mixing & Outbreak Attribution endpoint (Phase 26)."""
    res = client.get(
        "/api/v1/detection/causal-demix?site_id=SITE-JA-01&cluster_size=24&custom_wbgt=34.0&cramps=0.8&oliguria=0.9",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res.status_code == 200
    data = res.json()
    assert "dominant_cause" in data
    assert "Hyperthermia" in data["dominant_cause"]
    assert data["dominant_probability"] > 0.50
    assert "tri_agency_raci_matrix" in data
    assert "MOHRE" in data["tri_agency_raci_matrix"]["lead_regulatory_authority"]
    assert len(data["posteriors"]) == 4


def test_api_action_confirm_endpoint():
    """Verifies frontline action confirmation and Lakehouse audit sync (Phase 28)."""
    res = client.post(
        "/api/v1/intercom/action-confirm",
        json={
            "action_type": "shade_break",
            "site_id": "SITE-JA-01",
            "foreman_name": "Tariq Mansoor",
            "affected_workers": 22,
            "notes": "Mandatory 15-minute hydration and shade rest underway in Zone B pavilion",
        },
        headers={"X-Role": "surveillance_officer"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "CONFIRMED"
    assert "confirmation_id" in data
    assert data["action_type"] == "shade_break"
    assert data["compliance_status"] == "COMPLIANT_RESOLUTION_44"
    assert data["thermal_debt_attenuation_kj_m2"] < 0
    assert data["audit_trail_synced"] is True


def test_api_grand_jury_dossier_html():
    """Verifies Grand Jury Technical Evaluation Dossier publication-grade HTML output (Phase 34)."""
    res = client.get("/api/v1/copilot/jury-dossier?format=html")
    assert res.status_code == 200
    assert "text/html" in res.headers["content-type"]
    text = res.text
    assert "Munzir" in text
    assert "Grand Jury Technical Evaluation Dossier" in text
    assert "RUBRIC 1" in text
    assert "ISO 7933:2004" in text
    assert "Bayesian Causal Outbreak De-Mixing" in text
    assert "TRIPOD+AI" in text


def test_api_grand_jury_dossier_json():
    """Verifies Grand Jury Technical Evaluation Dossier structured JSON audit payload (Phase 34)."""
    res = client.get("/api/v1/copilot/jury-dossier?format=json")
    assert res.status_code == 200
    data = res.json()
    assert data["platform"].startswith("Munzir")
    assert "headline_metrics" in data
    assert data["headline_metrics"]["architecture_phases_completed"] == 30
    assert len(data["rubric_mapping"]) == 6
    assert len(data["governance_checklist"]) == 7
    assert data["cryptographic_seal"].startswith("SHA256:")


