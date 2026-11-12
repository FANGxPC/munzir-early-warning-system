"""
Tests for MOHRE Ministerial Policy Studio & Regulatory Counterfactual Engine (Phase 24).
"""

from prahari.whatif.ministerial_studio import (
    MinisterialPolicyParameters,
    MinisterialPolicyStudioEngine,
    PolicySimulationResult,
)


def test_policy_studio_baseline_evaluation():
    """Verifies macroeconomic and clinical projections under baseline UAE Res 44 parameters."""
    engine = MinisterialPolicyStudioEngine(seed=42)

    params = MinisterialPolicyParameters(
        ban_start_hour=12.5,  # 12:30
        ban_end_hour=15.0,    # 15:00
        mandatory_electrolyte_wbgt_threshold=32.0,
        max_rest_shelter_radius_m=250,
        mandatory_biomarker_screening=False,
        target_workforce_cohort=50000,
    )

    res = engine.simulate_policy_counterfactual(params)

    assert res.target_workforce_size == 50000
    assert res.baseline_hospital_admissions > 100
    assert res.simulated_hospital_admissions <= res.baseline_hospital_admissions
    assert res.admissions_avoided >= 0
    assert res.workdays_saved > 0
    assert res.gross_productivity_saved_aed > 0
    assert res.net_economic_benefit_aed > 0
    assert res.benefit_cost_ratio > 1.0
    assert "MOHRE" in res.statutory_amendment_draft


def test_policy_studio_expanded_protection_delta():
    """Verifies that expanding the midday ban and mandating screening amplifies health gains."""
    engine = MinisterialPolicyStudioEngine(seed=42)

    # Standard Policy
    base_params = MinisterialPolicyParameters(
        ban_start_hour=12.5,
        ban_end_hour=15.0,
        mandatory_electrolyte_wbgt_threshold=32.0,
        max_rest_shelter_radius_m=250,
        mandatory_biomarker_screening=False,
        target_workforce_cohort=50000,
    )
    res_base = engine.simulate_policy_counterfactual(base_params)

    # Aggressive Enhanced Protection Policy
    enhanced_params = MinisterialPolicyParameters(
        ban_start_hour=11.5,  # 11:30 (1 hour earlier)
        ban_end_hour=15.5,    # 15:30 (30m later)
        mandatory_electrolyte_wbgt_threshold=30.0,  # Lower threshold
        max_rest_shelter_radius_m=100,  # Shelters within 100m
        mandatory_biomarker_screening=True,  # Active USG dipsticks
        target_workforce_cohort=50000,
    )
    res_enhanced = engine.simulate_policy_counterfactual(enhanced_params)

    # Enhanced protection should avoid significantly more hospitalizations
    assert res_enhanced.admissions_avoided > res_base.admissions_avoided
    assert res_enhanced.admissions_reduction_pct > res_base.admissions_reduction_pct
    assert res_enhanced.admissions_reduction_pct >= 35.0
    assert res_enhanced.workdays_saved > res_base.workdays_saved
    assert res_enhanced.severe_icu_cases_averted > res_base.severe_icu_cases_averted


def test_policy_studio_to_dict_serialization():
    """Verifies JSON serializability for the REST API."""
    engine = MinisterialPolicyStudioEngine(seed=42)
    params = MinisterialPolicyParameters(target_workforce_cohort=25000)
    res = engine.simulate_policy_counterfactual(params)
    data = res.to_dict()

    assert "policy_summary" in data
    assert "epidemiological_outcomes" in data
    assert "macro_financial_aed" in data
    assert data["epidemiological_outcomes"]["admissions_avoided"] > 0
    assert "net_savings_90ci" in data["macro_financial_aed"]
    assert len(data["macro_financial_aed"]["net_savings_90ci"]) == 2
    assert "statutory_amendment_draft" in data

