"""
Baseline Detection Models for Comparative Operational Benchmarking.
Implements standard public health baselines to prove the core value proposition:
"Fusion gives 2-4 days more lead time at the same or lower false-alarm rate."

Baselines:
1. Single-Signal Fixed Threshold: Alerts when daily count exceeds mu + 3*sigma of rolling 28-day window.
2. CDC EARS C2 on Clinical Data Only: Alerts when C2 CUSUM statistic exceeds 3.0 using 7-day baseline with 2-day guard band.
3. PRAHARI Full Fusion (L1-L5): Multi-signal exposure-adjusted fusion with calibrated LightGBM and anti-fatigue policy.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd


class FixedThresholdDetector:
    """
    Baseline A: Naive single-signal fixed threshold.
    Alerts when current value > mu + 3 * sigma over a 28-day trailing window.
    """

    def __init__(self, window_days: int = 28, sigma_mult: float = 3.0):
        self.window_days = window_days
        self.sigma_mult = sigma_mult

    def evaluate_series(self, series: pd.Series) -> pd.Series:
        """
        Takes a daily time series and returns a boolean series of alerts (True = Alert).
        Uses shift(1) to avoid look-ahead bias.
        """
        rolling_mean = series.shift(1).rolling(window=self.window_days, min_periods=7).mean()
        rolling_std = series.shift(1).rolling(window=self.window_days, min_periods=7).std().fillna(1.0)
        threshold = rolling_mean + (self.sigma_mult * rolling_std)
        # Alert if count strictly exceeds threshold and count >= 5
        alerts = (series > threshold) & (series >= 5.0)
        return alerts.fillna(False)


class EarsC2Detector:
    """
    Baseline B: CDC Early Aberration Reporting System (EARS) C2 algorithm.
    Evaluates clinical syndromic data only.
    Uses 7-day baseline window with a 2-day guard band [t-9 to t-3].
    Alerts when C2 = (Y_t - mu) / sigma > 3.0.
    """

    def __init__(self, baseline_len: int = 7, guard_band: int = 2, threshold_z: float = 3.0):
        self.baseline_len = baseline_len
        self.guard_band = guard_band
        self.threshold_z = threshold_z

    def evaluate_series(self, series: pd.Series) -> pd.Series:
        """
        Takes daily clinical time series and returns boolean alerts.
        """
        # Guard band shifts baseline by 2 days prior to today
        shifted = series.shift(self.guard_band + 1)
        base_mean = shifted.rolling(window=self.baseline_len, min_periods=4).mean()
        base_std = shifted.rolling(window=self.baseline_len, min_periods=4).std().fillna(1.0)
        base_std = base_std.apply(lambda s: max(s, 1.0))

        z_score = (series - base_mean) / base_std
        alerts = (z_score > self.threshold_z) & (series >= 5.0)
        return alerts.fillna(False)


class BaselineBenchmarkEngine:
    """
    Runs side-by-side detection across all three paradigms:
    - Single-Signal Threshold
    - CDC EARS C2
    - PRAHARI Full Fusion
    """

    def __init__(self):
        self.fixed_detector = FixedThresholdDetector()
        self.ears_detector = EarsC2Detector()

    def run_baselines_on_location(
        self,
        df_location_daily: pd.DataFrame,
        primary_signal: str = "clinical_resp",
    ) -> pd.DataFrame:
        """
        Applies Baseline A and Baseline B to the primary clinical signal for a location.
        Returns dataframe with boolean columns 'alert_fixed_threshold' and 'alert_ears_c2'.
        """
        df = df_location_daily.sort_values("obs_date").copy()
        sig_df = df[df["signal_type"] == primary_signal]

        if sig_df.empty:
            df["alert_fixed_threshold"] = False
            df["alert_ears_c2"] = False
            return df

        sig_series = pd.Series(sig_df["value"].values, index=sig_df["obs_date"])

        alerts_fixed = self.fixed_detector.evaluate_series(sig_series)
        alerts_ears = self.ears_detector.evaluate_series(sig_series)

        # Map back to date
        fixed_map = dict(zip(sig_series.index, alerts_fixed.values))
        ears_map = dict(zip(sig_series.index, alerts_ears.values))

        df["alert_fixed_threshold"] = df["obs_date"].map(fixed_map).fillna(False)
        df["alert_ears_c2"] = df["obs_date"].map(ears_map).fillna(False)

        return df

