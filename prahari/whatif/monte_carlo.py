"""
Monte Carlo Uncertainty Propagation Engine for Health & Economic Interventions.
Propagates stochastic uncertainty across literature-sourced assumption ranges.
Produces strictly median and 90% uncertainty intervals [p5, p95] — never a single point estimate.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

from prahari.whatif.config import load_assumptions_config


class MonteCarloInterventionSimulator:
    """
    Executes Monte Carlo uncertainty propagation over occupational health and
    economic intervention assumptions.
    """

    def __init__(self, n_iterations: int = 1000, seed: int = 42):
        self.n_iterations = n_iterations
        self.seed = seed
        self.assumptions_cfg = load_assumptions_config()

    def run_simulation(
        self,
        exposure_comparison: Dict[str, Any],
        duration_days: float = 30.0,
        workforce_size: int = 1000,
        is_water_cooling_active: bool = False,
        is_shade_active: bool = False,
        is_reschedule_active: bool = False,
    ) -> Dict[str, Any]:
        """
        Runs N iterations sampling all parameters across their defined min-max ranges.
        """
        rng = np.random.RandomState(self.seed)
        N = self.n_iterations

        effects = self.assumptions_cfg.get("intervention_effects", {})
        baselines = self.assumptions_cfg.get("epidemiological_baselines", {})
        economics = self.assumptions_cfg.get("economic_valuations", {})
        costs = self.assumptions_cfg.get("intervention_costs", {})

        # Extract assumption parameter bounds (with safe fallbacks)
        def get_range(d: Dict[str, Any], key: str, default: Tuple[float, float]) -> Tuple[float, float]:
            item = d.get(key, {})
            r = item.get("range")
            if r and len(r) == 2:
                return float(r[0]), float(r[1])
            return default

        r_slope = get_range(effects, "exposure_response_injury_slope", (0.08, 0.25))
        r_wrs = get_range(effects, "hydration_wrs_relative_risk", (0.22, 0.41))
        r_base_rate = get_range(baselines, "baseline_heat_illness_rate", (0.015, 0.040))
        r_severe_frac = get_range(baselines, "severe_case_fraction", (0.015, 0.045))
        r_workdays_lost = get_range(baselines, "workdays_lost_per_incident", (2.0, 5.0))
        r_cost_workday = get_range(economics, "cost_per_lost_workday_aed", (350.0, 600.0))
        r_cost_hosp = get_range(economics, "cost_per_severe_hospitalisation_aed", (8000.0, 18000.0))

        # Costs (labeled UNVERIFIED)
        r_cost_shade = get_range(costs, "cost_shade_canopy_rental_per_worker_month_aed", (15.0, 60.0))
        r_cost_water = get_range(costs, "cost_hydration_point_per_worker_day_aed", (1.50, 4.00))
        r_cost_shift = get_range(costs, "cost_shift_reschedule_friction_per_worker_month_aed", (5.0, 35.0))

        # Sample parameter arrays (Uniform distributions across literature bounds)
        s_slope = rng.uniform(r_slope[0], r_slope[1], N)
        s_wrs = rng.uniform(r_wrs[0], r_wrs[1], N) if is_water_cooling_active else np.ones(N)
        s_base_rate = rng.uniform(r_base_rate[0], r_base_rate[1], N)
        s_severe_frac = rng.uniform(r_severe_frac[0], r_severe_frac[1], N)
        s_workdays_lost = rng.uniform(r_workdays_lost[0], r_workdays_lost[1], N)
        s_cost_workday = rng.uniform(r_cost_workday[0], r_cost_workday[1], N)
        s_cost_hosp = rng.uniform(r_cost_hosp[0], r_cost_hosp[1], N)

        s_cost_shade = rng.uniform(r_cost_shade[0], r_cost_shade[1], N) if is_shade_active else np.zeros(N)
        s_cost_water = rng.uniform(r_cost_water[0], r_cost_water[1], N) if is_water_cooling_active else np.zeros(N)
        s_cost_shift = rng.uniform(r_cost_shift[0], r_cost_shift[1], N) if is_reschedule_active else np.zeros(N)

        # Baseline exposure metrics
        b_exp = exposure_comparison["baseline"]
        sc_exp = exposure_comparison["scenario"]

        b_danger_hours = max(b_exp["exposure_hours_danger"], 0.1)
        sc_danger_hours = max(sc_exp["exposure_hours_danger"], 0.0)

        # Exposure ratio: ratio of heat exposure under scenario vs baseline
        # Weighted combination of danger (weight 1.0) and caution (weight 0.4)
        b_score = b_exp["exposure_hours_danger"] + 0.4 * b_exp["exposure_hours_caution"]
        sc_score = sc_exp["exposure_hours_danger"] + 0.4 * sc_exp["exposure_hours_caution"]
        f_exposure = max(0.0, min(1.0, sc_score / max(b_score, 0.1)))

        # Baseline cases over period (scaled to duration fraction of 90-day season)
        time_fraction = max(duration_days / 90.0, 0.05)
        # Exposure slope increases baseline rate by thermal excess over 28°C
        thermal_excess_base = max(b_exp["mean_wbgt_working"] - 28.0, 0.0)
        n_baseline_cases = workforce_size * s_base_rate * time_fraction * (1.0 + s_slope * thermal_excess_base)

        # Scenario cases: modulated by exposure reduction and hydration WRS factor
        thermal_excess_scen = max(sc_exp["mean_wbgt_working"] - 28.0, 0.0)
        scenario_multiplier = f_exposure * s_wrs * (1.0 + s_slope * thermal_excess_scen) / (1.0 + s_slope * thermal_excess_base)
        scenario_multiplier = np.clip(scenario_multiplier, 0.05, 1.0)
        n_scenario_cases = n_baseline_cases * scenario_multiplier

        # Averted clinical and operational burdens
        cases_averted = np.maximum(0.0, n_baseline_cases - n_scenario_cases)
        severe_averted = cases_averted * s_severe_frac
        workdays_saved = cases_averted * s_workdays_lost

        # Economic Gross Savings (AED)
        savings_workdays_aed = workdays_saved * s_cost_workday
        savings_medical_aed = severe_averted * s_cost_hosp
        gross_savings_aed = savings_workdays_aed + savings_medical_aed

        # Implementation Costs (AED)
        months_fraction = max(duration_days / 30.0, 0.1)
        cost_shade_total = workforce_size * s_cost_shade * months_fraction
        cost_water_total = workforce_size * s_cost_water * duration_days
        cost_shift_total = workforce_size * s_cost_shift * months_fraction
        total_implementation_cost = cost_shade_total + cost_water_total + cost_shift_total

        # Net Benefit & BCR
        net_savings_aed = gross_savings_aed - total_implementation_cost
        bcr = gross_savings_aed / np.maximum(100.0, total_implementation_cost)

        # Calculate percentile intervals: Median (p50), 90% CI: [p5, p95]
        def get_interval(arr: np.ndarray) -> Dict[str, float]:
            return {
                "median": round(float(np.percentile(arr, 50)), 2),
                "p05": round(float(np.percentile(arr, 5)), 2),
                "p95": round(float(np.percentile(arr, 95)), 2),
                "mean": round(float(np.mean(arr)), 2),
            }

        samples_dict = {
            "cases_averted": cases_averted,
            "severe_averted": severe_averted,
            "workdays_saved": workdays_saved,
            "gross_savings_aed": gross_savings_aed,
            "total_implementation_cost": total_implementation_cost,
            "net_savings_aed": net_savings_aed,
            "benefit_cost_ratio": bcr,
        }

        parameter_samples = {
            "slope": s_slope,
            "wrs_rr": s_wrs,
            "baseline_rate": s_base_rate,
            "severe_fraction": s_severe_frac,
            "workdays_lost_rate": s_workdays_lost,
            "cost_workday": s_cost_workday,
            "cost_hospitalisation": s_cost_hosp,
        }

        return {
            "simulation_meta": {
                "n_iterations": N,
                "random_seed": self.seed,
                "duration_days": duration_days,
                "workforce_size": workforce_size,
                "confidence_level": "90% Interval (p05 to p95)",
            },
            "cases_averted": get_interval(cases_averted),
            "severe_incidents_averted": get_interval(severe_averted),
            "workdays_saved": get_interval(workdays_saved),
            "gross_savings_aed": get_interval(gross_savings_aed),
            "implementation_cost_aed": get_interval(total_implementation_cost),
            "net_savings_aed": get_interval(net_savings_aed),
            "benefit_cost_ratio": get_interval(bcr),
            "_internal_samples": samples_dict,
            "_parameter_samples": parameter_samples,
        }

