"""
Tests for Phase 21: Compound Multi-Hazard Climate-Health Engine.
Verifies non-linear synergistic risk calculations between extreme thermal stress (WBGT)
and airborne particulate dust storms (PM10/PM2.5) using real Lakehouse telemetry.
"""

import pytest
from fastapi.testclient import TestClient
from prahari.api.app import app
from prahari.hazard.compound_engine import CompoundHazardEngine

client = TestClient(app)


def test_synergistic_relative_risk_calculation():
    """Verifies that simultaneous heat and PM10 produce non-linear synergistic risk amplification."""
    engine = CompoundHazardEngine()

    # Case 1: Heat only (WBGT 34°C, PM10 30 µg/m³ baseline)
    rr_h1, rr_p1, syn1, comp1 = engine.compute_synergistic_relative_risk(wbgt=34.0, pm10=30.0)
    assert rr_h1 > 1.4
    assert rr_p1 == 1.0
    assert syn1 == 0.0

    # Case 2: Dust only (WBGT 25°C baseline, PM10 150 µg/m³)
    rr_h2, rr_p2, syn2, comp2 = engine.compute_synergistic_relative_risk(wbgt=25.0, pm10=150.0)
    assert rr_h2 == 1.0
    assert rr_p2 > 1.1
    assert syn2 == 0.0

    # Case 3: Compound Heat + Dust (WBGT 34°C, PM10 150 µg/m³)
    rr_h3, rr_p3, syn3, comp3 = engine.compute_synergistic_relative_risk(wbgt=34.0, pm10=150.0)
    assert syn3 > 0.0
    # Synergistic risk must exceed additive risk: comp3 > 1 + (rr_h3 - 1) + (rr_p3 - 1)
    additive_risk = 1.0 + (rr_h3 - 1.0) + (rr_p3 - 1.0)
    assert comp3 > additive_risk


def test_compound_tier_classification():
    """Verifies assignment of hazard severity tiers."""
    engine = CompoundHazardEngine()

    assert engine.classify_compound_tier(1.1) == "Normal"
    assert engine.classify_compound_tier(1.5) == "Moderate Compound Risk"
    assert engine.classify_compound_tier(2.5) == "High Compound Alert"
    assert engine.classify_compound_tier(4.2) == "Extreme Compound Emergency"


def test_compound_mitigation_directives_contraindications():
    """Verifies that compound events strictly contraindicate unpressurized water misting."""
    engine = CompoundHazardEngine()
    directives, contraindications = engine.generate_mitigation_directives(
        tier="Extreme Compound Emergency",
        wbgt=35.0,
        pm10=140.0,
    )

    assert any("HEPA" in d for d in directives)
    assert any("N95" in d or "FFP2" in d for d in directives)
    assert any("misting" in c.lower() for c in contraindications)


def test_site_compound_hazard_from_lakehouse():
    """Verifies evaluation of real Lakehouse observation on August 18, 2024."""
    engine = CompoundHazardEngine()
    assessment = engine.evaluate_site_compound_hazard(site_id="SITE-JA-01", target_date="2024-08-18")

    assert assessment.geo_id == "SITE-JA-01"
    assert assessment.wbgt_max_c > 35.0
    assert assessment.pm10_ugm3 > 100.0
    assert assessment.compound_relative_risk > 2.0
    assert assessment.pulmonary_thermal_coupling_flag is True


def test_api_compound_assessment_endpoint():
    """Verifies GET /api/v1/hazard/compound-assessment returns 200 with valid structure."""
    resp = client.get(
        "/api/v1/hazard/compound-assessment?site_id=SITE-JA-01&date=2024-08-18",
        headers={"X-Role": "surveillance_officer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["geo_id"] == "SITE-JA-01"
    assert "environmental" in data
    assert "epidemiological_risk" in data
    assert data["epidemiological_risk"]["compound_relative_risk"] > 1.0
    assert "mitigation_directives" in data
    assert len(data["mitigation_directives"]) > 0


def test_api_compound_series_endpoint():
    """Verifies GET /api/v1/hazard/compound-series returns seasonal time series from Lakehouse."""
    resp = client.get(
        "/api/v1/hazard/compound-series?site_id=SITE-JA-01&start_date=2024-06-01&end_date=2024-09-30",
        headers={"X-Role": "surveillance_officer"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["days_count"] > 100
    assert len(data["records"]) > 100
    sample = data["records"][0]
    assert "wbgt_max" in sample
    assert "pm10" in sample
    assert "compound_rr" in sample

