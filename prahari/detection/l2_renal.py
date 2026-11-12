"""
Layer 2 Renal Surveillance Coupling: Ambient WBGT Exposure to Sub-Clinical AKI (Phase 14).
Links cumulative extreme heat exposure (WBGT >= 32°C hours over 7-14 days)
to biomarker renal strain, predicting downstream emergency department surge.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from prahari.biomarkers.renal_engine import CohortRenalSummary


@dataclass
class RenalCouplingAlert:
    """Alert generated when sub-clinical renal strain precedes hospital impact."""
    site_id: str
    observation_date: str
    subclinical_aki_risk_score: float  # 0.0 to 1.0
    kdigo_stage_1_rate: float
    pct_dehydrated: float
    cumulative_wbgt_32_hours_14d: float
    alert_tier: str  # Normal, Watch, Warning, Emergency
    estimated_lead_time_days: float
    clinical_mechanism: str
    recommended_action: str


def evaluate_renal_environmental_coupling(
    renal_summary: CohortRenalSummary,
    cumulative_wbgt_32_hours_14d: float,
) -> RenalCouplingAlert:
    """
    Evaluates whether observed cohort renal stress is driven by prolonged occupational heat exposure.
    Grounded in Wegman et al. (2018) and Glaser et al. (Lancet Planetary Health 2016).
    """
    if renal_summary.suppressed:
        return RenalCouplingAlert(
            site_id=renal_summary.site_id,
            observation_date=renal_summary.observation_date,
            subclinical_aki_risk_score=0.0,
            kdigo_stage_1_rate=0.0,
            pct_dehydrated=0.0,
            cumulative_wbgt_32_hours_14d=cumulative_wbgt_32_hours_14d,
            alert_tier="Normal",
            estimated_lead_time_days=0.0,
            clinical_mechanism="Insufficient cohort size (privacy suppressed)",
            recommended_action="Maintain routine surveillance",
        )

    # Base risk driven by dehydration % and KDIGO stage 1 rate
    dehydration_weight = (renal_summary.pct_dehydrated / 100.0) * 0.4
    aki_weight = min(1.0, renal_summary.kdigo_stage_1_rate_per_1000 / 100.0) * 0.4
    severe_aki_weight = min(1.0, renal_summary.kdigo_stage_2_3_rate_per_1000 / 30.0) * 0.2
    biological_strain = dehydration_weight + aki_weight + severe_aki_weight

    # Thermal amplifier: cumulative exposure > 40 hours in 14 days amplifies risk
    thermal_factor = min(1.5, 1.0 + (max(0.0, cumulative_wbgt_32_hours_14d - 20.0) / 80.0))
    risk_score = round(min(1.0, biological_strain * thermal_factor), 3)

    if risk_score >= 0.70 or renal_summary.kdigo_stage_2_3_rate_per_1000 >= 15.0:
        tier = "Warning"
        lead_time = 11.5
        mechanism = (
            f"Severe cumulative pre-renal stress: {renal_summary.pct_dehydrated}% dehydration and "
            f"{renal_summary.kdigo_stage_1_rate_per_1000}/1k KDIGO stage-1 AKI across {cumulative_wbgt_32_hours_14d:.1f}h "
            f"extreme WBGT exposure. Signals impending clinical heat exhaustion admissions."
        )
        action = (
            "Mandate immediate electrolyte replacement protocols, double shade rest duration (20m/h), "
            "and conduct on-site urine specific gravity Dipstick rescreening for heavy labor gangs."
        )
    elif risk_score >= 0.40 or renal_summary.subclinical_aki_flag:
        tier = "Watch"
        lead_time = 14.0
        mechanism = (
            f"Emerging sub-clinical dehydration: {renal_summary.pct_dehydrated}% cohort hyperconcentration with "
            f"mean hydration index {renal_summary.mean_hydration_index}. Indicates early tubular strain."
        )
        action = (
            "Deploy mobile chilled electrolyte points within 150m of work gangs and instruct foremen to "
            "enforce mandatory hydration checks at shift start and midday."
        )
    else:
        tier = "Normal"
        lead_time = 0.0
        mechanism = "Biomarker indices within expected physiological baseline."
        action = "Maintain standard occupational monitoring."

    return RenalCouplingAlert(
        site_id=renal_summary.site_id,
        observation_date=renal_summary.observation_date,
        subclinical_aki_risk_score=risk_score,
        kdigo_stage_1_rate=renal_summary.kdigo_stage_1_rate_per_1000,
        pct_dehydrated=renal_summary.pct_dehydrated,
        cumulative_wbgt_32_hours_14d=cumulative_wbgt_32_hours_14d,
        alert_tier=tier,
        estimated_lead_time_days=lead_time,
        clinical_mechanism=mechanism,
        recommended_action=action,
    )

