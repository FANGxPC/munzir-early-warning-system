"""
Tests for L1 Aberration Detection Layer (CDC EARS C1-C3 and Farrington-Flexible).
"""

import pytest
import numpy as np
import pandas as pd
from prahari.detection.l1_aberration import EARSDetector, FarringtonDetector, L1AberrationDetector, L1Result


def test_ears_c1_baseline():
    """Verify CDC EARS C1 moving baseline and z-score calculation."""
    detector = EARSDetector()
    # Baseline mean = 10.0, std ~ 1.0
    series = [10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 10.0, 20.0]
    mean, threshold, z, p = detector.detect_c1(series)

    assert mean == 10.0
    assert threshold > 10.0
    assert z > 3.0  # 20.0 is significant surge over baseline 10.0
    assert p < 0.01


def test_ears_c2_and_c3():
    """Verify CDC EARS C2 (with 2-day guard band) and C3 (accumulated sum)."""
    detector = EARSDetector()
    # Baseline 7 days (t-11 to t-5), 2-day guard band, and 3 consecutive rising days (t-2, t-1, t)
    series = [5.0, 5.0, 6.0, 5.0, 5.0, 6.0, 5.0, 6.0, 6.0, 12.0, 15.0, 20.0]
    mean_c2, thresh_c2, z_c2, p_c2 = detector.detect_c2(series)
    assert z_c2 > 2.0
    assert thresh_c2 > mean_c2

    mean_c3, thresh_c3, z_c3, p_c3 = detector.detect_c3(series)
    assert z_c3 >= 2.0  # C3 threshold exceeded on sustained outbreak


def test_farrington_flexible_glm():
    """Verify Farrington quasi-Poisson model with harmonic seasonality and outbreak downweighting."""
    farrington = FarringtonDetector(alpha=0.05, min_history_days=60)

    # Generate 120 days of baseline seasonal counts with an injected spike on the last day
    np.random.seed(42)
    dates = pd.date_range("2025-01-01", periods=120).strftime("%Y-%m-%d").tolist()
    doy = np.arange(1, 121)
    # Seasonal baseline: base 20 + 5*sin
    seasonal_mean = 20.0 + 5.0 * np.sin(2 * np.pi * doy / 365.25)
    counts = [np.random.poisson(m) for m in seasonal_mean]
    counts[-1] = 65  # Injected severe aberration

    df = pd.DataFrame({
        "obs_date": dates,
        "value": counts,
        "signal_type": "clinical_resp",
        "geo_id": "DXB-JA",
    })

    result: L1Result = farrington.fit_and_predict(df, current_date_str=dates[-1])

    assert result.observed_count == 65.0
    assert result.expected_count < 35.0
    assert result.exceedance_score > 1.5
    assert result.z_score > 3.0
    assert result.p_value < 0.05
    assert result.algorithm == "farrington_flexible"


def test_l1_short_history_fallback():
    """Ensure graceful fallback to EARS C2 when history is too short for Farrington GLM."""
    detector = L1AberrationDetector()
    dates = pd.date_range("2026-01-01", periods=10).strftime("%Y-%m-%d").tolist()
    df = pd.DataFrame({
        "obs_date": dates,
        "value": [10.0] * 9 + [30.0],
        "signal_type": "absence_heat",
        "geo_id": "SITE-JA-01",
    })

    res = detector.process_series(df, current_date_str=dates[-1], algorithm="farrington")
    # Must fallback cleanly without raising exception
    assert res.observed_count == 30.0
    assert res.exceedance_score > 1.0
    assert res.algorithm == "ears_c2_fallback"
