"""
Tests for Phase 20: Safe-Harbor Worker Protection Shield.
Verifies cryptographic anti-disciplinary boundaries, statutory compliance certificates,
and small-cell suppression under UAE Federal Decree-Law No. 33 of 2021 Article 13.
"""

import pytest
from fastapi.testclient import TestClient
from prahari.api.app import app
from prahari.privacy.safe_harbor import SafeHarborComplianceEngine

client = TestClient(app)


def test_safe_harbor_certificate_generation():
    """Verifies that compliance certificate contains valid SHA-256 seal and statutory citations."""
    engine = SafeHarborComplianceEngine(epsilon=1.0, k_anonymity=50)
    cert = engine.generate_compliance_certificate()

    assert cert.certificate_id.startswith("SHC-UAE-")
    assert cert.status == "ACTIVE_COMPLIANT"
    assert cert.privacy_budget_epsilon == 1.0
    assert cert.small_cell_k_anonymity == 50
    assert len(cert.audit_seal_sha256) == 64  # Valid SHA-256 hex string

    # Verify statutory citations
    articles = [g["article"] for g in cert.statutory_guarantees]
    assert any("Article 13" in a for a in articles)
    assert any("Articles 5 & 14" in a for a in articles)


def test_safe_harbor_blocks_employer_disciplinary_query():
    """Verifies that an employer role attempting individual worker queries is hard-blocked."""
    engine = SafeHarborComplianceEngine()
    result = engine.evaluate_query_authorization(
        role="employer_safety",
        query_type="individual_break_log",
        query_payload={"worker_id": "WRK-DXB-1049", "target_site": "SITE-JA-01"},
    )

    assert result.authorized is False
    assert result.status_code == 403
    assert "Safe-Harbor" in result.reason
    assert "Decree-Law No. 33" in result.statutory_citation
    assert result.audit_log_id.startswith("AUDIT-SHB-")
    assert result.quarantine_token is not None


def test_safe_harbor_enforces_small_cell_suppression():
    """Verifies that cohort sizes below k=50 are rejected to prevent re-identification."""
    engine = SafeHarborComplianceEngine(k_anonymity=50)
    result = engine.evaluate_query_authorization(
        role="surveillance_officer",
        query_type="aggregate_cohort_health",
        query_payload={"cohort_size": 25},
    )

    assert result.authorized is False
    assert result.status_code == 422
    assert "below the mandatory privacy threshold" in result.reason


def test_safe_harbor_allows_authorized_aggregate_query():
    """Verifies that legitimate aggregated surveillance queries pass without hindrance."""
    engine = SafeHarborComplianceEngine(k_anonymity=50)
    result = engine.evaluate_query_authorization(
        role="surveillance_officer",
        query_type="aggregate_district_heat_burden",
        query_payload={"cohort_size": 120, "geo_id": "DXB-JA"},
    )

    assert result.authorized is True
    assert result.status_code == 200
    assert "Authorized" in result.reason


def test_api_safe_harbor_certificate_endpoint():
    """Verifies GET /api/v1/privacy/safe-harbor-certificate returns 200 with valid certificate."""
    resp = client.get("/api/v1/privacy/safe-harbor-certificate")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ACTIVE_COMPLIANT"
    assert "privacy_parameters" in data
    assert data["privacy_parameters"]["individual_disciplinary_access"] == "CRYPTOGRAPHICALLY_BLOCKED"
    assert "audit_seal_sha256" in data


def test_api_test_disciplinary_query_employer_blocked():
    """Verifies POST /api/v1/privacy/test-disciplinary-query triggers HTTP 403 for employer."""
    resp = client.post(
        "/api/v1/privacy/test-disciplinary-query",
        json={"query_type": "individual_break_log", "worker_id": "WRK-9921"},
        headers={"X-Role": "employer_safety"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert data["authorized"] is False
    assert "UAE Federal Decree-Law No. 33" in data["statutory_citation"]
    assert "quarantine_token" in data

