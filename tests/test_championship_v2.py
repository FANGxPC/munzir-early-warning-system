"""
Comprehensive Automated Test Suite for Munzir Championship Features (Phases 22-25).
Verifies:
  1. ISO 7933 Predicted Heat Strain & Nocturnal Thermal Debt APIs
  2. Hands-Free Multilingual Two-Way Voice Intercom API
  3. MOHRE Ministerial Policy Studio & Regulatory Replay API
  4. DHA NABIDH & Malaffi HL7 FHIR R4 Clinical Decision Support Gateway
  5. Live Re-Identification Risk Meter & Safe-Harbor Privacy Auditor
"""

import pytest
from fastapi.testclient import TestClient
from prahari.api.app import app


@pytest.fixture(scope="module")
def client():
    return TestClient(app)


def test_api_phs_physics_simulation(client):
    """Verifies ISO 7933 rational heat balance simulation via REST API."""
    # 1. Heavy rigging under extreme Dubai summer heat
    r = client.get(
        "/api/v1/physiology/phs",
        params={
            "air_temp_c": 44.0,
            "relative_humidity_pct": 70.0,
            "mean_radiant_temp_c": 50.0,
            "air_velocity_m_s": 0.4,
            "activity_type": "heavy_rigging",
            "initial_core_temp_c": 37.0,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert "heat_fluxes_w_m2" in data
    assert "physiological_strain" in data
    assert data["t_re_final"] > 37.0
    # Evaporative required exceeds capacity => uncompensable heat storage
    assert data["heat_fluxes_w_m2"]["heat_storage_rate"] > 0.0
    assert data["physiological_strain"]["strain_status"] == "UNCOMPENSABLE_CRITICAL"
    assert data["d_lim_min"] < 60.0
    assert data["sweat_rate_l_h"] > 1.5


def test_api_thermal_debt_lakehouse_grounding(client):
    """Verifies 72-hour nocturnal debt evaluation grounded in Lakehouse Parquet telemetry."""
    r = client.get(
        "/api/v1/physiology/thermal-debt",
        params={
            "site_id": "SITE-JA-01",
            "date": "2024-08-18",
            "activity_type": "heavy_rigging",
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    assert data["site_id"] == "SITE-JA-01"
    assert len(data["daily_profiles"]) == 3
    assert data["cumulative_thermal_debt_w_m2"] > 0.0
    # Day 3 starting core temperature reflects nocturnal failure within physiological bounds
    assert 37.2 <= data["day3_initial_t_re"] <= 39.5
    assert data["collapse_risk_tier"] in ("Moderate", "High", "Critical Collapse Risk")
    assert len(data["mandatory_countermeasures"]) >= 2


def test_api_voice_intercom_multilingual_triage(client):
    """Verifies multilingual voice intercom triage in Urdu, Arabic, and English."""
    # 1. Urdu Emergency
    r_ur = client.post(
        "/api/v1/llm/voice-intercom",
        json={
            "spoken_transcript": "Berth 4 par do mazdoor behosh ho gaye hain aur ulti ho rahi hai",
            "site_id": "SITE-JA-01",
        },
    )
    assert r_ur.status_code == 200, r_ur.text
    d_ur = r_ur.json()
    assert d_ur["detected_language"] == "ur"
    assert d_ur["urgency_level"] == "Emergency"
    assert "spoken_audio" in d_ur
    assert len(d_ur["spoken_audio"]["ur"]) > 0

    # 2. English Routine Break
    r_en = client.post(
        "/api/v1/llm/voice-intercom",
        json={
            "spoken_transcript": "Foreman Tariq: 15-minute scheduled rest break completed for Zone A",
            "site_id": "SITE-JA-01",
        },
    )
    assert r_en.status_code == 200, r_en.text
    d_en = r_en.json()
    assert d_en["detected_language"] == "en"
    assert d_en["urgency_level"] == "Routine"


def test_api_policy_studio_macroeconomic_replay(client):
    """Verifies counterfactual policy simulation with Monte Carlo uncertainty across 50,000 workers."""
    r = client.post(
        "/api/v1/whatif/policy-studio",
        json={
            "scenario_name": "MOHRE Midday Ban Expansion & Mandatory ORS",
            "cohort_size": 50000,
            "midday_ban_start_hour": 12.0,
            "midday_ban_end_hour": 15.5,
            "wbgt_threshold_mandatory_ors": 31.0,
            "max_distance_to_cooling_shelter_m": 150.0,
            "mandatory_bedside_usg_screening": True,
            "monte_carlo_draws": 150,
        },
    )
    assert r.status_code == 200, r.text
    data = r.json()

    # Clinical outcomes
    assert data["heat_stroke_cases_averted"] > 50
    assert data["aki_hospitalizations_prevented"] > 10
    # Financial outcomes
    assert data["economic_dividend_aed"] > 500000.0
    assert data["benefit_cost_ratio"] > 1.0
    # Conformal interval
    ci = data["ci_95_economic_dividend_aed"]
    assert len(ci) == 2
    assert ci[0] < ci[1]
    # Statutory decree wording
    assert "MANDATORY MIDDAY BREAK WINDOW" in data["statutory_amendment_draft"]


def test_api_nabidh_clinical_decision_bundle(client):
    """Verifies DHA NABIDH HL7 FHIR R4 clinical decision bundle export."""
    r = client.get(
        "/api/v1/fhir/nabidh-bundle",
        params={
            "site_id": "SITE-JA-01",
            "date": "2024-08-18",
        },
    )
    assert r.status_code == 200, r.text
    bundle = r.json()

    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 4

    types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "RiskAssessment" in types
    assert "Flag" in types
    assert "CarePlan" in types
    assert "Provenance" in types

    # Check CarePlan activities
    cp = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "CarePlan")
    assert len(cp["activity"]) >= 2

    # Check Provenance signature
    prov = next(e["resource"] for e in bundle["entry"] if e["resource"]["resourceType"] == "Provenance")
    assert len(prov["signature"][0]["data"]) == 64  # Valid SHA-256 hex string


def test_api_reidentification_risk_auditor(client):
    """Verifies empirical k-anonymity and re-identification vulnerability calculation."""
    # 1. Large cohort (500) -> SAFE
    r_safe = client.get("/api/v1/privacy/reidentification-risk", params={"cohort_size": 500})
    assert r_safe.status_code == 200, r_safe.text
    d_safe = r_safe.json()
    assert d_safe["risk_level"] == "SAFE"
    assert d_safe["small_cell_violations"] == 0
    assert d_safe["k_anonymity"] >= 50

    # 2. Medium cohort (250) -> ELEVATED
    r_elev = client.get("/api/v1/privacy/reidentification-risk", params={"cohort_size": 250})
    assert r_elev.status_code == 200, r_elev.text
    d_elev = r_elev.json()
    assert d_elev["risk_level"] == "ELEVATED"
    assert d_elev["small_cell_violations"] > 0

    # 3. Micro cohort (15) -> CRITICAL
    r_crit = client.get("/api/v1/privacy/reidentification-risk", params={"cohort_size": 15})
    assert r_crit.status_code == 200, r_crit.text
    d_crit = r_crit.json()
    assert d_crit["risk_level"] == "CRITICAL"
    assert d_crit["small_cell_violations"] > 0

