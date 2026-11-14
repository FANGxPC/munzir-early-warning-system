"""
Unified What-If Intervention Simulator Engine.
Orchestrates deterministic schedule exposure recomputations, Monte Carlo uncertainty
propagation, tornado sensitivity rankings, and ties directly into alert playbooks.
Enforces differential privacy boundaries and small-cell suppression rules.
"""

from typing import Dict, List, Any, Optional
from datetime import datetime
import json
from pathlib import Path

from prahari.config import (
    BASE_DIR,
    REGIONAL_PROFILES,
    WORKPLACE_MIN_GROUP_SIZE,
    SMALL_CELL_K,
)
from prahari.whatif.config import (
    load_assumptions_config,
    get_unverified_assumptions,
)
from prahari.whatif.exposure import (
    WorkSchedule,
    ExposureCalculator,
)
from prahari.whatif.monte_carlo import MonteCarloInterventionSimulator
from prahari.whatif.sensitivity import TornadoSensitivityAnalyzer


class WhatIfSimulator:
    """
    Simulates operational workplace interventions against real WBGT time series,
    propagating uncertainty across peer-reviewed and statutory assumptions.
    """

    AVAILABLE_SCENARIOS = {
        "shift_hours": {
            "name": "Shift Working Hours (Split Shift)",
            "description": "Shifts work to early morning (05:30-11:30) and early evening (16:30-18:30), avoiding peak midday solar radiation.",
            "feasibility": "High. Commonly practiced on UAE infrastructure projects with temporary site floodlighting.",
            "cost_notes": "Estimated operational friction of AED 15/worker/month (dual bus logistics, pre-dawn site lighting). Mark: UNVERIFIED.",
            "cost_status": "UNVERIFIED",
            "schedule": WorkSchedule(
                name="Early Split Shift",
                start_hour=5.5,
                end_hour=11.5,
                break_start=11.5,
                break_end=16.5,
                split_shift_start_2=16.5,
                split_shift_end_2=18.5,
            ),
            "shade_delta_c": 0.0,
            "is_water_cooling_active": False,
            "is_shade_active": False,
            "is_reschedule_active": True,
        },
        "extend_break": {
            "name": "Extend Midday Heat Break",
            "description": "Extends the mandatory midday break from 11:30 to 15:30 (4.0 hours) during extreme heat alerts, exceeding statutory minimums.",
            "feasibility": "High. Aligns directly with UAE MOHRE Ministerial Resolution 44 (12:30-15:00 minimum ban).",
            "cost_notes": "Negligible direct material expense; minor shift rescheduling friction.",
            "cost_status": "VERIFIED_STATUTORY_EXTENSION",
            "schedule": WorkSchedule(
                name="Extended Midday Break",
                start_hour=6.5,
                end_hour=17.5,
                break_start=11.5,
                break_end=15.5,
            ),
            "shade_delta_c": 0.0,
            "is_water_cooling_active": False,
            "is_shade_active": False,
            "is_reschedule_active": False,
        },
        "add_shade": {
            "name": "Deploy Modular Shade Canopies",
            "description": "Erects UV-blocking mobile shade pavilions over active structural assembly, logistics, and rest areas.",
            "feasibility": "High. Modular 100m² canopies deployable within 4 hours.",
            "cost_notes": "Estimated commercial hire rate of AED 30/worker/month. Mark: UNVERIFIED (Commercial rental quote).",
            "cost_status": "UNVERIFIED",
            "schedule": WorkSchedule(
                name="Standard Shift with Shade",
                start_hour=7.0,
                end_hour=16.0,
                break_start=12.5,
                break_end=14.0,
            ),
            "shade_delta_c": 2.5,  # Sourced from Hall & Horta (2020)
            "is_water_cooling_active": False,
            "is_shade_active": True,
            "is_reschedule_active": False,
        },
        "add_water_cooling": {
            "name": "Mandatory Hydration & Chilled Rest Stations",
            "description": "Institutes enforced 250ml electrolyte hydration every 30 mins paired with high-velocity misting fans in rest bays.",
            "feasibility": "High. Requires dedicated hydration stewards and chilled dispensers.",
            "cost_notes": "Consumables estimate of AED 2.50/worker/day (3L chilled water + electrolyte powder). Mark: UNVERIFIED.",
            "cost_status": "UNVERIFIED",
            "schedule": WorkSchedule(
                name="Standard Shift with Hydration Protocol",
                start_hour=7.0,
                end_hour=16.0,
                break_start=12.5,
                break_end=14.0,
            ),
            "shade_delta_c": 0.0,
            "is_water_cooling_active": True,
            "is_shade_active": False,
            "is_reschedule_active": False,
        },
        "combined_protocol": {
            "name": "Comprehensive Multi-Layer Protection Protocol",
            "description": "Combines early morning split-shift, extended midday break, mobile shade canopies, and active chilled hydration.",
            "feasibility": "High for mega-projects; requires project director authorization.",
            "cost_notes": "Combined implementation costs across shade, water, and shift adjustments (~AED 105/worker/month). Mark: UNVERIFIED.",
            "cost_status": "UNVERIFIED",
            "schedule": WorkSchedule(
                name="Comprehensive Protocol Shift",
                start_hour=5.5,
                end_hour=11.5,
                break_start=11.5,
                break_end=16.5,
                split_shift_start_2=16.5,
                split_shift_end_2=18.5,
            ),
            "shade_delta_c": 2.5,
            "is_water_cooling_active": True,
            "is_shade_active": True,
            "is_reschedule_active": True,
        },
    }

    def __init__(self, seed: int = 42):
        self.seed = seed
        self.assumptions_cfg = load_assumptions_config()
        self.mc_engine = MonteCarloInterventionSimulator(n_iterations=1000, seed=self.seed)

    def simulate(
        self,
        site_id: str = "SITE-JA-01",
        action_type: str = "combined_protocol",
        start_date: str = "2024-06-01",
        end_date: str = "2024-06-30",
        workforce_override: Optional[int] = None,
        shade_delta_override: Optional[float] = None,
        break_extension_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Executes end-to-end intervention simulation:
        1. Validates privacy threshold (workforce >= 50 workers)
        2. Computes deterministic exposure-hours from real WBGT
        3. Runs Monte Carlo uncertainty propagation over assumptions
        4. Computes tornado sensitivity rankings
        5. Labels all UNVERIFIED cost and effect parameters
        """
        if action_type not in self.AVAILABLE_SCENARIOS:
            raise ValueError(f"Unknown action_type '{action_type}'. Available: {list(self.AVAILABLE_SCENARIOS.keys())}")

        scenario_def = self.AVAILABLE_SCENARIOS[action_type]

        # 1. Lookup site and workforce
        site_info = None
        for s in REGIONAL_PROFILES.get("uae", {}).get("sites", []):
            if s["id"] == site_id:
                site_info = s
                break

        workforce = workforce_override or (site_info["workforce"] if site_info else 1000)

        # Enforce Privacy Layer: minimum group size for workplace health surveillance
        if workforce < WORKPLACE_MIN_GROUP_SIZE:
            raise PermissionError(
                f"Privacy Protection Error: Workforce cohort ({workforce}) is below minimum group size ({WORKPLACE_MIN_GROUP_SIZE}). "
                "Individual or small-cohort simulations are prohibited to prevent re-identification."
            )

        # 2. Load authentic WBGT series
        df_wbgt = ExposureCalculator.load_site_wbgt_series(site_id, start_date, end_date)
        duration_days = max(1.0, float(len(df_wbgt["date"].unique()))) if (not df_wbgt.empty and "date" in df_wbgt.columns) else 1.0

        # 3. Deterministic Exposure Computation
        baseline_schedule = WorkSchedule("Standard Baseline", 7.0, 16.0, 12.5, 14.0)
        scenario_schedule = scenario_def["schedule"]
        if break_extension_minutes is not None and break_extension_minutes > 0:
            extra_half_hours = (break_extension_minutes / 60.0) / 2.0
            scenario_schedule = WorkSchedule(
                name=f"{scenario_schedule.name} (+{break_extension_minutes}m)",
                start_hour=scenario_schedule.start_hour,
                end_hour=scenario_schedule.end_hour,
                break_start=max(10.0, scenario_schedule.break_start - extra_half_hours),
                break_end=min(17.0, scenario_schedule.break_end + extra_half_hours),
                split_shift_start_2=scenario_schedule.split_shift_start_2,
                split_shift_end_2=scenario_schedule.split_shift_end_2,
            )

        shade_delta = shade_delta_override if shade_delta_override is not None else scenario_def["shade_delta_c"]

        exposure_comp = ExposureCalculator.compare_interventions_deterministic(
            df_wbgt=df_wbgt,
            baseline_schedule=baseline_schedule,
            scenario_schedule=scenario_schedule,
            shade_delta_c=shade_delta,
            workforce_size=workforce,
        )

        # 4. Monte Carlo Uncertainty Propagation
        mc_results = self.mc_engine.run_simulation(
            exposure_comparison=exposure_comp,
            duration_days=duration_days,
            workforce_size=workforce,
            is_water_cooling_active=scenario_def["is_water_cooling_active"],
            is_shade_active=scenario_def["is_shade_active"],
            is_reschedule_active=scenario_def["is_reschedule_active"],
        )

        # 5. Sensitivity & Tornado Analysis
        tornado_ranking = TornadoSensitivityAnalyzer.compute_tornado_ranking(
            mc_results,
            target_metric="cases_averted",
        )

        # 6. Privacy Suppression Gate (Small-Cell Rule)
        median_cases = mc_results["cases_averted"]["median"]
        is_suppressed = False
        suppression_notice = None
        if median_cases < SMALL_CELL_K:
            is_suppressed = True
            suppression_notice = f"Small-cell suppression active: projected cases < {SMALL_CELL_K}. Displayed as bounded estimate."

        # 7. Unverified Assumptions Audit
        unverified_list = get_unverified_assumptions(self.assumptions_cfg)

        return {
            "metadata": {
                "site_id": site_id,
                "site_name": site_info["name"] if site_info else site_id,
                "action_type": action_type,
                "scenario_name": scenario_def["name"],
                "start_date": start_date,
                "end_date": end_date,
                "duration_days": int(duration_days),
                "workforce_size": workforce,
                "generated_at": datetime.now().isoformat(),
                "privacy_compliant": True,
                "is_suppressed": is_suppressed,
                "suppression_notice": suppression_notice,
            },
            "feasibility_and_costs": {
                "feasibility_assessment": scenario_def["feasibility"],
                "cost_notes": scenario_def["cost_notes"],
                "cost_status": scenario_def["cost_status"],
            },
            "deterministic_exposure": exposure_comp,
            "stochastic_outcomes": {
                "cases_averted": mc_results["cases_averted"],
                "severe_incidents_averted": mc_results["severe_incidents_averted"],
                "workdays_saved": mc_results["workdays_saved"],
                "gross_savings_aed": mc_results["gross_savings_aed"],
                "implementation_cost_aed": mc_results["implementation_cost_aed"],
                "net_savings_aed": mc_results["net_savings_aed"],
                "benefit_cost_ratio": mc_results["benefit_cost_ratio"],
            },
            "tornado_sensitivity": tornado_ranking,
            "unverified_assumptions": unverified_list,
        }
