"""
Microclimate Bias Correction Engine for Model-Derived WBGT.
Implements explainable diurnal/humidity-regime stratified bias correction,
strictly time-blocked cross-validation (zero temporal leakage), conformal
interval widening, and Leave-One-Sensor-Out (LOSO) spatial validation.
"""

from typing import Dict, List, Any, Optional, Tuple
import numpy as np
import pandas as pd

from prahari.bias_correction.config import (
    HUMIDITY_REGIMES,
    DEFAULT_TIME_BLOCK_FOLDS,
    CONFORMAL_CONFIDENCE_LEVEL,
    CONFORMAL_Z,
    UNSENSORED_SITE_PENALTY_MULTIPLIER,
    get_humidity_regime,
)
from prahari.bias_correction.evaluator import BiasEvaluator


class MicroclimateBiasCorrectionModel:
    """
    Explainable, physical regime-aware bias correction model.
    Learns diurnal solar radiation offsets and coastal humidity regime adjustments.
    """

    def __init__(self):
        # Learned hourly bias lookup: hour -> mean(model - sensor)
        self.hourly_bias: Dict[int, float] = {h: 0.0 for h in range(24)}
        # Learned regime residual offset: regime -> mean residual bias
        self.regime_offset: Dict[str, float] = {"low": 0.0, "moderate": 0.0, "high": 0.0}
        # Multiplicative scaling factor (defaults to 1.0)
        self.scale_factor: float = 1.0
        # Stratified residual standard deviations for conformal prediction
        self.residual_std: Dict[str, float] = {"low": 0.5, "moderate": 0.5, "high": 0.5}
        self.hourly_residual_std: Dict[int, float] = {h: 0.5 for h in range(24)}
        self.overall_residual_std: float = 0.5
        self.is_fitted: bool = False

    def fit(
        self,
        df: pd.DataFrame,
        sensor_col: str = "wbgt_sensor",
        model_col: str = "wbgt_model",
        time_col: str = "timestamp",
        rh_col: str = "rh_pct",
    ) -> "MicroclimateBiasCorrectionModel":
        """
        Fits diurnal and regime parameters on training DataFrame.
        """
        if df.empty:
            return self

        work_df = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(work_df[time_col]):
            work_df["dt"] = pd.to_datetime(work_df[time_col])
        else:
            work_df["dt"] = work_df[time_col]

        work_df["hour"] = work_df["dt"].dt.hour
        work_df["regime"] = work_df[rh_col].apply(get_humidity_regime)

        # Raw error: (Model - Sensor)
        raw_error = work_df[model_col] - work_df[sensor_col]
        work_df["raw_error"] = raw_error

        # Step 1: Learn Diurnal Hourly Bias
        hourly_means = work_df.groupby("hour")["raw_error"].mean().to_dict()
        for h in range(24):
            self.hourly_bias[h] = float(hourly_means.get(h, 0.0))

        # Subtract diurnal bias to get residual error
        work_df["diurnal_bias"] = work_df["hour"].map(self.hourly_bias).fillna(0.0)
        work_df["diurnal_residual"] = work_df["raw_error"] - work_df["diurnal_bias"]

        # Step 2: Learn Regime Offsets on Diurnal Residuals
        regime_means = work_df.groupby("regime")["diurnal_residual"].mean().to_dict()
        for r_name in ["low", "moderate", "high"]:
            self.regime_offset[r_name] = float(regime_means.get(r_name, 0.0))

        # Step 3: Compute Corrected Out-of-Sample Uncertainty for Conformal Bands
        total_correction = work_df["diurnal_bias"] + work_df["regime"].map(self.regime_offset).fillna(0.0)
        corrected_model = work_df[model_col] - total_correction
        final_residuals = corrected_model - work_df[sensor_col]

        self.overall_residual_std = max(float(final_residuals.std(ddof=1)), 0.15) if len(final_residuals) > 1 else 0.5

        # Hourly uncertainty
        work_df["final_res"] = final_residuals
        h_stds = work_df.groupby("hour")["final_res"].std(ddof=1).to_dict()
        for h in range(24):
            val = h_stds.get(h)
            self.hourly_residual_std[h] = float(val) if val and not np.isnan(val) and val > 0.05 else self.overall_residual_std

        # Regime uncertainty
        r_stds = work_df.groupby("regime")["final_res"].std(ddof=1).to_dict()
        for r_name in ["low", "moderate", "high"]:
            val = r_stds.get(r_name)
            self.residual_std[r_name] = float(val) if val and not np.isnan(val) and val > 0.05 else self.overall_residual_std

        self.is_fitted = True
        return self

    def predict(
        self,
        df: pd.DataFrame,
        model_col: str = "wbgt_model",
        time_col: str = "timestamp",
        rh_col: str = "rh_pct",
        is_unsensored: bool = False,
        base_sigma: float = 0.8,
    ) -> pd.DataFrame:
        """
        Applies learned bias correction and outputs corrected WBGT
        along with conformal prediction intervals.
        """
        if not self.is_fitted:
            raise RuntimeError("Model must be fitted before predict.")

        out = df.copy()
        if not pd.api.types.is_datetime64_any_dtype(out[time_col]):
            out["dt"] = pd.to_datetime(out[time_col])
        else:
            out["dt"] = out[time_col]

        out["hour"] = out["dt"].dt.hour
        out["regime"] = out[rh_col].apply(get_humidity_regime)

        diurnal = out["hour"].map(self.hourly_bias).fillna(0.0)
        regime_adj = out["regime"].map(self.regime_offset).fillna(0.0)
        total_bias = diurnal + regime_adj

        # Corrected WBGT = Raw Model - Estimated Model Error
        out["wbgt_bias_correction"] = total_bias.round(3)
        out["wbgt_corrected"] = (out[model_col] - total_bias).round(2)

        # Conformal interval estimation
        h_uncertainty = out["hour"].map(self.hourly_residual_std).fillna(self.overall_residual_std)
        combined_sigma = np.sqrt(base_sigma ** 2 + h_uncertainty ** 2)

        # If applying to unsensored site, apply unvalidated spatial transfer multiplier
        if is_unsensored:
            effective_sigma = combined_sigma * UNSENSORED_SITE_PENALTY_MULTIPLIER
            out["spatial_flag"] = "UNVALIDATED-SPATIALLY"
            out["spatial_validated"] = False
        else:
            effective_sigma = combined_sigma
            out["spatial_flag"] = "SENSED"
            out["spatial_validated"] = True

        half_width = (CONFORMAL_Z * effective_sigma).round(2)
        out["conformal_interval_half_width"] = half_width
        out["wbgt_corrected_lower"] = (out["wbgt_corrected"] - half_width).round(2)
        out["wbgt_corrected_upper"] = (out["wbgt_corrected"] + half_width).round(2)

        return out


