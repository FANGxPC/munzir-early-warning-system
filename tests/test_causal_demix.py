"""
Automated Unit Tests for Bayesian Causal De-Mixing & Multi-Signal Outbreak Attribution Engine (Phase 26).
"""

import pytest
from prahari.detection.causal_engine import (
    BayesianCausalDeMixingEngine,
    CausalDeMixingResult,
    CausalEtiologyPosterior,
)


def test_causal_demix_pure_heat_cluster():
    """Verifies that classic heat stroke symptoms in high WBGT isolate hyperthermia."""
    engine = BayesianCausalDeMixingEngine()

    heat_symptoms = {
        "fever_chills_present": False,
        "vomiting_cluster_post_meal": False,
        "severe_oliguria_dark_urine": True,
        "watery_diarrhea_dominant": False,
        "wheezing_dyspnea_cough": False,
        "muscle_cramps_extremities": True,
    }

    res = engine.evaluate_cluster_cause(
        site_id="SITE-JA-01",
        target_date="2024-08-18",
        cluster_size=14,
        symptoms=heat_symptoms,
        custom_wbgt=34.5,
        custom_pm10=80.0,
    )

    assert "Hyperthermia" in res.dominant_cause
    assert res.dominant_probability > 0.65
    assert res.tri_agency_raci_matrix["lead_regulatory_authority"].startswith("MOHRE")
    assert "Resolution No. 44" in res.tri_agency_raci_matrix["statutory_mandate"]

    # Verify probability normalization
    total_p = sum(p.posterior_probability for p in res.posteriors)
    assert abs(total_p - 1.0) < 1e-3


def test_causal_demix_foodborne_norovirus_cluster():
    """Verifies that explosive post-meal vomiting with fever and diarrhea flags foodborne source."""
    engine = BayesianCausalDeMixingEngine()

    food_symptoms = {
        "fever_chills_present": True,
        "vomiting_cluster_post_meal": True,
        "severe_oliguria_dark_urine": False,
        "watery_diarrhea_dominant": True,
        "wheezing_dyspnea_cough": False,
        "muscle_cramps_extremities": False,
        "canteen_hygiene_incident_flag": True,
    }

    res = engine.evaluate_cluster_cause(
        site_id="SITE-AQ-01",
        target_date="2024-08-18",
        cluster_size=25,
        symptoms=food_symptoms,
        custom_wbgt=29.0,
        custom_pm10=65.0,
    )

    assert "Foodborne" in res.dominant_cause or "Gastroenteritis" in res.dominant_cause
    assert res.dominant_probability > 0.70
    assert "Dubai Municipality" in res.tri_agency_raci_matrix["lead_regulatory_authority"]
    assert "Food Code" in res.tri_agency_raci_matrix["statutory_mandate"]


def test_causal_demix_shamal_dust_toxic_inhalation():
    """Verifies that acute wheezing and dyspnea during high PM10 dust storm flags toxic aerosol."""
    engine = BayesianCausalDeMixingEngine()

    dust_symptoms = {
        "fever_chills_present": False,
        "vomiting_cluster_post_meal": False,
        "severe_oliguria_dark_urine": False,
        "watery_diarrhea_dominant": False,
        "wheezing_dyspnea_cough": True,
        "muscle_cramps_extremities": False,
    }

    res = engine.evaluate_cluster_cause(
        site_id="SITE-DS-01",
        target_date="2024-08-18",
        cluster_size=12,
        symptoms=dust_symptoms,
        custom_wbgt=30.0,
        custom_pm10=220.0,
    )

    assert "Mineral Dust" in res.dominant_cause or "Toxic Aerosol" in res.dominant_cause
    assert res.dominant_probability > 0.60
    assert "Civil Defense" in res.tri_agency_raci_matrix["lead_regulatory_authority"] or "Dubai Municipality" in res.tri_agency_raci_matrix["lead_regulatory_authority"]


def test_causal_demix_co_morbidity_detection():
    """Verifies detection of simultaneous co-morbidities (heat + canteen food poisoning)."""
    engine = BayesianCausalDeMixingEngine()

    co_morbid_symptoms = {
        "fever_chills_present": 0.35,
        "vomiting_cluster_post_meal": 0.60,
        "severe_oliguria_dark_urine": 0.85,
        "watery_diarrhea_dominant": 0.40,
        "wheezing_dyspnea_cough": 0.0,
        "muscle_cramps_extremities": 0.80,
        "canteen_hygiene_incident_flag": True,
    }

    res = engine.evaluate_cluster_cause(
        site_id="SITE-JA-01",
        target_date="2024-08-18",
        cluster_size=30,
        symptoms=co_morbid_symptoms,
        custom_wbgt=34.0,
        custom_pm10=90.0,
    )

    # In a compound scenario, both heat and food are elevated
    assert res.is_multi_causal_co_morbidity is True
    assert len(res.secondary_causes) >= 1
    assert res.tri_agency_raci_matrix["multi_agency_coordination_required"] is True
    assert len(res.action_orders) >= 2


def test_causal_demix_to_dict_and_credible_intervals():
    """Verifies that 90% credible intervals are ordered and to_dict serializes cleanly."""
    engine = BayesianCausalDeMixingEngine()
    res = engine.evaluate_cluster_cause(site_id="SITE-JA-01")
    d = res.to_dict()

    assert "dominant_cause" in d
    assert "dominant_probability" in d
    assert "posteriors" in d
    assert len(d["posteriors"]) == 4

    for p in d["posteriors"]:
        ci = p["credible_interval_90_pct"]
        assert len(ci) == 2
        assert ci[0] <= ci[1]
        assert 0.0 <= ci[0] <= 100.0
        assert 0.0 <= ci[1] <= 100.0

    assert "tri_agency_raci_matrix" in d
    assert "action_orders" in d
