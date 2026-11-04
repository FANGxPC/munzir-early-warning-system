"""
Tests for L2 Exposure-Adjusted Baseline Layer.
Distinguishes environmental/weather-explained surges from unexplained outbreak excess.
"""

import pytest
import numpy as np
import pandas as pd
from prahari.detection.l2_exposure import L2ExposureBaselineModel, L2ResidualResult


def test_l2_environment_explained_surge():
    """
    When high PM2.5 causes clinical respiratory surge, L2 model attributes
    the rise to environment (high explained_fraction, is_environment_driven=True).
    """
    model = L2ExposureBaselineModel(min_train_samples=30)
    np.random.seed(42)

    # Generate 60 days
    dates = pd.date_range("2025-06-01", periods=60).strftime("%Y-%m-%d").tolist()
    pm25_vals = np.random.uniform(20.0, 45.0, size=60)
    # On day 58-59, severe PM2.5 dust storm hits
    pm25_vals[-3:] = [140.0, 160.0, 150.0]

    # Baseline visits ~ 25 + 0.25 * lagged PM2.5
    resp_counts = []
    for i in range(60):
        lag_pm = pm25_vals[i - 1] if i > 0 else pm25_vals[i]
        expected = 25.0 + 0.25 * lag_pm
        resp_counts.append(int(np.random.poisson(expected)))

    df = pd.DataFrame({
        "obs_date": dates,
        "signal_type": "clinical_resp",
        "geo_id": "DXB-JA",
        "value": resp_counts,
        "denominator": 100000.0,
        "pm25": pm25_vals,
        "wbgt_max": [30.0] * 60,
    })

    res: L2ResidualResult = model.evaluate_date(
        merged_df=df,
        current_date_str=dates[-1],
        target_signal="clinical_resp",
        geo_id="DXB-JA",
    )

    assert res.observed > 0
    # Total excess = unexplained + explained_by_environment
    assert abs(res.total_excess - (res.unexplained_excess + res.explained_by_environment)) < 0.1
    # Since PM2.5 spiked, exposure-expected should be higher than unadjusted expected
    assert res.exposure_expected > res.unadjusted_expected
    assert res.explained_by_environment > 0


def test_l2_unexplained_outbreak_spike():
    """
    When visits spike while environmental exposure is completely normal,
    unexplained_excess should account for nearly 100% of the total excess.
    """
    model = L2ExposureBaselineModel(min_train_samples=30)
    np.random.seed(42)

    dates = pd.date_range("2025-01-01", periods=50).strftime("%Y-%m-%d").tolist()
    pm25_vals = np.random.uniform(25.0, 35.0, size=50)  # Calm, normal air quality
    resp_counts = [int(np.random.poisson(30.0)) for _ in range(49)]
    resp_counts.append(85)  # Sudden unexplained cluster spike

    df = pd.DataFrame({
        "obs_date": dates,
        "signal_type": "clinical_resp",
        "geo_id": "DXB-AQ",
        "value": resp_counts,
        "denominator": 100000.0,
        "pm25": pm25_vals,
        "wbgt_max": [25.0] * 50,
    })

    res: L2ResidualResult = model.evaluate_date(
        merged_df=df,
        current_date_str=dates[-1],
        target_signal="clinical_resp",
        geo_id="DXB-AQ",
    )

    assert res.observed == 85.0
    assert res.unexplained_excess > 30.0
    assert res.p_value_unexplained < 0.05
    assert res.is_environment_driven is False  # Cannot blame the weather


def test_l2_short_history_fallback():
    """Fallback when history is under min_train_samples."""
    model = L2ExposureBaselineModel(min_train_samples=30)
    dates = pd.date_range("2026-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    df = pd.DataFrame({
        "obs_date": dates,
        "signal_type": "absence_heat",
        "geo_id": "SITE-JA-01",
        "value": [5.0] * 9 + [25.0],
        "denominator": 500.0,
        "pm25": [30.0] * 10,
        "wbgt_max": [31.0] * 10,
    })

    res = model.evaluate_date(df, dates[-1], "absence_heat", "SITE-JA-01")
    assert res.observed == 25.0
    assert res.total_excess > 0
    assert res.unexplained_excess == res.total_excess

