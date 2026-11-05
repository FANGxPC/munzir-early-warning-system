"""
Wet Bulb Globe Temperature (WBGT) and Outdoor Heat Stress Derivation Engine.
Calculates psychrometric wet bulb, natural wet bulb, black globe temperature,
and outdoor/indoor WBGT based on standard micrometeorological formulations
(Liljegren, Bernard, Stull).
"""

import math
from typing import Dict, List, Any, Optional
import numpy as np
import pandas as pd

from prahari.config import WBGT_CAUTION, WBGT_EXTREME_CAUTION, WBGT_DANGER
from prahari.models.canonical import SignalObservation


def compute_stull_wet_bulb(temp_c: float, rel_humidity_pct: float) -> float:
    """
    Calculate psychrometric wet-bulb temperature (°C) using Stull's formula (2011).
    Valid for temperatures between -20°C and 50°C and RH 5% to 99%.
    """
    t = float(temp_c)
    rh = float(np.clip(rel_humidity_pct, 1.0, 100.0))

    tw = (
        t * math.atan(0.151977 * math.sqrt(rh + 8.313659))
        + math.atan(t + rh)
        - math.atan(rh - 1.676331)
        + 0.00391838 * (rh ** 1.5) * math.atan(0.023101 * rh)
        - 4.686035
    )
    return float(tw)


def compute_globe_temperature(
    temp_c: float,
    wind_speed_ms: float,
    solar_radiation_wm2: float,
) -> float:
    """
    Estimate standard 150mm matte black globe temperature (Tg, °C)
    balancing radiative solar absorption and convective wind dissipation.
    """
    t = float(temp_c)
    v = max(float(wind_speed_ms), 0.1)
    s = max(float(solar_radiation_wm2), 0.0)

    # Convective heat transfer coefficient term
    h_c = 1.4 * (v ** 0.6)
    delta_tg = (0.015 * s) / (1.0 + 0.15 * h_c)
    return float(t + delta_tg)


def compute_natural_wet_bulb(
    temp_c: float,
    rel_humidity_pct: float,
    wind_speed_ms: float,
    solar_radiation_wm2: float,
) -> float:
    """
    Estimate natural wet bulb temperature (Tnw, °C) taking into account
    solar radiation on a wet wick and air ventilation.
    """
    tw = compute_stull_wet_bulb(temp_c, rel_humidity_pct)
    v = max(float(wind_speed_ms), 0.1)
    s = max(float(solar_radiation_wm2), 0.0)

    # Solar radiative warming on wet bulb wick
    delta_tnw = (0.0045 * s) / (1.0 + 0.25 * math.sqrt(v))
    return float(tw + delta_tnw)


def compute_wbgt_outdoor(
    temp_c: float,
    rel_humidity_pct: float,
    wind_speed_ms: float,
    solar_radiation_wm2: float,
) -> float:
    """
    Calculate outdoor WBGT (°C):
    WBGT = 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
    """
    tnw = compute_natural_wet_bulb(temp_c, rel_humidity_pct, wind_speed_ms, solar_radiation_wm2)
    tg = compute_globe_temperature(temp_c, wind_speed_ms, solar_radiation_wm2)
    ta = float(temp_c)

    wbgt = 0.7 * tnw + 0.2 * tg + 0.1 * ta
    return float(round(wbgt, 2))


def process_daily_wbgt(
    hourly_df: pd.DataFrame,
    geo_id: str,
    geo_level: str = "site",
    workforce_or_pop: Optional[float] = None,
) -> List[SignalObservation]:
    """
    Process hourly weather records for one day into daily aggregated WBGT signal observations.
    Required columns in hourly_df:
      ['time', 'temperature_2m', 'relative_humidity_2m', 'wind_speed_10m', 'shortwave_radiation']
    """
    if hourly_df.empty:
        return []

    # Calculate hourly outdoor WBGT
    wbgt_values = []
    for _, row in hourly_df.iterrows():
        val = compute_wbgt_outdoor(
            temp_c=row["temperature_2m"],
            rel_humidity_pct=row["relative_humidity_2m"],
            wind_speed_ms=row.get("wind_speed_10m", 1.5),
            solar_radiation_wm2=row.get("shortwave_radiation", 0.0),
        )
        wbgt_values.append(val)

    hourly_df = hourly_df.copy()
    hourly_df["wbgt"] = wbgt_values

    # Extract date string YYYY-MM-DD
    first_time = str(hourly_df["time"].iloc[0])
    obs_date = first_time[:10]

    max_wbgt = float(np.max(wbgt_values))
    mean_wbgt = float(np.mean(wbgt_values))
    hours_above_caution = int(np.sum(np.array(wbgt_values) >= WBGT_CAUTION))
    hours_above_extreme = int(np.sum(np.array(wbgt_values) >= WBGT_EXTREME_CAUTION))
    hours_above_danger = int(np.sum(np.array(wbgt_values) >= WBGT_DANGER))

    observations = [
        SignalObservation(
            signal_type="wbgt_max",
            geo_level=geo_level,
            geo_id=geo_id,
            obs_date=obs_date,
            value=round(max_wbgt, 2),
            denominator=workforce_or_pop,
            location_confidence="exact" if geo_level == "site" else "district_only",
        ),
        SignalObservation(
            signal_type="wbgt_hours_danger",
            geo_level=geo_level,
            geo_id=geo_id,
            obs_date=obs_date,
            value=float(hours_above_danger),
            denominator=workforce_or_pop,
            location_confidence="exact" if geo_level == "site" else "district_only",
        ),
        SignalObservation(
            signal_type="wbgt_hours_caution",
            geo_level=geo_level,
            geo_id=geo_id,
            obs_date=obs_date,
            value=float(hours_above_caution),
            denominator=workforce_or_pop,
            location_confidence="exact" if geo_level == "site" else "district_only",
        ),
    ]

    return observations