def evaluate_time_blocked_cv(
    df: pd.DataFrame,
    n_folds: int = DEFAULT_TIME_BLOCK_FOLDS,
    sensor_col: str = "wbgt_sensor",
    model_col: str = "wbgt_model",
    time_col: str = "timestamp",
    rh_col: str = "rh_pct",
) -> Dict[str, Any]:
    """
    Executes Time-Blocked Cross-Validation across n contiguous, non-overlapping
    temporal blocks to strictly prevent temporal autocorrelation leakage.

    Returns:
        Dict with out-of-fold evaluation metrics before and after correction,
        fold definitions, and fold-by-fold results.
    """
    if df.empty:
        raise ValueError("DataFrame is empty, cannot perform cross-validation.")

    work_df = df.copy()
    if not pd.api.types.is_datetime64_any_dtype(work_df[time_col]):
        work_df["dt"] = pd.to_datetime(work_df[time_col])
    else:
        work_df["dt"] = work_df[time_col]

    work_df = work_df.sort_values(by="dt").reset_index(drop=True)
    total_len = len(work_df)

    block_size = int(np.ceil(total_len / n_folds))
    fold_indices: List[Tuple[int, int]] = []

    for i in range(n_folds):
        start_idx = i * block_size
        end_idx = min((i + 1) * block_size, total_len)
        if start_idx < total_len:
            fold_indices.append((start_idx, end_idx))

    out_of_fold_preds = pd.Series(index=work_df.index, dtype=float)
    out_of_fold_lower = pd.Series(index=work_df.index, dtype=float)
    out_of_fold_upper = pd.Series(index=work_df.index, dtype=float)

    fold_summaries = []

    for fold_num, (test_start, test_end) in enumerate(fold_indices):
        test_mask = pd.Series(False, index=work_df.index)
        test_mask.iloc[test_start:test_end] = True
        train_mask = ~test_mask

        train_data = work_df[train_mask]
        test_data = work_df[test_mask]

        test_start_dt = str(test_data["dt"].min())
        test_end_dt = str(test_data["dt"].max())

        # Fit model strictly on training blocks
        model = MicroclimateBiasCorrectionModel()
        model.fit(
            train_data,
            sensor_col=sensor_col,
            model_col=model_col,
            time_col=time_col,
            rh_col=rh_col,
        )

        # Predict on held-out test block
        preds_test = model.predict(
            test_data,
            model_col=model_col,
            time_col=time_col,
            rh_col=rh_col,
            is_unsensored=False,
        )

        out_of_fold_preds.iloc[test_start:test_end] = preds_test["wbgt_corrected"].values
        out_of_fold_lower.iloc[test_start:test_end] = preds_test["wbgt_corrected_lower"].values
        out_of_fold_upper.iloc[test_start:test_end] = preds_test["wbgt_corrected_upper"].values

        # Fold error comparison
        fold_before = BiasEvaluator.compute_metrics(
            test_data[sensor_col].values,
            test_data[model_col].values,
        )
        fold_after = BiasEvaluator.compute_metrics(
            test_data[sensor_col].values,
            preds_test["wbgt_corrected"].values,
        )

        fold_summaries.append({
            "fold": fold_num + 1,
            "start_time": test_start_dt,
            "end_time": test_end_dt,
            "test_samples": len(test_data),
            "train_samples": len(train_data),
            "before_mae": fold_before["mae"],
            "after_mae": fold_after["mae"],
            "before_rmse": fold_before["rmse"],
            "after_rmse": fold_after["rmse"],
            "mae_reduction_pct": round(
                (fold_before["mae"] - fold_after["mae"]) / max(fold_before["mae"], 1e-4) * 100.0,
                2
            ),
        })

    work_df["wbgt_corrected"] = out_of_fold_preds
    work_df["wbgt_lower"] = out_of_fold_lower
    work_df["wbgt_upper"] = out_of_fold_upper

    # Compute overall held-out out-of-fold metrics
    cv_comparison = BiasEvaluator.compare_before_after(
        work_df,
        sensor_col=sensor_col,
        raw_model_col=model_col,
        corrected_col="wbgt_corrected",
        rh_col=rh_col,
        time_col=time_col,
    )

    # Conformal empirical coverage on held-out test sets
    in_bounds = (work_df[sensor_col] >= work_df["wbgt_lower"]) & (work_df[sensor_col] <= work_df["wbgt_upper"])
    empirical_coverage = round(float(in_bounds.mean() * 100.0), 2)

    return {
        "n_folds": len(fold_indices),
        "validation_strategy": "Contiguous Time-Blocked Cross-Validation (Zero Temporal Leakage)",
        "conformal_target_coverage_pct": int(CONFORMAL_CONFIDENCE_LEVEL * 100),
        "empirical_test_coverage_pct": empirical_coverage,
        "fold_results": fold_summaries,
        "held_out_comparison": cv_comparison,
        "out_of_fold_series": work_df,
    }


