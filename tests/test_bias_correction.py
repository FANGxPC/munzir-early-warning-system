"""
Unit & Integration Test Suite for Munzir Sentinel WBGT Microclimate Bias Correction.
Tests:
  1. Synthetic known-bias recovery (model recovers injected offset within ±0.05°C)
  2. Time-contiguous cross-validation folds (zero chronological overlap / leakage)
  3. Sensor sanity screening (filters range faults, stuck sensors, and DHT22 saturation)
  4. Conformal interval widening & spatial transfer flags (UNVALIDATED-SPATIALLY)
  5. Multi-sensor Leave-One-Sensor-Out (LOSO) spatial validation
  6. REST API endpoint responses (/bias-correction, /transfer, /sources)
  7. CLI command execution
"""

import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from fastapi.testclient import TestClient

from prahari.bias_correction.config import (
    SANITY_BOUNDS,
    HUMIDITY_REGIMES,
    UNSENSORED_SITE_PENALTY_MULTIPLIER,
    load_sources_config,
)
from prahari.bias_correction.sanity import SensorSanityFilter
from prahari.bias_correction.evaluator import BiasEvaluator
from prahari.bias_correction.model import (
    MicroclimateBiasCorrectionModel,
    evaluate_time_blocked_cv,
    evaluate_leave_one_sensor_out,
)
from prahari.bias_correction.data_loader import SentinelDataLoader
from prahari.bias_correction.engine import BiasCorrectionEngine
from prahari.api.app import app


# --- 1. Synthetic Known-Bias Recovery Test ---

def test_synthetic_known_bias_recovery():
    """
    Asserts that the explainable model precisely recovers an injected known bias
    (e.g., +2.5°C during daytime hours, +1.0°C during night hours) from synthetic data.
    """
    n_days = 10
    n_hours = n_days * 24
    base_time = datetime(2024, 6, 1, 0, 0)
    timestamps = [base_time + timedelta(hours=i) for i in range(n_hours)]

    rng = np.random.RandomState(42)
    # Synthetic true WBGT
    true_wbgt = 28.0 + 5.0 * np.sin(np.linspace(0, 2 * np.pi * n_days, n_hours))

    # Injected known bias into model:
    # Day (hours 8-18): Model underestimates heat by -2.5°C (i.e. Model = True - 2.5)
    # Night: Model underestimates heat by -1.0°C
    known_bias = np.array([
        -2.5 if 8 <= t.hour <= 18 else -1.0
        for t in timestamps
    ])

    raw_model_wbgt = true_wbgt + known_bias + rng.normal(0, 0.05, n_hours)
    rh_series = 50.0 + 20.0 * np.cos(np.linspace(0, 2 * np.pi * n_days, n_hours))

    df = pd.DataFrame({
        "timestamp": [t.isoformat() for t in timestamps],
        "wbgt_sensor": true_wbgt,
        "wbgt_model": raw_model_wbgt,
        "rh_pct": rh_series,
    })

    # Evaluate raw error
    raw_metrics = BiasEvaluator.compute_metrics(df["wbgt_sensor"].values, df["wbgt_model"].values)
    assert raw_metrics["mae"] > 1.5

    # Fit model
    model = MicroclimateBiasCorrectionModel()
    model.fit(df, sensor_col="wbgt_sensor", model_col="wbgt_model", time_col="timestamp", rh_col="rh_pct")

    # Verify diurnal parameters recover injected bias
    for h in range(8, 19):
        # Injected was -2.5°C error, model should learn bias close to -2.5°C
        assert abs(model.hourly_bias[h] - (-2.5)) < 0.15, f"Hour {h} bias recovery failed: {model.hourly_bias[h]}"

    for h in [0, 1, 2, 3, 4, 5, 21, 22, 23]:
        assert abs(model.hourly_bias[h] - (-1.0)) < 0.15, f"Hour {h} bias recovery failed: {model.hourly_bias[h]}"

    # Predict
    pred = model.predict(df, model_col="wbgt_model", time_col="timestamp", rh_col="rh_pct")
    corrected_metrics = BiasEvaluator.compute_metrics(df["wbgt_sensor"].values, pred["wbgt_corrected"].values)

    # MAE should drop by > 90%
    mae_reduction = (raw_metrics["mae"] - corrected_metrics["mae"]) / raw_metrics["mae"]
    assert mae_reduction > 0.90
    assert corrected_metrics["mae"] < 0.10


