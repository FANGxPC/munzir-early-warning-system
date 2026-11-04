"""
Tests for L4 Multi-Signal ML Fusion and L5 Anti-Alert-Fatigue Policy Engine.
"""

import pytest
import numpy as np
import pandas as pd
from prahari.detection.l4_fusion import (
    L4FusionModel,
    FusionFeatureExtractor,
    FusionPrediction,
    FEATURE_NAMES,
)
from prahari.detection.l5_policy import (
    L5AlertPolicyEngine,
    PrahariAlert,
    AlertSeverity,
)


def test_fusion_feature_extractor():
    """Verify feature extractor assembles all 17 standardized features and computes 7d trends."""
    dates = pd.date_range("2026-05-01", periods=10).strftime("%Y-%m-%d").tolist()
    records = []
    for d in dates:
        records.append({"obs_date": d, "geo_id": "SITE-JA-01", "signal_type": "clinical_resp", "value": 15.0, "completeness_score": 0.95, "source_latency_hrs": 2.0})
        records.append({"obs_date": d, "geo_id": "SITE-JA-01", "signal_type": "absence_heat", "value": 5.0, "completeness_score": 0.95, "source_latency_hrs": 2.0})
        records.append({"obs_date": d, "geo_id": "SITE-JA-01", "signal_type": "wbgt_max", "value": 31.5, "completeness_score": 0.95, "source_latency_hrs": 2.0})
        records.append({"obs_date": d, "geo_id": "SITE-JA-01", "signal_type": "pm25", "value": 42.0, "completeness_score": 0.95, "source_latency_hrs": 2.0})

    df = pd.DataFrame(records)

    feats = FusionFeatureExtractor.extract_features_for_row(
        geo_id="SITE-JA-01",
        obs_date=dates[-1],
        obs_df=df,
        l1_results={"resp_exceedance": 1.8, "absence_exceedance": 2.1},
        l2_results={"resp_unexplained": 8.5, "heat_unexplained": 4.0},
        l3_results={"is_significant": True, "relative_risk": 2.3},
    )

    assert len(feats) == len(FEATURE_NAMES)
    for f in FEATURE_NAMES:
        assert f in feats
    assert feats["l1_resp_exceedance"] == 1.8
    assert feats["l2_heat_unexplained_excess"] == 4.0
    assert feats["l3_cluster_active"] == 1.0
    assert feats["wbgt_max"] == 31.5
    assert feats["dq_completeness_score"] == 0.95


def test_fusion_model_training_and_calibration(tmp_path):
    """
    Verify L4 model trains with time-based split, calibrates probabilities,
    evaluates Brier score, and computes 5-group SHAP contributions.
    """
    model_file = tmp_path / "fusion.joblib"
    calib_file = tmp_path / "calib.joblib"
    model = L4FusionModel(model_path=model_file, calibrator_path=calib_file)

    np.random.seed(42)
    n_samples = 200
    dates = pd.date_range("2025-01-01", periods=n_samples).strftime("%Y-%m-%d").tolist()

    # Generate synthetic feature dataframe
    data = {}
    for f in FEATURE_NAMES:
        data[f] = np.random.uniform(0.0, 3.0, size=n_samples)

    # Injected correlation with label
    y = ((data["l1_resp_exceedance"] > 1.8) & (data["l3_cluster_active"] > 0.5)).astype(int)

    X_df = pd.DataFrame(data)
    y_series = pd.Series(y)
    dates_series = pd.Series(dates)

    metrics = model.train(X_df, y_series, dates_series, split_date="2025-05-01")

    assert "brier_score" in metrics
    assert metrics["brier_score"] <= 0.25  # Good calibration
    assert metrics["auc_roc"] >= 0.70
    assert model_file.exists()
    assert calib_file.exists()

    # Inference test
    sample_feat = {f: 2.5 for f in FEATURE_NAMES}
    pred: FusionPrediction = model.predict(sample_feat)

    assert 0.0 <= pred.probability <= 1.0
    assert pred.ci_low <= pred.probability <= pred.ci_high
    assert "clinical" in pred.shap_contributions
    assert "environmental" in pred.shap_contributions
    assert "workplace" in pred.shap_contributions


def test_l5_multi_signal_corroboration_rule():
    """
    CRITICAL POLICY TEST:
    A single-signal spike can only reach WATCH.
    Warning or Alert requires at least 2 corroborating signal groups.
    """
    engine = L5AlertPolicyEngine(p_watch=0.35, p_warning=0.60, p_alert=0.80)

    # High probability (0.85), but ONLY single signal (clinical) is contributing
    single_signal_pred = FusionPrediction(
        probability=0.85,
        ci_low=0.75,
        ci_high=0.95,
        shap_contributions={
            "clinical": 0.45,
            "workplace": 0.01,
            "environmental": 0.02,
            "spatiotemporal": 0.0,
            "data_quality": 0.0,
        },
    )

    alert = engine.evaluate(single_signal_pred, geo_id="DXB-JA", obs_date="2026-06-01")
    # Must be capped at WATCH despite 85% probability!
    assert alert.severity == AlertSeverity.WATCH

    # Now add corroborating signal (environmental SHAP > 0.08)
    corroborated_pred = FusionPrediction(
        probability=0.85,
        ci_low=0.75,
        ci_high=0.95,
        shap_contributions={
            "clinical": 0.35,
            "workplace": 0.01,
            "environmental": 0.22,  # Corroborating environmental driver
            "spatiotemporal": 0.0,
            "data_quality": 0.0,
        },
    )

    alert_corrob = engine.evaluate(corroborated_pred, geo_id="DXB-JA", obs_date="2026-06-01")
    # With 2 corroborating groups, escalates to ALERT
    assert alert_corrob.severity in [AlertSeverity.WARNING, AlertSeverity.ALERT]


def test_l5_decoy_backlog_dump_suppression():
    """
    ANTI-ALERT-FATIGUE TEST:
    Sudden volume surges accompanied by high source latency (>= 48h)
    represent reporting backlog dumps and MUST NOT fire Warning or Alert.
    """
    engine = L5AlertPolicyEngine()

    backlog_pred = FusionPrediction(
        probability=0.90,
        ci_low=0.80,
        ci_high=1.00,
        shap_contributions={"clinical": 0.35, "workplace": 0.20},
        feature_vector={
            "dq_source_latency_hrs": 72.0,  # 3 days late batch dump
            "dq_completeness_score": 0.40,
        },
    )

    alert = engine.evaluate(backlog_pred, geo_id="DXB-HT", obs_date="2024-06-11")
    # Must be recognized as decoy and suppressed
    assert alert.is_suppressed_decoy is True
    assert alert.severity == AlertSeverity.WATCH
    assert alert.alert_type == "data_artefact"
    assert "backlog dump" in alert.dq_status.lower()


def test_l5_dq_gate_low_completeness():
    """
    DQ GATE TEST:
    If completeness < 0.70, severity is capped and flagged 'low confidence - missing data'.
    """
    engine = L5AlertPolicyEngine()

    low_comp_pred = FusionPrediction(
        probability=0.88,
        ci_low=0.78,
        ci_high=0.98,
        shap_contributions={"clinical": 0.30, "workplace": 0.25},
        feature_vector={"dq_completeness_score": 0.55, "dq_source_latency_hrs": 2.0},
    )

    alert = engine.evaluate(low_comp_pred, geo_id="DXB-AQ", obs_date="2026-07-01")
    assert "low confidence" in alert.dq_status.lower()
    assert alert.severity != AlertSeverity.ALERT  # Capped due to missing data