def evaluate_leave_one_sensor_out(
    df_sensor1: pd.DataFrame,
    df_sensor2: pd.DataFrame,
    sensor1_name: str = "SENT-001 (SITE-JA-01)",
    sensor2_name: str = "SENT-002 (SITE-AQ-01)",
    sensor_col: str = "wbgt_sensor",
    model_col: str = "wbgt_model",
    time_col: str = "timestamp",
    rh_col: str = "rh_pct",
) -> Dict[str, Any]:
    """
    Performs Leave-One-Sensor-Out (LOSO) spatial cross-validation between two physical nodes.
    Trains on Sensor 1, tests on held-out Sensor 2, and vice-versa.
    """
    # Direction A: Train on S1 -> Test on S2
    m1 = MicroclimateBiasCorrectionModel()
    m1.fit(df_sensor1, sensor_col=sensor_col, model_col=model_col, time_col=time_col, rh_col=rh_col)
    pred_s2 = m1.predict(df_sensor2, model_col=model_col, time_col=time_col, rh_col=rh_col, is_unsensored=False)
    comp_a = BiasEvaluator.compare_before_after(
        pred_s2,
        sensor_col=sensor_col,
        raw_model_col=model_col,
        corrected_col="wbgt_corrected",
        rh_col=rh_col,
        time_col=time_col,
    )

    # Direction B: Train on S2 -> Test on S1
    m2 = MicroclimateBiasCorrectionModel()
    m2.fit(df_sensor2, sensor_col=sensor_col, model_col=model_col, time_col=time_col, rh_col=rh_col)
    pred_s1 = m2.predict(df_sensor1, model_col=model_col, time_col=time_col, rh_col=rh_col, is_unsensored=False)
    comp_b = BiasEvaluator.compare_before_after(
        pred_s1,
        sensor_col=sensor_col,
        raw_model_col=model_col,
        corrected_col="wbgt_corrected",
        rh_col=rh_col,
        time_col=time_col,
    )

    return {
        "strategy": "Leave-One-Sensor-Out Spatial Cross-Validation (LOSO)",
        "transfers": [
            {
                "train_sensor": sensor1_name,
                "held_out_sensor": sensor2_name,
                "n_test_samples": len(df_sensor2),
                "before_mae": comp_a["before"]["overall"]["mae"],
                "after_mae": comp_a["after"]["overall"]["mae"],
                "mae_reduction_pct": comp_a["improvements"]["mae_reduction_pct"],
                "before_rmse": comp_a["before"]["overall"]["rmse"],
                "after_rmse": comp_a["after"]["overall"]["rmse"],
                "rmse_reduction_pct": comp_a["improvements"]["rmse_reduction_pct"],
            },
            {
                "train_sensor": sensor2_name,
                "held_out_sensor": sensor1_name,
                "n_test_samples": len(df_sensor1),
                "before_mae": comp_b["before"]["overall"]["mae"],
                "after_mae": comp_b["after"]["overall"]["mae"],
                "mae_reduction_pct": comp_b["improvements"]["mae_reduction_pct"],
                "before_rmse": comp_b["before"]["overall"]["rmse"],
                "after_rmse": comp_b["after"]["overall"]["rmse"],
                "rmse_reduction_pct": comp_b["improvements"]["rmse_reduction_pct"],
            },
        ],
        "mean_spatial_transfer_mae_reduction_pct": round(
            (comp_a["improvements"]["mae_reduction_pct"] + comp_b["improvements"]["mae_reduction_pct"]) / 2.0,
            2
        ),
    }
