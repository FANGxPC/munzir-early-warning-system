"""
L1 Layer: Per-Signal Aberration Detection (Epidemiological Baselines).
Implements:
1. CDC EARS C1, C2, and C3 algorithms (moving-baseline z-scores for short histories)
2. Farrington-Flexible algorithm (quasi-Poisson GLM with harmonic seasonality and outbreak down-weighting)
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
import math
import warnings
import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.api as sm
import statsmodels.formula.api as smf


@dataclass
class L1Result:
    """Standardized output per signal × location × day from L1 aberration models."""
    signal_type: str
    geo_id: str
    obs_date: str
    observed_count: float
    expected_count: float
    upper_threshold: float
    exceedance_score: float  # observed / upper_threshold
    p_value: float
    z_score: float
    algorithm: str  # ears_c1, ears_c2, ears_c3, farrington


class EARSDetector:
    """
    CDC Early Aberration Reporting System (EARS) C1, C2, C3 implementation.
    Reference: Hutwagner et al., CDC MMWR (2003).
    """

    @staticmethod
    def detect_c1(series: List[float], min_variance: float = 0.5) -> Tuple[float, float, float, float]:
        """
        EARS C1: 7-day moving baseline immediately preceding the current day (t-7 to t-1).
        Returns: (expected, threshold_3sd, z_score, p_value)
        """
        if len(series) < 8:
            return 0.0, 0.0, 0.0, 1.0

        current = series[-1]
        baseline = series[-8:-1]  # 7 days prior
        mean = float(np.mean(baseline))
        std = float(np.std(baseline, ddof=1))
        effective_std = max(std, min_variance, math.sqrt(max(mean, 0.1)))

        z = (current - mean) / effective_std
        threshold = mean + 3.0 * effective_std
        p_val = float(1.0 - stats.norm.cdf(z))
        return mean, threshold, float(z), p_val

    @staticmethod
    def detect_c2(series: List[float], min_variance: float = 0.5) -> Tuple[float, float, float, float]:
        """
        EARS C2: 7-day moving baseline with a 2-day guard band (t-9 to t-3).
        The guard band prevents emerging outbreaks from inflating the baseline.
        Returns: (expected, threshold_3sd, z_score, p_value)
        """
        if len(series) < 10:
            return EARSDetector.detect_c1(series, min_variance)

        current = series[-1]
        baseline = series[-10:-3]  # 7 days with 2-day buffer
        mean = float(np.mean(baseline))
        std = float(np.std(baseline, ddof=1))
        effective_std = max(std, min_variance, math.sqrt(max(mean, 0.1)))

        z = (current - mean) / effective_std
        threshold = mean + 3.0 * effective_std
        p_val = float(1.0 - stats.norm.cdf(z))
        return mean, threshold, float(z), p_val

    @staticmethod
    def detect_c3(series: List[float], min_variance: float = 0.5) -> Tuple[float, float, float, float]:
        """
        EARS C3: 3-day accumulated excess over C2 baseline.
        Captures low-grade sustained rises over 3 consecutive days.
        Returns: (expected, threshold, c3_score, p_value)
        """
        if len(series) < 12:
            return EARSDetector.detect_c2(series, min_variance)

        # Compute C2 z-scores for past 3 days (t-2, t-1, t)
        z_scores = []
        for offset in [2, 1, 0]:
            sub_series = series[: len(series) - offset] if offset > 0 else series
            _, _, z, _ = EARSDetector.detect_c2(sub_series, min_variance)
            z_scores.append(max(0.0, z - 1.0))

        c3_sum = float(np.sum(z_scores))
        threshold = 2.0  # CDC standard threshold for C3
        mean, c2_thresh, current_z, _ = EARSDetector.detect_c2(series, min_variance)

        # Approximate p-value from chi-square distribution of sum of squared truncated normal
        p_val = float(1.0 - stats.chi2.cdf(c3_sum ** 2, df=3))
        return mean, threshold, c3_sum, p_val


class FarringtonDetector:
    """
    Farrington-Flexible aberration detection algorithm.
    Fits a quasi-Poisson GLM with linear trend and annual harmonic seasonality,
    down-weights historical outbreak periods using Anscombe residuals,
    and computes the 2/3 power transformed upper threshold.
    Reference: Farrington & Andrews (1996), Noufaily et al. (2013).
    """

    def __init__(self, alpha: float = 0.05, min_history_days: int = 60):
        self.alpha = alpha
        self.z_alpha = float(stats.norm.ppf(1.0 - alpha))
        self.min_history_days = min_history_days

    def fit_and_predict(
        self,
        history_df: pd.DataFrame,
        current_date_str: str,
        value_col: str = "value",
        date_col: str = "obs_date",
    ) -> L1Result:
        """
        Evaluates current day against historical quasi-Poisson baseline.
        history_df must contain at least `date_col` and `value_col`.
        """
        df = history_df.sort_values(by=date_col).copy()
        current_rows = df[df[date_col] == current_date_str]

        if current_rows.empty:
            raise ValueError(f"Date {current_date_str} not found in history_df")

        current_val = float(current_rows[value_col].iloc[0])
        past_df = df[df[date_col] < current_date_str].copy()

        # If history is short, gracefully fall back to EARS C2
        if len(past_df) < self.min_history_days:
            values = list(past_df[value_col].values) + [current_val]
            mean, thresh, z, p = EARSDetector.detect_c2(values)
            exc = current_val / max(thresh, 0.1)
            sig_type = str(current_rows.get("signal_type", pd.Series(["unknown"])).iloc[0])
            geo_id = str(current_rows.get("geo_id", pd.Series(["unknown"])).iloc[0])
            return L1Result(
                signal_type=sig_type,
                geo_id=geo_id,
                obs_date=current_date_str,
                observed_count=current_val,
                expected_count=round(mean, 2),
                upper_threshold=round(thresh, 2),
                exceedance_score=round(exc, 3),
                p_value=round(p, 4),
                z_score=round(z, 2),
                algorithm="ears_c2_fallback",
            )

        # Prepare regression covariates
        past_df["t"] = np.arange(len(past_df))
        past_df["day_of_year"] = pd.to_datetime(past_df[date_col]).dt.dayofyear
        past_df["sin_harmonic"] = np.sin(2.0 * math.pi * past_df["day_of_year"] / 365.25)
        past_df["cos_harmonic"] = np.cos(2.0 * math.pi * past_df["day_of_year"] / 365.25)

        current_t = len(past_df)
        curr_dt = pd.to_datetime(current_date_str)
        curr_doy = curr_dt.dayofyear
        curr_sin = math.sin(2.0 * math.pi * curr_doy / 365.25)
        curr_cos = math.cos(2.0 * math.pi * curr_doy / 365.25)

        # 1. Step 1: Initial GLM fit (Poisson)
        formula = f"{value_col} ~ t + sin_harmonic + cos_harmonic"
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                model = smf.glm(formula=formula, data=past_df, family=sm.families.Poisson()).fit()

                # 2. Step 2: Compute Anscombe residuals to down-weight past outbreaks
                fitted_vals = np.maximum(model.fittedvalues.values, 0.01)
                y_vals = past_df[value_col].values
                anscombe_residuals = (3.0 / 2.0) * (y_vals ** (2.0 / 3.0) - fitted_vals ** (2.0 / 3.0)) / (fitted_vals ** (1.0 / 6.0))

                # Anscombe threshold: 2.58 (standard Farrington threshold)
                weights = np.ones(len(past_df))
                outbreak_mask = anscombe_residuals > 2.58
                weights[outbreak_mask] = (2.58 / anscombe_residuals[outbreak_mask]) ** 2

                # 3. Step 3: Re-fit quasi-Poisson with outbreak down-weighting
                refit_model = smf.glm(
                    formula=formula,
                    data=past_df,
                    family=sm.families.Poisson(),
                    freq_weights=weights,
                ).fit()

            # Predict for current observation
            pred_df = pd.DataFrame({
                "t": [current_t],
                "sin_harmonic": [curr_sin],
                "cos_harmonic": [curr_cos],
            })
            expected = float(refit_model.predict(pred_df).iloc[0])
            expected = max(expected, 0.1)

            # Dispersion parameter phi = Pearson chi2 / DoF
            phi = max(1.0, float(refit_model.pearson_chi2 / max(1, refit_model.df_resid)))

            # Variance under quasi-Poisson: Var(Y) = phi * mu
            var_y = phi * expected

            # 2/3 power transformation upper threshold (Farrington & Andrews, 1996)
            term = 1.0 + (2.0 / 3.0) * self.z_alpha * (math.sqrt(var_y) / expected)
            threshold = float(expected * max(term, 0.0) ** (1.5))
            threshold = max(threshold, expected + 1.0)

            # Exceedance and p-value
            exceedance = current_val / threshold
            z = (current_val - expected) / math.sqrt(var_y)
            p_val = float(1.0 - stats.norm.cdf(z))

            sig_type = str(current_rows.get("signal_type", pd.Series(["unknown"])).iloc[0])
            geo_id = str(current_rows.get("geo_id", pd.Series(["unknown"])).iloc[0])

            return L1Result(
                signal_type=sig_type,
                geo_id=geo_id,
                obs_date=current_date_str,
                observed_count=current_val,
                expected_count=round(expected, 2),
                upper_threshold=round(threshold, 2),
                exceedance_score=round(exceedance, 3),
                p_value=round(p_val, 4),
                z_score=round(z, 2),
                algorithm="farrington_flexible",
            )
        except Exception:
            # Fallback to EARS C2 if GLM does not converge
            values = list(past_df[value_col].values) + [current_val]
            mean, thresh, z, p = EARSDetector.detect_c2(values)
            exc = current_val / max(thresh, 0.1)
            sig_type = str(current_rows.get("signal_type", pd.Series(["unknown"])).iloc[0])
            geo_id = str(current_rows.get("geo_id", pd.Series(["unknown"])).iloc[0])
            return L1Result(
                signal_type=sig_type,
                geo_id=geo_id,
                obs_date=current_date_str,
                observed_count=current_val,
                expected_count=round(mean, 2),
                upper_threshold=round(thresh, 2),
                exceedance_score=round(exc, 3),
                p_value=round(p, 4),
                z_score=round(z, 2),
                algorithm="ears_c2_fallback",
            )


class L1AberrationDetector:
    """
    Unified manager running L1 epidemiological baselines (EARS C1-C3 and Farrington)
    over a dataframe of time series observations.
    """

    def __init__(self):
        self.ears = EARSDetector()
        self.farrington = FarringtonDetector()

    def process_series(
        self,
        df: pd.DataFrame,
        current_date_str: str,
        value_col: str = "value",
        date_col: str = "obs_date",
        algorithm: str = "farrington",
    ) -> L1Result:
        """Process time series up to current date with selected algorithm."""
        if algorithm == "farrington":
            return self.farrington.fit_and_predict(df, current_date_str, value_col, date_col)

        # EARS algorithms
        past_and_curr = df[df[date_col] <= current_date_str].sort_values(by=date_col)
        vals = past_and_curr[value_col].astype(float).values.tolist()
        curr_row = past_and_curr.iloc[-1]
        observed = float(curr_row[value_col])

        if algorithm == "ears_c1":
            mean, thresh, z, p = self.ears.detect_c1(vals)
        elif algorithm == "ears_c3":
            mean, thresh, z, p = self.ears.detect_c3(vals)
        else:
            mean, thresh, z, p = self.ears.detect_c2(vals)

        exceedance = observed / max(thresh, 0.1)
        return L1Result(
            signal_type=str(curr_row.get("signal_type", "unknown")),
            geo_id=str(curr_row.get("geo_id", "unknown")),
            obs_date=current_date_str,
            observed_count=observed,
            expected_count=round(mean, 2),
            upper_threshold=round(thresh, 2),
            exceedance_score=round(exceedance, 3),
            p_value=round(p, 4),
            z_score=round(z, 2),
            algorithm=algorithm,
        )

