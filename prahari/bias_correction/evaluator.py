"""
Statistical Evaluator for Model vs. Sensor WBGT Error.
Calculates Bias (MBE), MAE, RMSE, and Pearson r overall, diurnal (hourly 0-23),
and stratified by humidity regimes.
"""

from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from prahari.bias_correction.config import get_humidity_regime


class BiasEvaluator:
    """
    Computes rigorous error and correlation statistics between regional model
    forecasts and on-site Sentinel observations.
    """

    @staticmethod
    def compute_metrics(
        sensor_values: np.ndarray,
        model_values: np.ndarray,
    ) -> Dict[str, float]:
        """
        Computes Mean Bias Error, MAE, RMSE, and Pearson correlation r.
        Bias is defined as (Model - Sensor):
          - Negative bias indicates the model underestimates on-site heat stress.
          - Positive bias indicates the model overestimates on-site heat stress.
        """
        if len(sensor_values) == 0 or len(model_values) == 0:
            return {
                "n": 0,
                "bias": 0.0,
                "mae": 0.0,
                "rmse": 0.0,
                "pearson_r": 0.0,
            }

        s = np.asarray(sensor_values, dtype=float)
        m = np.asarray(model_values, dtype=float)

        diff = m - s
        bias = float(np.mean(diff))
        mae = float(np.mean(np.abs(diff)))
        rmse = float(np.sqrt(np.mean(diff ** 2)))

        std_s = float(np.std(s))
        std_m = float(np.std(m))
        if std_s > 1e-6 and std_m > 1e-6:
            r = float(np.corrcoef(s, m)[0, 1])
            if np.isnan(r):
                r = 0.0
        else:
            r = 1.0 if np.allclose(s, m) else 0.0

        return {
            "n": int(len(s)),
            "bias": round(bias, 3),
            "mae": round(mae, 3),
            "rmse": round(rmse, 3),
            "pearson_r": round(r, 4),
        }

    @classmethod
    def evaluate_series(
        cls,
        df: pd.DataFrame,
        sensor_col: str = "wbgt_sensor",
        model_col: str = "wbgt_model",
        time_col: str = "timestamp",
        rh_col: str = "rh_pct",
    ) -> Dict[str, Any]:
        """
        Evaluates model vs. sensor series across overall, diurnal hourly,
        and humidity regime stratifications.
        """
        if df.empty:
            return {"overall": cls.compute_metrics(np.array([]), np.array([]))}

        df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(df[time_col]):
            df["dt"] = pd.to_datetime(df[time_col])
        else:
            df["dt"] = df[time_col]

        df["hour"] = df["dt"].dt.hour
        df["regime"] = df[rh_col].apply(get_humidity_regime)

        # 1. Overall
        overall = cls.compute_metrics(df[sensor_col].values, df[model_col].values)

        # 2. Hourly Diurnal Profile
        hourly_profile = []
        for h in range(24):
            subset = df[df["hour"] == h]
            if len(subset) > 0:
                m = cls.compute_metrics(subset[sensor_col].values, subset[model_col].values)
                hourly_profile.append({
                    "hour": h,
                    "n": m["n"],
                    "bias": m["bias"],
                    "mae": m["mae"],
                    "rmse": m["rmse"],
                    "mean_sensor": round(float(subset[sensor_col].mean()), 2),
                    "mean_model": round(float(subset[model_col].mean()), 2),
                })
            else:
                hourly_profile.append({
                    "hour": h,
                    "n": 0,
                    "bias": 0.0,
                    "mae": 0.0,
                    "rmse": 0.0,
                    "mean_sensor": 0.0,
                    "mean_model": 0.0,
                })

        # 3. Stratified by Humidity Regime
        regimes = {}
        for r_name in ["low", "moderate", "high"]:
            subset = df[df["regime"] == r_name]
            regimes[r_name] = cls.compute_metrics(subset[sensor_col].values, subset[model_col].values)

        return {
            "overall": overall,
            "diurnal_profile": hourly_profile,
            "by_humidity_regime": regimes,
        }

    @classmethod
    def compare_before_after(
        cls,
        df: pd.DataFrame,
        sensor_col: str = "wbgt_sensor",
        raw_model_col: str = "wbgt_raw",
        corrected_col: str = "wbgt_corrected",
        rh_col: str = "rh_pct",
        time_col: str = "timestamp",
    ) -> Dict[str, Any]:
        """
        Produces a direct comparison of error metrics before and after correction.
        """
        before = cls.evaluate_series(
            df,
            sensor_col=sensor_col,
            model_col=raw_model_col,
            time_col=time_col,
            rh_col=rh_col,
        )
        after = cls.evaluate_series(
            df,
            sensor_col=sensor_col,
            model_col=corrected_col,
            time_col=time_col,
            rh_col=rh_col,
        )

        mae_improvement_pct = 0.0
        rmse_improvement_pct = 0.0
        if before["overall"]["mae"] > 0:
            mae_improvement_pct = round(
                (before["overall"]["mae"] - after["overall"]["mae"]) / before["overall"]["mae"] * 100.0,
                2
            )
        if before["overall"]["rmse"] > 0:
            rmse_improvement_pct = round(
                (before["overall"]["rmse"] - after["overall"]["rmse"]) / before["overall"]["rmse"] * 100.0,
                2
            )

        return {
            "before": before,
            "after": after,
            "improvements": {
                "mae_reduction_pct": mae_improvement_pct,
                "rmse_reduction_pct": rmse_improvement_pct,
                "bias_magnitude_before": abs(before["overall"]["bias"]),
                "bias_magnitude_after": abs(after["overall"]["bias"]),
            },
        }

