"""Unit tests for WBGT calculation formulas and aggregation."""

import pandas as pd
import pytest
from prahari.ingestion.wbgt import (
    compute_stull_wet_bulb,
    compute_globe_temperature,
    compute_wbgt_outdoor,
    process_daily_wbgt,
)


def test_stull_wet_bulb():
    # At 30°C and 50% RH, wet bulb should be around 22°C - 23°C
    tw = compute_stull_wet_bulb(30.0, 50.0)
    assert 21.5 < tw < 23.5

    # At 100% RH, wet bulb equals dry bulb
    tw_saturated = compute_stull_wet_bulb(25.0, 100.0)
    assert pytest.approx(tw_saturated, abs=0.5) == 25.0


def test_wbgt_outdoor():
    # Extreme summer day: 42°C, 45% RH, high solar radiation (800 W/m2), wind 2 m/s
    wbgt_hot = compute_wbgt_outdoor(42.0, 45.0, 2.0, 800.0)
    # This represents dangerous outdoor heat stress in Dubai
    assert wbgt_hot > 32.0

    # Mild winter day: 22°C, 40% RH, mild sun (300 W/m2), wind 3 m/s
    wbgt_mild = compute_wbgt_outdoor(22.0, 40.0, 3.0, 300.0)
    assert wbgt_mild < 24.0


def test_process_daily_wbgt():
    # Create 24 hours of synthetic summer weather
    hours = [f"2026-07-15T{h:02d}:00:00" for h in range(24)]
    temps = [28.0 + 14.0 * max(0.0, (1 - abs(h - 14) / 8.0)) for h in range(24)]
    rhs = [60.0 - 25.0 * max(0.0, (1 - abs(h - 14) / 8.0)) for h in range(24)]
    winds = [2.0] * 24
    rads = [max(0.0, 900.0 * (1 - abs(h - 13) / 6.0)) if 7 <= h <= 19 else 0.0 for h in range(24)]

    df = pd.DataFrame({
        "time": hours,
        "temperature_2m": temps,
        "relative_humidity_2m": rhs,
        "wind_speed_10m": winds,
        "shortwave_radiation": rads,
    })

    obs = process_daily_wbgt(df, geo_id="SITE-JA-01", geo_level="site", workforce_or_pop=3200.0)
    assert len(obs) == 3

    types = {o.signal_type: o.value for o in obs}
    assert "wbgt_max" in types
    assert "wbgt_hours_danger" in types
    assert types["wbgt_max"] > 30.0
    assert types["wbgt_hours_danger"] >= 1

