"""
Phase 5 Privacy & RBAC Test Suite for PRAHARI.
Validates strict Entra ID role boundaries and tests the essential Phase 5 exit criteria:
"logging in as employer_safety cannot reach district clinical data or any sub-site breakdown (tested)."
"""

import pytest
from fastapi.testclient import TestClient

from prahari.api.app import app
from prahari.api.rbac import EntraRole


@pytest.fixture
def client():
    return TestClient(app)


def test_employer_safety_cannot_reach_district_clinical_data(client):
    """
    CRITICAL EXIT CRITERIA TEST:
    Logging in as employer_safety CANNOT access district clinical syndromic data.
    Must return HTTP 403 Forbidden.
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }
    response = client.get("/api/v1/clinical/syndromic?geo_id=DXB-JA", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert "Access Denied" in data["detail"]
    assert "clinical" in data["detail"].lower()


def test_employer_safety_cannot_reach_other_employer_sites(client):
    """
    CRITICAL EXIT CRITERIA TEST:
    Logging in as employer_safety for SITE-JA-01 CANNOT access SITE-AQ-01.
    Must return HTTP 403 Forbidden.
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }
    # Attempting to query another employer's site
    response = client.get("/api/v1/workplace/site-rates?site_id=SITE-AQ-01", headers=headers)
    assert response.status_code == 403
    data = response.json()
    assert "SITE-JA-01" in data["detail"]
    assert "SITE-AQ-01" in data["detail"]


def test_employer_safety_cannot_reach_district_level_workplace(client):
    """
    Employer safety cannot query district-wide aggregates.
    Must return HTTP 403 Forbidden.
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }
    response = client.get("/api/v1/workplace/site-rates?site_id=DXB-JA", headers=headers)
    assert response.status_code == 403
    assert "cannot access district/regional data" in response.json()["detail"]


def test_employer_safety_prohibits_subsite_breakdowns(client):
    """
    CRITICAL EXIT CRITERIA TEST:
    Any query attempting to break down rates by gang, crew, worker, or demographics
    is strictly rejected to prevent worker re-identification.
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }

    # Prohibited parameters: worker_id, employee_id, subteam, gang_id, shift_id
    prohibited_queries = [
        "gang_id=CREW-04",
        "worker_id=EMP-9821",
        "subteam=Masonry",
        "shift_id=NIGHT-B",
        "nationality=SouthAsian",
    ]

    for q in prohibited_queries:
        param_name = q.split("=")[0]
        response = client.get(f"/api/v1/workplace/site-rates?site_id=SITE-JA-01&{q}", headers=headers)
        assert response.status_code == 403
        data = response.json()
        assert f"Parameter '{param_name}' is strictly forbidden" in data["detail"]
        assert "prevent worker re-identification" in data["detail"]


def test_employer_safety_cannot_inspect_audit_logs(client):
    """
    Audit logs are reserved for oversight roles (auditor, surveillance_officer, regulator).
    employer_safety must be rejected with HTTP 403 Forbidden.
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }
    response = client.get("/api/v1/audit/logs", headers=headers)
    assert response.status_code == 403
    assert "not permitted to inspect security audit logs" in response.json()["detail"]


def test_employer_safety_mandatory_statutory_banner(client):
    """
    Workplace safety rates view must always inject the mandatory statutory non-disciplinary banner:
    'Aggregate data — not for individual employment or disciplinary decisions.'
    """
    headers = {
        "X-Role": "employer_safety",
        "X-User-ID": "site-safety-officer-ja",
        "X-Employer-ID": "SITE-JA-01",
    }
    response = client.get("/api/v1/workplace/site-rates?site_id=SITE-JA-01&date=2025-08-20", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["statutory_banner"] == "Aggregate data — not for individual employment or disciplinary decisions."
    assert data["site_id"] == "SITE-JA-01"
    assert data["workforce_size"] >= 50
    assert data["is_suppressed"] is False
    assert data["absence_rate_per_1000"] is not None


def test_workplace_minimum_group_size_suppression(client):
    """
    If a worksite cohort is small (N < 50), rates must be suppressed.
    """
    from prahari.api.employer_service import EmployerSafetyService
    svc = EmployerSafetyService()
    # Temporarily simulate a tiny sub-site with 25 workers
    svc.sites_by_id["SITE-TINY"] = {
        "id": "SITE-TINY",
        "name": "Small Subcontractor Hut",
        "district_id": "DXB-JA",
        "workforce": 25,
    }

    # Query with surveillance_officer role to bypass site-id matching
    view = svc.get_site_rates("SITE-TINY", target_date="2025-08-20", user=None)
    assert view.is_suppressed is True
    assert view.absence_rate_per_1000 is None
    assert view.heat_incident_rate_per_1000 is None
    assert "violates minimum group size (N >= 50)" in view.suppression_reason


def test_public_role_strips_worksite_identifiers(client):
    """
    Public portal queries receive differential privacy aggregate views only:
    worksites are stripped, and privacy notice is included.
    """
    headers = {"X-Role": "public"}
    response = client.get("/api/v1/map/layers?date=2025-08-20", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["role_view"] == "public"
    assert "Differential Privacy" in data["privacy_notice"]
    for feat in data["features"]:
        assert feat["geo_level"] == "district"
        assert not feat["geo_id"].startswith("SITE-")
        assert feat["hatch_pattern"] is True  # Public sees hatched pattern for district-only estimates


def test_surveillance_officer_full_access(client):
    """
    Surveillance officer has full public health authority:
    can access clinical data, situation map with sites and districts, and audit logs.
    """
    headers = {"X-Role": "surveillance_officer"}
    
    # Clinical access
    r_clin = client.get("/api/v1/clinical/syndromic?geo_id=DXB-JA", headers=headers)
    assert r_clin.status_code == 200
    assert r_clin.json()["access_granted_to"] == "surveillance_officer"

    # Map access
    r_map = client.get("/api/v1/map/layers?date=2025-08-20", headers=headers)
    assert r_map.status_code == 200
    assert len(r_map.json()["features"]) > 10

    # Audit logs
    r_audit = client.get("/api/v1/audit/logs", headers=headers)
    assert r_audit.status_code == 200