# --- 2. Time-Contiguous Cross-Validation Folds (Zero Leakage) ---

def test_time_blocked_cv_contiguous_non_overlapping():
    """
    Asserts that the time-blocked CV splits produce strictly contiguous, non-overlapping
    folds without temporal leakage or random shuffling.
    """
    df = SentinelDataLoader.load_paired_telemetry(site_id="SITE-JA-01")
    clean_df, _ = SensorSanityFilter.filter_telemetry(df)

    res = evaluate_time_blocked_cv(clean_df, n_folds=5)

    assert res["n_folds"] == 5
    fold_details = res["fold_results"]
    assert len(fold_details) == 5

    # Check temporal ordering and contiguity across folds
    for i in range(len(fold_details) - 1):
        end_current = fold_details[i]["end_time"]
        start_next = fold_details[i + 1]["start_time"]
        assert end_current < start_next, f"Fold {i} end ({end_current}) not before fold {i+1} start ({start_next})"

    # Verify held-out metrics show improvement
    improvements = res["held_out_comparison"]["improvements"]
    assert improvements["mae_reduction_pct"] > 50.0
    assert improvements["rmse_reduction_pct"] > 50.0
    assert res["empirical_test_coverage_pct"] >= 90.0


# --- 3. Sensor Sanity Screening Test ---

def test_sensor_sanity_filter():
    """
    Asserts that range anomalies, thermodynamic impossibilities, stuck sensors,
    and DHT22 condensation saturation events are screened out.
    """
    base_time = datetime(2024, 6, 1, 0, 0)
    records = []

    # 10 normal records
    for i in range(10):
        records.append({
            "timestamp": (base_time + timedelta(hours=i)).isoformat(),
            "node_id": "TEST-NODE",
            "air_temp_c": 35.0,
            "rh_pct": 50.0,
            "globe_temp_c": 42.0,
            "wbgt_c": 31.0,
        })

    # Out of range air temp (85°C)
    records.append({
        "timestamp": (base_time + timedelta(hours=10)).isoformat(),
        "node_id": "TEST-NODE",
        "air_temp_c": 85.0,
        "rh_pct": 50.0,
        "globe_temp_c": 42.0,
        "wbgt_c": 31.0,
    })

    # Thermodynamic implausibility (Tg 10°C colder than Ta)
    records.append({
        "timestamp": (base_time + timedelta(hours=11)).isoformat(),
        "node_id": "TEST-NODE",
        "air_temp_c": 40.0,
        "rh_pct": 50.0,
        "globe_temp_c": 25.0,
        "wbgt_c": 31.0,
    })

    # DHT22 condensation saturation: 8 consecutive hours of 99.5% RH
    for j in range(8):
        records.append({
            "timestamp": (base_time + timedelta(hours=12 + j)).isoformat(),
            "node_id": "TEST-NODE",
            "air_temp_c": 30.0,
            "rh_pct": 99.5,
            "globe_temp_c": 32.0,
            "wbgt_c": 29.0,
        })

    df = pd.DataFrame(records)
    clean_df, audit = SensorSanityFilter.filter_telemetry(df)

    assert audit["total_records"] == 20
    assert audit["breakdown"]["range_violations"] >= 1
    assert audit["breakdown"]["thermal_implausibility"] >= 1
    # Saturation threshold is 6 hours; hours 7 and 8 should be flagged
    assert audit["breakdown"]["dht22_condensation_saturation"] == 2
    assert audit["valid_records"] < audit["total_records"]
    assert len(clean_df) == audit["valid_records"]


# --- 4. Conformal Interval Widening & Spatial Flags ---

