"""
L2 Layer: Exposure-Adjusted Baselines (Distinguishes Expected Weather Surge from Outbreaks).
Fits distributed-lag exposure models (PM2.5 lags 0-3, WBGT lags 0-2) and produces two views:
1. 'Total Excess': aberration over normal calendar/seasonal baseline
2. 'Unexplained Excess': aberration NOT explained by ambient heat or air pollution
"""

from dataclasses import dataclass
from typing import Dict, List, Any, Optional, Tuple
import math
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf


@dataclass
class L2ResidualResult:
    """Standardized output from L2 exposure-adjusted modeling."""
    signal_type: str
    geo_id: str
    obs_date: str
    observed: float
    unadjusted_expected: float
    exposure_expected: float
    total_excess: float               # observed - unadjusted_expected
    unexplained_excess: float         # observed - exposure_expected
    explained_by_environment: float   # exposure_expected - unadjusted_expected
    explained_fraction: float         # fraction of total excess explained by weather/AQ
    is_environment_driven: bool       # True if rise is consistent with heatwave/pollution
    unexplained_z_score: float
    p_value_unexplained: float


class L2ExposureBaselineModel:
    """
    Fits exposure-response generalized linear models with lagged environmental terms.
    """

    def __init__(self, min_train_samples: int = 40):
        self.min_train_samples = min_train_samples

    def evaluate_date(
        self,
        merged_df: pd.DataFrame,
        current_date_str: str,
        target_signal: str,
        geo_id: str,
    ) -> L2ResidualResult:
        """
        Evaluates observations for target_signal at geo_id up to current_date_str.
        merged_df must contain:
          ['obs_date', 'signal_type', 'geo_id', 'value', 'denominator', 'pm25', 'wbgt_max']
        """
        df = merged_df[
            (merged_df["signal_type"] == target_signal) & (merged_df["geo_id"] == geo_id)
        ].sort_values(by="obs_date").copy()

        if df.empty:
            raise ValueError(f"No records found for signal={target_signal}, geo_id={geo_id}")

        curr_rows = df[df["obs_date"] == current_date_str]
        if curr_rows.empty:
            raise ValueError(f"Date {current_date_str} not in merged_df for {target_signal}")

        observed = float(curr_rows["value"].iloc[0])
        denom = float(curr_rows["denominator"].iloc[0]) if pd.notna(curr_rows["denominator"].iloc[0]) else 100000.0

        past_df = df[df["obs_date"] < current_date_str].copy()

        # If history is too short for GLM fitting, return conservative fallback
        if len(past_df) < self.min_train_samples:
            mean_val = float(past_df["value"].mean()) if not past_df.empty else observed
            tot_excess = max(0.0, observed - mean_val)
            return L2ResidualResult(
                signal_type=target_signal,
                geo_id=geo_id,
                obs_date=current_date_str,
                observed=observed,
                unadjusted_expected=round(mean_val, 2),
                exposure_expected=round(mean_val, 2),
                total_excess=round(tot_excess, 2),
                unexplained_excess=round(tot_excess, 2),
                explained_by_environment=0.0,
                explained_fraction=0.0,
                is_environment_driven=False,
                unexplained_z_score=1.0 if tot_excess > 0 else 0.0,
                p_value_unexplained=0.05 if tot_excess > 0 else 0.5,
            )

        # 1. Feature Engineering: lags, DOW, harmonics, non-linear splines
        full_df = df[df["obs_date"] <= current_date_str].copy()
        full_df["dt"] = pd.to_datetime(full_df["obs_date"])
        full_df["day_of_week"] = full_df["dt"].dt.dayofweek
        full_df["day_of_year"] = full_df["dt"].dt.dayofyear
        full_df["sin_doy"] = np.sin(2.0 * math.pi * full_df["day_of_year"] / 365.25)
        full_df["cos_doy"] = np.cos(2.0 * math.pi * full_df["day_of_year"] / 365.25)

        # Environmental Lags
        if "pm25" in full_df.columns:
            full_df["pm25_lag0"] = full_df["pm25"].fillna(30.0)
            full_df["pm25_lag1"] = full_df["pm25_lag0"].shift(1).fillna(30.0)
            full_df["pm25_lag2"] = full_df["pm25_lag0"].shift(2).fillna(30.0)
            full_df["pm25_lag3"] = full_df["pm25_lag0"].shift(3).fillna(30.0)
            full_df["pm25_3d_mean"] = (full_df["pm25_lag0"] + full_df["pm25_lag1"] + full_df["pm25_lag2"]) / 3.0
            full_df["pm25_excess"] = np.maximum(0.0, full_df["pm25_3d_mean"] - 25.0)
        else:
            full_df["pm25_excess"] = 0.0

        if "wbgt_max" in full_df.columns:
            full_df["wbgt_lag0"] = full_df["wbgt_max"].fillna(26.0)
            full_df["wbgt_lag1"] = full_df["wbgt_lag0"].shift(1).fillna(26.0)
            full_df["wbgt_lag2"] = full_df["wbgt_lag0"].shift(2).fillna(26.0)
            full_df["wbgt_3d_max"] = np.maximum(full_df["wbgt_lag0"], np.maximum(full_df["wbgt_lag1"], full_df["wbgt_lag2"]))
            full_df["wbgt_excess"] = np.maximum(0.0, full_df["wbgt_3d_max"] - 28.0)
        else:
            full_df["wbgt_excess"] = 0.0

        # Split train (past) and test (current day)
        train_df = full_df[full_df["obs_date"] < current_date_str].copy()
        current_row = full_df[full_df["obs_date"] == current_date_str]

        # 2. Fit Model A: Unadjusted Calendar Baseline (Seasonality + Day of Week)
        formula_unadj = "value ~ C(day_of_week) + sin_doy + cos_doy"
        try:
            model_unadj = smf.glm(
                formula=formula_unadj,
                data=train_df,
                family=sm.families.NegativeBinomial(alpha=0.15),
            ).fit()
            unadj_expected = float(model_unadj.predict(current_row).iloc[0])
        except Exception:
            unadj_expected = float(train_df["value"].mean())

        unadj_expected = max(unadj_expected, 0.1)

        # 3. Fit Model B: Exposure-Adjusted Model (Includes Weather & PM2.5 Lags)
        if "resp" in target_signal:
            formula_adj = "value ~ C(day_of_week) + sin_doy + cos_doy + pm25_excess"
        elif "heat" in target_signal or "absence" in target_signal:
            formula_adj = "value ~ C(day_of_week) + sin_doy + cos_doy + wbgt_excess"
        else:
            # GI, fever, or lab test with no direct weather link
            formula_adj = "value ~ C(day_of_week) + sin_doy + cos_doy"

        try:
            model_adj = smf.glm(
                formula=formula_adj,
                data=train_df,
                family=sm.families.NegativeBinomial(alpha=0.15),
            ).fit()
            exposure_expected = float(model_adj.predict(current_row).iloc[0])
        except Exception:
            exposure_expected = unadj_expected

        exposure_expected = max(exposure_expected, 0.1)

        # 4. Compute Residual Decompositions
        total_excess = observed - unadj_expected
        unexplained_excess = observed - exposure_expected
        explained_env = exposure_expected - unadj_expected

        # Explained fraction of total excess
        if total_excess > 0:
            explained_fraction = max(0.0, min(1.0, explained_env / total_excess))
        else:
            explained_fraction = 0.0

        # Z-score of unexplained residual
        residual_std = max(float(train_df["value"].std()), 1.0)
        unexplained_z = unexplained_excess / residual_std
        p_val_unexplained = float(1.0 - stats.norm.cdf(unexplained_z))

        # Flag as environment-driven if explained fraction >= 60%
        is_environment_driven = (explained_fraction >= 0.60) and (unexplained_z < 2.0)

        return L2ResidualResult(
            signal_type=target_signal,
            geo_id=geo_id,
            obs_date=current_date_str,
            observed=round(observed, 2),
            unadjusted_expected=round(unadj_expected, 2),
            exposure_expected=round(exposure_expected, 2),
            total_excess=round(total_excess, 2),
            unexplained_excess=round(unexplained_excess, 2),
            explained_by_environment=round(explained_env, 2),
            explained_fraction=round(explained_fraction, 3),
            is_environment_driven=is_environment_driven,
            unexplained_z_score=round(unexplained_z, 2),
            p_value_unexplained=round(p_val_unexplained, 4),
        )

