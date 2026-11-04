"""
API Integration Tests for PRAHARI Health & Resilience Impact Model Endpoints (Phase 7)
"""

from fastapi.testclient import TestClient
from prahari.api.app import app

client = TestClient(app)


def test_api_get_impact_assumptions():
    """Verify assumptions registry endpoint with traceable citations."""
    response = client.get("/api/v1/impact/assumptions", headers={"X-Role": "surveillance_officer"})
    assert response.status_code == 200
    data = response.json()
    assert "workforce_size" in data
    assert "baseline_heat_illness_rate" in data
    assert "cost_per_lost_workday_aed" in data
    assert data["workforce_size"]["unit"] == "workers"
    assert "MOHRE" in data["workforce_size"]["source"]


def test_api_calculate_resilience_impact_default():
    """Verify default impact calculation via REST API."""
    response = client.post("/api/v1/impact/calculate", headers={"X-Role": "regulator"}, json={})
    assert response.status_code == 200
    data = response.json()

    assert data["is_modelled_estimate"] is True
    assert "MODELLED ESTIMATE" in data["disclaimer"]
    central = data["central_estimate"]
    assert central["lost_workdays_averted"] > 0
    assert central["net_economic_benefit_aed"] > 0
    assert central["benefit_cost_ratio"] > 10.0
    assert central["alert_fatigue_overhead_pct"] < 5.0

    # Check scenarios
    scenarios = data["scenarios"]
    assert scenarios["low_conservative"]["net_economic_benefit_aed"] < scenarios["central_expected"]["net_economic_benefit_aed"]
    assert scenarios["central_expected"]["net_economic_benefit_aed"] < scenarios["high_optimistic"]["net_economic_benefit_aed"]


def test_api_calculate_resilience_impact_custom():
    """Verify custom parameters properly adjust calculations via REST API."""
    payload = {
        "workforce": {
            "workforce_size": 25000,
            "baseline_heat_illness_rate": 0.02,
        },
        "economic": {
            "cost_per_lost_workday_aed": 500.0,
        }
    }
    response = client.post("/api/v1/impact/calculate", headers={"X-Role": "employer_safety"}, json=payload)
    assert response.status_code == 200
    data = response.json()

    central = data["central_estimate"]
    # 25,000 * 0.02 = 500 baseline cases
    assert central["total_baseline_cases"] == 500.0
    assert data["assumptions_audit"]["workforce_size"]["value"] == 25000.0


def test_api_get_impact_sensitivity():
    """Verify 2D sensitivity matrix endpoint."""
    response = client.get("/api/v1/impact/sensitivity", headers={"X-Role": "surveillance_officer"})
    assert response.status_code == 200
    data = response.json()
    assert len(data["lead_time_steps"]) == 6
    assert len(data["preventability_steps"]) == 6
    assert len(data["grid"]) == 6


def test_api_get_district_policy_evidence():
    """Verify privacy-preserving district policy evidence brief endpoint."""
    response = client.get("/api/v1/impact/policy-report?month=July+2024", headers={"X-Role": "regulator"})
    assert response.status_code == 200
    data = response.json()

    assert data["reporting_period"] == "July 2024"
    assert len(data["districts"]) == 4
    for dist in data["districts"]:
        assert dist["data_suppression_applied"] is True
        # Small-cell suppression
        cases = dist["attributable_heat_stress_cases_suppressed"]
        assert cases == 0 or cases > 10

    assert len(data["policy_recommendations"]) >= 3
    assert len(data["statutory_citations"]) >= 4


def test_api_get_policy_report_summary():
    """Verify policy report executive summary endpoint."""
    response = client.get("/api/v1/impact/policy-report/summary", headers={"X-Role": "regulator"})
    assert response.status_code == 200
    data = response.json()
    assert data["total_extreme_heat_hours"] > 0
    assert data["highest_risk_district"] != ""
    assert data["total_preventable_cases_projected"] > 0


def test_api_get_policy_report_markdown():
    """Verify markdown printable brief export endpoint."""
    response = client.get("/api/v1/impact/policy-report/markdown", headers={"X-Role": "regulator"})
    assert response.status_code == 200
    text = response.text
    assert "# PRAHARI Regulatory Policy Evidence Brief" in text
    assert "District Exposure Burden Summary" in text

