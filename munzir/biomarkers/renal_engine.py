"""
Munzir Occupational Renal Biomarker Surveillance Engine (Phase 14).
Implements sub-clinical Acute Kidney Injury (AKI) detection via CKD-EPI 2021 eGFR,
KDIGO staging, and Urine Specific Gravity (USG) hydration indices.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class RenalObservation:
    """Individual anonymized renal biomarker observation."""
    worker_cohort_id: str
    site_id: str
    observation_date: str
    serum_creatinine_mg_dl: float
    serum_creatinine_baseline_mg_dl: float
    age: int
    is_female: bool
    blood_urea_nitrogen_mg_dl: float
    urine_specific_gravity: float
    work_shift: str = "day"


@dataclass(frozen=True)
class RenalAssessment:
    """Derived clinical assessment of individual renal stress."""
    egfr_ml_min: float
    kdigo_stage: int  # 0, 1, 2, 3
    hydration_index: float
    is_dehydrated: bool
    is_aki: bool
    risk_level: str  # Normal, Caution, Warning, Emergency


@dataclass
class CohortRenalSummary:
    """Privacy-preserving cohort aggregate renal surveillance summary."""
    site_id: str
    observation_date: str
    total_screened: int
    suppressed: bool
    mean_egfr: float
    pct_dehydrated: float
    kdigo_stage_1_rate_per_1000: float
    kdigo_stage_2_3_rate_per_1000: float
    elevated_creatinine_rate_per_1000: float
    mean_hydration_index: float
    subclinical_aki_flag: bool
    lead_time_days_ahead_of_ed: float = 12.0  # Literature: 10-14 days lead time


def compute_ckd_epi_2021_egfr(
    serum_creatinine_mg_dl: float,
    age: int,
    is_female: bool,
) -> float:
    """
    Computes Estimated Glomerular Filtration Rate (eGFR) using the race-free
    2021 CKD-EPI Creatinine Equation (Inker et al., NEJM 2021; DOI: 10.1056/NEJMoa2102953).

    Formula:
      eGFR = 142 * min(Scr/kappa, 1)^alpha * max(Scr/kappa, 1)^(-1.200)
             * (0.9938^Age) * (1.012 if female else 1.0)
    """
    if serum_creatinine_mg_dl <= 0:
        raise ValueError("Serum creatinine must be strictly positive")
    if age < 18 or age > 110:
        raise ValueError("Age must be between 18 and 110")

    kappa = 0.7 if is_female else 0.9
    alpha = -0.241 if is_female else -0.302
    female_factor = 1.012 if is_female else 1.0

    scr_over_kappa = serum_creatinine_mg_dl / kappa
    term1 = min(scr_over_kappa, 1.0) ** alpha
    term2 = max(scr_over_kappa, 1.0) ** (-1.200)
    term3 = 0.9938 ** age

    egfr = 142.0 * term1 * term2 * term3 * female_factor
    return round(egfr, 2)


def classify_kdigo_aki(
    serum_creatinine_mg_dl: float,
    baseline_creatinine_mg_dl: float,
    egfr_ml_min: float,
    urine_specific_gravity: float = 1.015,
) -> Tuple[int, str]:
    """
    Classifies Acute Kidney Injury (AKI) stage according to KDIGO 2012 guidelines
    supplemented by occupational dehydration markers (USG >= 1.025).

    Returns:
      (stage: int, risk_level: str)
      0: Normal
      1: Stage 1 (Sub-clinical Warning)
      2: Stage 2 (Severe Warning)
      3: Stage 3 (Emergency Cluster)
    """
    if baseline_creatinine_mg_dl <= 0:
        baseline_creatinine_mg_dl = 0.9  # clinical standard male baseline

    ratio = serum_creatinine_mg_dl / baseline_creatinine_mg_dl
    absolute_rise = serum_creatinine_mg_dl - baseline_creatinine_mg_dl

    # KDIGO Stage 3: >= 3.0x baseline OR creatinine >= 4.0 mg/dL with acute rise >= 0.5 mg/dL
    # OR acute drop in eGFR < 35 mL/min/1.73m^2
    if ratio >= 3.0 or (serum_creatinine_mg_dl >= 4.0 and absolute_rise >= 0.5) or egfr_ml_min < 35.0:
        return 3, "Emergency"

    # KDIGO Stage 2: 2.0x to 2.9x baseline
    if ratio >= 2.0:
        return 2, "Warning"

    # KDIGO Stage 1: 1.5x to 1.9x baseline OR absolute rise >= 0.3 mg/dL (26.5 umol/L)
    # OR severe hyperconcentration (USG >= 1.028 with mild creatinine rise >= 1.3x)
    if ratio >= 1.5 or absolute_rise >= 0.3 or (urine_specific_gravity >= 1.028 and ratio >= 1.3):
        return 1, "Caution"

    # Stage 0: Normal
    if urine_specific_gravity >= 1.025:
        return 0, "Caution"  # Significant dehydration without manifest AKI
    return 0, "Normal"


def compute_hydration_index(
    bun_mg_dl: float,
    creatinine_mg_dl: float,
    urine_specific_gravity: float,
) -> float:
    """
    Computes Hydration & Pre-Renal Azotemia Index:
      H_index = (BUN / Creatinine) * ((USG - 1.000) / 0.020)
    Values > 20.0 indicate high pre-renal dehydration risk.
    """
    if creatinine_mg_dl <= 0:
        creatinine_mg_dl = 0.9
    bun_cr_ratio = bun_mg_dl / creatinine_mg_dl
    usg_factor = max(0.0, (urine_specific_gravity - 1.000) / 0.020)
    return round(bun_cr_ratio * usg_factor, 2)


def assess_renal_observation(obs: RenalObservation) -> RenalAssessment:
    """Computes comprehensive clinical assessment for a single biomarker observation."""
    egfr = compute_ckd_epi_2021_egfr(obs.serum_creatinine_mg_dl, obs.age, obs.is_female)
    stage, risk = classify_kdigo_aki(
        obs.serum_creatinine_mg_dl,
        obs.serum_creatinine_baseline_mg_dl,
        egfr,
        obs.urine_specific_gravity,
    )
    h_idx = compute_hydration_index(
        obs.blood_urea_nitrogen_mg_dl,
        obs.serum_creatinine_mg_dl,
        obs.urine_specific_gravity,
    )
    is_dehydrated = obs.urine_specific_gravity >= 1.025 or h_idx >= 20.0
    is_aki = stage >= 1

    return RenalAssessment(
        egfr_ml_min=egfr,
        kdigo_stage=stage,
        hydration_index=h_idx,
        is_dehydrated=is_dehydrated,
        is_aki=is_aki,
        risk_level=risk,
    )


def aggregate_cohort_renal_health(
    observations: List[RenalObservation],
    min_cohort_size: int = 50,
) -> CohortRenalSummary:
    """
    Aggregates individual screening observations into privacy-preserving cohort metrics.
    Enforces small-cell suppression: if total screened < min_cohort_size, suppresses details.
    """
    if not observations:
        return CohortRenalSummary(
            site_id="UNKNOWN",
            observation_date=date.today().isoformat(),
            total_screened=0,
            suppressed=True,
            mean_egfr=0.0,
            pct_dehydrated=0.0,
            kdigo_stage_1_rate_per_1000=0.0,
            kdigo_stage_2_3_rate_per_1000=0.0,
            elevated_creatinine_rate_per_1000=0.0,
            mean_hydration_index=0.0,
            subclinical_aki_flag=False,
        )

    site_id = observations[0].site_id
    obs_date = observations[0].observation_date
    total = len(observations)

    if total < min_cohort_size:
        return CohortRenalSummary(
            site_id=site_id,
            observation_date=obs_date,
            total_screened=total,
            suppressed=True,
            mean_egfr=0.0,
            pct_dehydrated=0.0,
            kdigo_stage_1_rate_per_1000=0.0,
            kdigo_stage_2_3_rate_per_1000=0.0,
            elevated_creatinine_rate_per_1000=0.0,
            mean_hydration_index=0.0,
            subclinical_aki_flag=False,
        )

    assessments = [assess_renal_observation(o) for o in observations]

    egfr_vals = [a.egfr_ml_min for a in assessments]
    dehydrated_count = sum(1 for a in assessments if a.is_dehydrated)
    stage_1_count = sum(1 for a in assessments if a.kdigo_stage == 1)
    stage_2_3_count = sum(1 for a in assessments if a.kdigo_stage >= 2)
    elevated_cr_count = sum(1 for o in observations if o.serum_creatinine_mg_dl >= 1.3)
    h_indices = [a.hydration_index for a in assessments]

    mean_egfr = round(sum(egfr_vals) / total, 1)
    pct_dehydrated = round((dehydrated_count / total) * 100.0, 1)
    stage_1_rate = round((stage_1_count / total) * 1000.0, 1)
    stage_2_3_rate = round((stage_2_3_count / total) * 1000.0, 1)
    elevated_cr_rate = round((elevated_cr_count / total) * 1000.0, 1)
    mean_h_idx = round(sum(h_indices) / total, 2)

    # Subclinical AKI flag triggers when Stage 1 rate > 30/1,000 (3%) or dehydration > 35%
    subclinical_aki_flag = stage_1_rate >= 30.0 or pct_dehydrated >= 35.0 or stage_2_3_rate >= 10.0

    return CohortRenalSummary(
        site_id=site_id,
        observation_date=obs_date,
        total_screened=total,
        suppressed=False,
        mean_egfr=mean_egfr,
        pct_dehydrated=pct_dehydrated,
        kdigo_stage_1_rate_per_1000=stage_1_rate,
        kdigo_stage_2_3_rate_per_1000=stage_2_3_rate,
        elevated_creatinine_rate_per_1000=elevated_cr_rate,
        mean_hydration_index=mean_h_idx,
        subclinical_aki_flag=subclinical_aki_flag,
        lead_time_days_ahead_of_ed=12.0,
    )

