"""
Tests for Phase 14: Occupational Renal Biomarker Surveillance & Sub-Clinical AKI Engine.
"""

import pytest
from prahari.biomarkers.renal_engine import (
    CohortRenalSummary,
    RenalAssessment,
    RenalObservation,
    aggregate_cohort_renal_health,
    assess_renal_observation,
    classify_kdigo_aki,
    compute_ckd_epi_2021_egfr,
    compute_hydration_index,
)
from prahari.detection.l2_renal import evaluate_renal_environmental_coupling


def test_ckd_epi_2021_standard_benchmarks():
    """Verifies CKD-EPI 2021 race-free eGFR formula matches established clinical outputs."""
    # Healthy young adult male: Cr 0.9 mg/dL, Age 30
    egfr_male = compute_ckd_epi_2021_egfr(0.9, 30, is_female=False)
    assert 115.0 <= egfr_male <= 125.0

    # Healthy young adult female: Cr 0.7 mg/dL, Age 30
    egfr_female = compute_ckd_epi_2021_egfr(0.7, 30, is_female=True)
    assert 115.0 <= egfr_female <= 125.0

    # Elevated creatinine male: Cr 2.0 mg/dL, Age 55 -> Should reflect moderate impairment (<45)
    egfr_impaired = compute_ckd_epi_2021_egfr(2.0, 55, is_female=False)
    assert egfr_impaired < 45.0

    # Bounds check
    with pytest.raises(ValueError):
        compute_ckd_epi_2021_egfr(-0.5, 30, is_female=False)
    with pytest.raises(ValueError):
        compute_ckd_epi_2021_egfr(1.0, 15, is_female=False)


def test_kdigo_aki_staging():
    """Verifies KDIGO 2012 staging rules."""
    baseline = 1.0

    # Normal: Cr 1.1 (ratio 1.1x)
    stage, risk = classify_kdigo_aki(1.1, baseline, egfr_ml_min=95.0, urine_specific_gravity=1.015)
    assert stage == 0
    assert risk == "Normal"

    # Stage 1: Cr 1.6 (ratio 1.6x >= 1.5x) or rise >= 0.3
    stage1, risk1 = classify_kdigo_aki(1.6, baseline, egfr_ml_min=65.0, urine_specific_gravity=1.026)
    assert stage1 == 1
    assert risk1 == "Caution"

    # Stage 2: Cr 2.2 (ratio 2.2x >= 2.0x)
    stage2, risk2 = classify_kdigo_aki(2.2, baseline, egfr_ml_min=40.0, urine_specific_gravity=1.028)
    assert stage2 == 2
    assert risk2 == "Warning"

    # Stage 3: Cr 3.2 (ratio 3.2x >= 3.0x) or eGFR < 35
    stage3, risk3 = classify_kdigo_aki(3.2, baseline, egfr_ml_min=25.0, urine_specific_gravity=1.032)
    assert stage3 == 3
    assert risk3 == "Emergency"


def test_hydration_and_azotemia_index():
    """Tests hydration index calculation and dehydration detection."""
    # Well-hydrated: BUN 12, Cr 1.0, USG 1.012 -> H_index = 12 * (0.012/0.02) = 7.2 (<20)
    h_normal = compute_hydration_index(12.0, 1.0, 1.012)
    assert h_normal < 15.0

    # Pre-renal azotemia: BUN 28, Cr 1.0, USG 1.028 -> H_index = 28 * (0.028/0.02) = 39.2 (>20)
    h_dehydrated = compute_hydration_index(28.0, 1.0, 1.028)
    assert h_dehydrated > 20.0


def test_cohort_aggregation_privacy_suppression():
    """Verifies that cohorts under minimum group size (N < 50) are suppressed."""
    small_cohort = [
        RenalObservation(
            worker_cohort_id=f"W-{i}",
            site_id="SITE-JA-01",
            observation_date="2025-08-15",
            serum_creatinine_mg_dl=1.1,
            serum_creatinine_baseline_mg_dl=0.9,
            age=35,
            is_female=False,
            blood_urea_nitrogen_mg_dl=18.0,
            urine_specific_gravity=1.024,
        )
        for i in range(25)  # 25 < 50
    ]

    summary = aggregate_cohort_renal_health(small_cohort, min_cohort_size=50)
    assert summary.suppressed is True
    assert summary.kdigo_stage_1_rate_per_1000 == 0.0


def test_cohort_aggregation_valid():
    """Verifies aggregate metrics on a full cohort (N = 60)."""
    obs_list = []
    for i in range(60):
        # 10 workers have Stage 1 AKI / dehydration
        if i < 10:
            cr = 1.6
            usg = 1.027
        else:
            cr = 0.95
            usg = 1.015
        obs_list.append(
            RenalObservation(
                worker_cohort_id=f"W-{i}",
                site_id="SITE-JA-01",
                observation_date="2025-08-18",
                serum_creatinine_mg_dl=cr,
                serum_creatinine_baseline_mg_dl=0.9,
                age=32,
                is_female=False,
                blood_urea_nitrogen_mg_dl=18.0,
                urine_specific_gravity=usg,
            )
        )

    summary = aggregate_cohort_renal_health(obs_list, min_cohort_size=50)
    assert summary.suppressed is False
    assert summary.total_screened == 60
    assert summary.kdigo_stage_1_rate_per_1000 > 100.0  # ~166.7 per 1,000
    assert summary.pct_dehydrated > 15.0
    assert summary.subclinical_aki_flag is True


def test_l2_renal_environmental_coupling():
    """Verifies coupling of cohort renal summary with cumulative thermal exposure."""
    summary = CohortRenalSummary(
        site_id="SITE-JA-01",
        observation_date="2025-08-18",
        total_screened=120,
        suppressed=False,
        mean_egfr=84.5,
        pct_dehydrated=42.0,
        kdigo_stage_1_rate_per_1000=48.0,
        kdigo_stage_2_3_rate_per_1000=8.0,
        elevated_creatinine_rate_per_1000=55.0,
        mean_hydration_index=22.4,
        subclinical_aki_flag=True,
    )

    alert = evaluate_renal_environmental_coupling(summary, cumulative_wbgt_32_hours_14d=65.0)
    assert alert.alert_tier in ("Watch", "Warning")
    assert alert.estimated_lead_time_days >= 10.0
    assert "electrolyte" in alert.recommended_action.lower()
