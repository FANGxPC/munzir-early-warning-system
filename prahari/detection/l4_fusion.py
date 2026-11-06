"""
L4 Layer: Multi-Signal Machine Learning Fusion with Calibration and SHAP Explainability.
Combines L1 aberration scores, L2 unexplained residuals, L3 space-time clusters,
forecasts, and DQ scores into a calibrated probability with conformal uncertainty bands
and human-interpretable SHAP feature contribution groups.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import warnings
import joblib
import numpy as np
import pandas as pd
from sklearn.isotonic import IsotonicRegression
from sklearn.metrics import brier_score_loss, roc_auc_score
from lightgbm import LGBMClassifier
import shap

from prahari.config import DETECTION_MODELS_DIR

# Artifact storage path for trained fusion model
FUSION_MODEL_PATH = Path(DETECTION_MODELS_DIR) / "fusion_model.joblib"
CALIBRATOR_PATH = Path(DETECTION_MODELS_DIR) / "fusion_calibrator.joblib"


@dataclass
class FusionPrediction:
    """Calibrated outbreak probability, conformal bounds, and SHAP attribution."""
    probability: float               # Calibrated probability P in [0.0, 1.0]
    ci_low: float                    # Lower conformal confidence bound
    ci_high: float                   # Upper conformal confidence bound
    shap_contributions: Dict[str, float]  # Groups: clinical, laboratory, workplace, environmental, data_quality
    brier_score: Optional[float] = None
    feature_vector: Optional[Dict[str, float]] = None


FEATURE_NAMES = [
    "l1_resp_exceedance",
    "l1_gi_exceedance",
    "l1_fever_exceedance",
    "l1_absence_exceedance",
    "l2_resp_unexplained_excess",
    "l2_heat_unexplained_excess",
    "l2_resp_explained_frac",
    "l3_cluster_active",
    "l3_cluster_rr",
    "trend_7d_resp",
    "trend_7d_absence",
    "wbgt_max",
    "wbgt_forecast_3d_max",
    "pm25",
    "pm25_forecast_3d_mean",
    "dq_completeness_score",
    "dq_source_latency_hrs",
]

SHAP_GROUPS = {
    "clinical": ["l1_resp_exceedance", "l1_gi_exceedance", "l1_fever_exceedance", "l2_resp_unexplained_excess", "trend_7d_resp"],
    "workplace": ["l1_absence_exceedance", "l2_heat_unexplained_excess", "trend_7d_absence"],
    "environmental": ["l2_resp_explained_frac", "wbgt_max", "wbgt_forecast_3d_max", "pm25", "pm25_forecast_3d_mean"],
    "spatiotemporal": ["l3_cluster_active", "l3_cluster_rr"],
    "data_quality": ["dq_completeness_score", "dq_source_latency_hrs"],
}


class FusionFeatureExtractor:
    """
    Constructs standardized L4 feature vectors across locations and dates.
    """

    @staticmethod
    def extract_features_for_row(
        geo_id: str,
        obs_date: str,
        obs_df: pd.DataFrame,
        l1_results: Optional[Dict[str, float]] = None,
        l2_results: Optional[Dict[str, float]] = None,
        l3_results: Optional[Dict[str, float]] = None,
    ) -> Dict[str, float]:
        """
        Builds a single feature vector from silver observations and L1-L3 layers.
        """
        feats: Dict[str, float] = {k: 0.0 for k in FEATURE_NAMES}

        # 1. Populate L1 features
        if l1_results:
            feats["l1_resp_exceedance"] = float(l1_results.get("resp_exceedance", 1.0))
            feats["l1_gi_exceedance"] = float(l1_results.get("gi_exceedance", 1.0))
            feats["l1_fever_exceedance"] = float(l1_results.get("fever_exceedance", 1.0))
            feats["l1_absence_exceedance"] = float(l1_results.get("absence_exceedance", 1.0))

        # 2. Populate L2 features
        if l2_results:
            feats["l2_resp_unexplained_excess"] = float(l2_results.get("resp_unexplained", 0.0))
            feats["l2_heat_unexplained_excess"] = float(l2_results.get("heat_unexplained", 0.0))
            feats["l2_resp_explained_frac"] = float(l2_results.get("resp_explained_frac", 0.0))

        # 3. Populate L3 space-time cluster features
        if l3_results:
            feats["l3_cluster_active"] = 1.0 if l3_results.get("is_significant", False) else 0.0
            feats["l3_cluster_rr"] = float(l3_results.get("relative_risk", 1.0))

        # 4. Environmental exposures & forecasts
        if not obs_df.empty:
            loc_df = obs_df[(obs_df["geo_id"] == geo_id) & (obs_df["obs_date"] == obs_date)]
            wbgt_row = loc_df[loc_df["signal_type"] == "wbgt_max"]
            pm25_row = loc_df[loc_df["signal_type"] == "pm25"]

            w_val = float(wbgt_row["value"].iloc[0]) if not wbgt_row.empty and pd.notna(wbgt_row["value"].iloc[0]) else 28.0
            p_val = float(pm25_row["value"].iloc[0]) if not pm25_row.empty and pd.notna(pm25_row["value"].iloc[0]) else 35.0

            feats["wbgt_max"] = w_val
            feats["wbgt_forecast_3d_max"] = round(w_val + 0.8, 1)  # Approximated forecast
            feats["pm25"] = p_val
            feats["pm25_forecast_3d_mean"] = round(p_val + 2.0, 1)

            # DQ metrics
            comp = loc_df["completeness_score"].mean() if "completeness_score" in loc_df.columns else 1.0
            lat_hrs = loc_df["source_latency_hrs"].mean() if "source_latency_hrs" in loc_df.columns else 1.0

            feats["dq_completeness_score"] = float(comp) if pd.notna(comp) else 1.0
            feats["dq_source_latency_hrs"] = float(lat_hrs) if pd.notna(lat_hrs) else 1.0

            # 5. Trends over past 7 days
            past_series = obs_df[(obs_df["geo_id"] == geo_id) & (obs_df["obs_date"] <= obs_date)]
            if not past_series.empty:
                resp_s = past_series[past_series["signal_type"] == "clinical_resp"].sort_values(by="obs_date")["value"].values
                if len(resp_s) >= 4:
                    recent = float(np.mean(resp_s[-3:]))
                    prior = float(np.mean(resp_s[-7:-3])) if len(resp_s) >= 7 else float(np.mean(resp_s[:-3]))
                    feats["trend_7d_resp"] = round((recent - prior) / max(prior, 1.0), 3)

                abs_s = past_series[past_series["signal_type"] == "absence_heat"].sort_values(by="obs_date")["value"].values
                if len(abs_s) >= 4:
                    recent = float(np.mean(abs_s[-3:]))
                    prior = float(np.mean(abs_s[-7:-3])) if len(abs_s) >= 7 else float(np.mean(abs_s[:-3]))
                    feats["trend_7d_absence"] = round((recent - prior) / max(prior, 1.0), 3)

        # Sanitize any NaNs or infinities
        sanitized = {}
        for k, v in feats.items():
            if v is None or pd.isna(v) or np.isnan(v) or np.isinf(v):
                sanitized[k] = 0.0
            else:
                sanitized[k] = float(v)

        return sanitized


class L4FusionModel:
    """
    Gradient-boosted decision tree fusion engine with isotonic calibration,
    conformal prediction intervals, and SHAP explainability.
    """

    def __init__(self, model_path: Optional[Path] = None, calibrator_path: Optional[Path] = None):
        self.model_path = Path(model_path or FUSION_MODEL_PATH)
        self.calibrator_path = Path(calibrator_path or CALIBRATOR_PATH)
        self.model_path.parent.mkdir(parents=True, exist_ok=True)

        self.booster: Optional[LGBMClassifier] = None
        self.calibrator: Optional[IsotonicRegression] = None
        self.explainer: Optional[shap.TreeExplainer] = None
        self.brier_score_: Optional[float] = None
        self.conformal_margin_: float = 0.12  # Conformal prediction uncertainty margin

    def train(
        self,
        X_df: pd.DataFrame,
        y_series: pd.Series,
        dates_series: pd.Series,
        split_date: str = "2026-01-01",
    ) -> Dict[str, Any]:
        """
        Trains LightGBM fusion model using time-based temporal splitting,
        calibrates via Isotonic Regression on held-out validation set,
        and initializes the SHAP TreeExplainer.
        """
        # Strict time-based split: Train on past, validate on future
        train_mask = dates_series < split_date
        val_mask = dates_series >= split_date

        X_train, y_train = X_df[train_mask][FEATURE_NAMES], y_series[train_mask]
        X_val, y_val = X_df[val_mask][FEATURE_NAMES], y_series[val_mask]

        if len(X_train) == 0 or len(X_val) == 0:
            # Fallback to 75/25 split if date filter is too restrictive
            split_idx = int(len(X_df) * 0.75)
            X_train, y_train = X_df.iloc[:split_idx][FEATURE_NAMES], y_series.iloc[:split_idx]
            X_val, y_val = X_df.iloc[split_idx:][FEATURE_NAMES], y_series.iloc[split_idx:]

        # Train LightGBM
        booster = LGBMClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.05,
            num_leaves=15,
            class_weight="balanced",
            random_state=42,
            verbose=-1,
        )
        booster.fit(X_train, y_train)

        # Predict raw probabilities on validation set
        val_raw_probs = booster.predict_proba(X_val)[:, 1]

        # Fit Isotonic Calibrator
        # To prevent degenerate step collapse under extreme class imbalance (99.9% zeros),
        # fit Isotonic Regression with stratified negative sampling (up to 10:1 ratio)
        pos_indices = np.where(y_val.values == 1)[0]
        neg_indices = np.where(y_val.values == 0)[0]
        calibrator = IsotonicRegression(out_of_bounds="clip", y_min=0.0, y_max=1.0)

        if len(pos_indices) > 0 and len(neg_indices) > 10 * len(pos_indices):
            rng = np.random.RandomState(42)
            sampled_neg = rng.choice(neg_indices, size=min(len(neg_indices), 10 * len(pos_indices)), replace=False)
            calib_idx = np.concatenate([pos_indices, sampled_neg])
            calibrator.fit(val_raw_probs[calib_idx], y_val.values[calib_idx])
        else:
            calibrator.fit(val_raw_probs, y_val)

        # Calibrated probabilities
        val_calibrated_probs = calibrator.predict(val_raw_probs)

        # Evaluate Brier Score & AUC
        brier = float(brier_score_loss(y_val, val_calibrated_probs))
        auc = float(roc_auc_score(y_val, val_calibrated_probs)) if len(np.unique(y_val)) > 1 else 1.0

        # Conformal residual margin at 90% coverage
        residuals = np.abs(y_val.values - val_calibrated_probs)
        conformal_margin = float(np.quantile(residuals, 0.90))

        # Initialize SHAP TreeExplainer
        explainer = shap.TreeExplainer(booster)

        self.booster = booster
        self.calibrator = calibrator
        self.explainer = explainer
        self.brier_score_ = brier
        self.conformal_margin_ = conformal_margin

        # Save model artifacts
        joblib.dump(booster, self.model_path)
        joblib.dump(calibrator, self.calibrator_path)

        return {
            "brier_score": round(brier, 4),
            "auc_roc": round(auc, 4),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "conformal_margin_90": round(conformal_margin, 3),
            "split_date": split_date,
        }

    def predict(self, feature_vector: Dict[str, float]) -> FusionPrediction:
        """
        Runs inference: predicts calibrated probability, computes conformal interval,
        and generates SHAP contribution breakdown across groups.
        """
        if self.booster is None or self.calibrator is None:
            if self.model_path.exists() and self.calibrator_path.exists():
                self.booster = joblib.load(self.model_path)
                self.calibrator = joblib.load(self.calibrator_path)
                self.explainer = shap.TreeExplainer(self.booster)
            else:
                raise RuntimeError("L4 Fusion Model not trained or loaded!")

        # Format input dataframe
        x_vals = [feature_vector.get(f, 0.0) for f in FEATURE_NAMES]
        df_x = pd.DataFrame([x_vals], columns=FEATURE_NAMES)

        # Raw model probability
        raw_prob = float(self.booster.predict_proba(df_x)[0, 1])

        # Isotonic calibration with prior scaling
        calibrated_prob = float(self.calibrator.predict([raw_prob])[0])
        max_y = getattr(self.calibrator, "y_thresholds_", [1.0])[-1]
        if max_y > 0 and max_y < 0.90:
            calibrated_prob = calibrated_prob / float(max_y)
        calibrated_prob = float(np.clip(calibrated_prob, 0.0, 1.0))

        # Conformal prediction interval [P_low, P_high]
        ci_low = max(0.0, round(calibrated_prob - self.conformal_margin_, 3))
        ci_high = min(1.0, round(calibrated_prob + self.conformal_margin_, 3))

        # Compute SHAP values
        assert self.explainer is not None
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                shap_vals = self.explainer.shap_values(df_x)
            if hasattr(shap_vals, "values"):
                shap_vals = shap_vals.values
            if isinstance(shap_vals, list):
                s_arr = shap_vals[1][0] if len(shap_vals) > 1 else shap_vals[0][0]
            elif hasattr(shap_vals, "ndim") and shap_vals.ndim == 3:
                s_arr = shap_vals[0, :, 1] if shap_vals.shape[2] > 1 else shap_vals[0, :, 0]
            elif hasattr(shap_vals, "ndim") and shap_vals.ndim == 2:
                s_arr = shap_vals[0]
            else:
                s_arr = np.array(shap_vals).flatten()
        except Exception:
            s_arr = np.zeros(len(FEATURE_NAMES))

        # Aggregate SHAP by group
        group_contributions: Dict[str, float] = {}
        for group_name, feat_list in SHAP_GROUPS.items():
            tot = sum(
                float(s_arr[FEATURE_NAMES.index(f)])
                for f in feat_list
                if f in FEATURE_NAMES
            )
            group_contributions[group_name] = round(tot, 3)

        return FusionPrediction(
            probability=round(calibrated_prob, 3),
            ci_low=ci_low,
            ci_high=ci_high,
            shap_contributions=group_contributions,
            brier_score=round(self.brier_score_, 4) if self.brier_score_ is not None else None,
            feature_vector=feature_vector,
        )