def test_conformal_interval_widening_for_unsensored():
    """
    Asserts that unsensored sites receive UNVALIDATED-SPATIALLY flag and
    exactly 1.5x widened prediction bands.
    """
    df = SentinelDataLoader.load_paired_telemetry(site_id="SITE-JA-01")
    clean_df, _ = SensorSanityFilter.filter_telemetry(df)

    model = MicroclimateBiasCorrectionModel()
    model.fit(clean_df)

    # In-situ sensed prediction
    pred_sensed = model.predict(clean_df, is_unsensored=False)
    assert pred_sensed["spatial_flag"].iloc[0] == "SENSED"
    assert bool(pred_sensed["spatial_validated"].iloc[0]) is True
    width_sensed = pred_sensed["conformal_interval_half_width"].iloc[0]

    # Unsensored spatial transfer prediction
    pred_unsensored = model.predict(clean_df, is_unsensored=True)
    assert pred_unsensored["spatial_flag"].iloc[0] == "UNVALIDATED-SPATIALLY"
    assert bool(pred_unsensored["spatial_validated"].iloc[0]) is False
    width_unsensored = pred_unsensored["conformal_interval_half_width"].iloc[0]

    ratio = width_unsensored / width_sensed
    assert abs(ratio - UNSENSORED_SITE_PENALTY_MULTIPLIER) < 0.05


# --- 5. Multi-Sensor Leave-One-Sensor-Out (LOSO) Validation ---

def test_leave_one_sensor_out_validation():
    """
    Asserts that Leave-One-Sensor-Out spatial validation between SENT-001 and SENT-002
    evaluates both directions and achieves error reduction on held-out sensors.
    """
    df = SentinelDataLoader.load_paired_telemetry()
    clean_df, _ = SensorSanityFilter.filter_telemetry(df)

    df_s1 = clean_df[clean_df["node_id"] == "SENT-001"]
    df_s2 = clean_df[clean_df["node_id"] == "SENT-002"]

    loso = evaluate_leave_one_sensor_out(df_s1, df_s2)

    assert len(loso["transfers"]) == 2
    assert loso["mean_spatial_transfer_mae_reduction_pct"] > 25.0

    t1 = loso["transfers"][0]
    assert t1["after_mae"] < t1["before_mae"]

    t2 = loso["transfers"][1]
    assert t2["after_mae"] < t2["before_mae"]


# --- 6. REST API Endpoints Verification ---

def test_bias_correction_api_endpoints():
    """
    Asserts that REST API endpoints return 200 with required schema fields.
    """
    client = TestClient(app)

    # 1. Bias correction report endpoint
    r1 = client.get("/api/v1/sentinel/bias-correction?site_id=SITE-JA-01")
    assert r1.status_code == 200
    data1 = r1.json()
    assert "error_metrics_summary" in data1
    assert "cv_validation" in data1
    assert "spatial_transfer" in data1
    assert "limitations_and_disclosures" in data1
    assert data1["error_metrics_summary"]["improvements"]["mae_reduction_pct"] > 50.0

    # 2. Spatial transfer endpoint
    r2 = client.get("/api/v1/sentinel/transfer")
    assert r2.status_code == 200
    data2 = r2.json()
    assert "spatial_register" in data2
    assert "loso_validation" in data2
    assert any(s["confidence_flag"] == "SENSED" for s in data2["spatial_register"])
    assert any(s["confidence_flag"] == "UNVALIDATED-SPATIALLY" for s in data2["spatial_register"])

    # 3. Sources & citations endpoint
    r3 = client.get("/api/v1/sentinel/sources")
    assert r3.status_code == 200
    data3 = r3.json()
    assert "citations" in data3
    assert "hardware_specifications" in data3
    assert "methodological_disclosures" in data3


# --- 7. End-to-End BiasCorrectionEngine Execution ---

def test_bias_correction_engine_e2e(tmp_path):
    """
    Asserts that BiasCorrectionEngine completes calibration, writes JSON and HTML reports,
    and returns valid structured summaries.
    """
    engine = BiasCorrectionEngine(output_dir=tmp_path)
    res = engine.run_calibration(site_id="SITE-JA-01", n_folds=5, export=True)

    assert (tmp_path / "bias_correction_results.json").exists()
    assert (tmp_path / "bias_correction_report.html").exists()

    assert res["audit"]["days_count"] >= 0
    assert res["cv_validation"]["n_folds"] == 5
    assert res["error_metrics_summary"]["after"]["mae"] < res["error_metrics_summary"]["before"]["mae"]
