"""
Tornado Sensitivity and Parameter Importance Engine.
Quantifies which assumption drives variance in projected health and economic outcomes.
Produces structured data for tornado diagrams and sensitivity rankings.
"""

from typing import Dict, List, Any
import numpy as np
import pandas as pd

from prahari.whatif.config import load_assumptions_config


class TornadoSensitivityAnalyzer:
    """
    Ranks input assumptions by their partial correlation with the target outcome,
    identifying the dominant drivers of uncertainty.
    """

    PARAM_METADATA = {
        "baseline_rate": {
            "name": "Baseline Heat-Related Illness Incidence",
            "section": "epidemiological_baselines",
            "key": "baseline_heat_illness_rate",
        },
        "slope": {
            "name": "Exposure-Response Slope (per °C WBGT)",
            "section": "intervention_effects",
            "key": "exposure_response_injury_slope",
        },
        "wrs_rr": {
            "name": "Water, Rest, Shade (WRS) Risk Ratio",
            "section": "intervention_effects",
            "key": "hydration_wrs_relative_risk",
        },
        "workdays_lost_rate": {
            "name": "Workdays Lost per Incident",
            "section": "epidemiological_baselines",
            "key": "workdays_lost_per_incident",
        },
        "cost_workday": {
            "name": "Economic Cost per Lost Workday",
            "section": "economic_valuations",
            "key": "cost_per_lost_workday_aed",
        },
        "severe_fraction": {
            "name": "Severe Heat Stroke Fraction",
            "section": "epidemiological_baselines",
            "key": "severe_case_fraction",
        },
        "cost_hospitalisation": {
            "name": "Severe Hospitalisation Cost",
            "section": "economic_valuations",
            "key": "cost_per_severe_hospitalisation_aed",
        },
    }

    @classmethod
    def compute_tornado_ranking(
        cls,
        simulation_result: Dict[str, Any],
        target_metric: str = "cases_averted",
    ) -> List[Dict[str, Any]]:
        """
        Computes tornado sensitivity metrics against the target simulation outcome.
        """
        param_samples = simulation_result.get("_parameter_samples", {})
        outcome_samples = simulation_result.get("_internal_samples", {}).get(target_metric)

        if outcome_samples is None or not param_samples:
            return []

        assumptions_cfg = load_assumptions_config()
        y = np.asarray(outcome_samples, dtype=float)
        y_median = float(np.median(y))

        results = []
        correlations = {}

        for p_key, p_arr in param_samples.items():
            x = np.asarray(p_arr, dtype=float)
            if np.std(x) < 1e-6 or np.std(y) < 1e-6:
                corr = 0.0
            else:
                corr = float(np.corrcoef(x, y)[0, 1])
                if np.isnan(corr):
                    corr = 0.0

            correlations[p_key] = corr

            # Look up metadata and verification status
            meta = cls.PARAM_METADATA.get(p_key, {"name": p_key, "section": "", "key": ""})
            sec = assumptions_cfg.get(meta.get("section", ""), {})
            item = sec.get(meta.get("key", ""), {})
            status = item.get("verification_status", "VERIFIED")

            # Compute low (p10) and high (p90) conditional outcomes for tornado bar width
            p10_mask = x <= np.percentile(x, 25)
            p90_mask = x >= np.percentile(x, 75)

            outcome_at_low_param = float(np.median(y[p10_mask])) if np.any(p10_mask) else y_median
            outcome_at_high_param = float(np.median(y[p90_mask])) if np.any(p90_mask) else y_median

            bar_left = min(outcome_at_low_param, outcome_at_high_param)
            bar_right = max(outcome_at_low_param, outcome_at_high_param)

            results.append({
                "param_key": p_key,
                "name": meta["name"],
                "correlation": round(corr, 3),
                "abs_correlation": round(abs(corr), 3),
                "verification_status": status,
                "median_outcome": round(y_median, 2),
                "bar_low": round(bar_left, 2),
                "bar_high": round(bar_right, 2),
                "swing": round(bar_right - bar_left, 2),
                "direction": "positive" if corr >= 0 else "negative",
            })

        # Rank by absolute swing / correlation descending
        results = sorted(results, key=lambda x: x["swing"], reverse=True)

        total_swing = sum(r["swing"] for r in results)
        for r in results:
            r["relative_importance_pct"] = round(
                (r["swing"] / max(total_swing, 1e-4)) * 100.0, 1
            )

        return results

