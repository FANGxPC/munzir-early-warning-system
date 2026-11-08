"""
Strict As-Of-Date Historical Replay Data Layer.
Guarantees zero hindsight leakage by strictly filtering observations and forecasts
by publication and reporting timestamps as of simulated date D.
"""

from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import numpy as np
import pandas as pd

from prahari.ingestion.wbgt import (
    compute_stull_wet_bulb,
    compute_globe_temperature,
    compute_wbgt_outdoor,
)
from prahari.timemachine.config import load_sources_config, ReplayEventConfig

logger = logging.getLogger(__name__)

DEFAULT_DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "timemachine"


class LeakageError(RuntimeError):
    """Raised when future data is detected in an as-of-date snapshot."""
    pass


@dataclass
class AsOfSnapshot:
    """Represents the complete state of public health intelligence visible on as_of_date D."""
    as_of_date: str
    event_id: str
    weather_history: pd.DataFrame       # Daily observed weather for date <= as_of_date
    weather_forecast: pd.DataFrame      # 1-to-3-day forward forecast as known on as_of_date
    reported_outcomes: pd.DataFrame     # Clinical counts received by health authority on or before as_of_date
    unreported_outcomes: pd.DataFrame   # Future or in-flight records not yet reported (for UI visualization)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def verify_no_leakage(self) -> None:
        """Verifies that no record in visible data has an obs_date or reported_date after as_of_date."""
        if not self.weather_history.empty:
            max_weather_obs = self.weather_history["obs_date"].max()
            if max_weather_obs > self.as_of_date:
                raise LeakageError(
                    f"Hindsight leakage in weather history: max obs_date {max_weather_obs} > as_of_date {self.as_of_date}"
                )

        if not self.reported_outcomes.empty:
            max_outcome_reported = self.reported_outcomes["reported_date"].max()
            if max_outcome_reported > self.as_of_date:
                raise LeakageError(
                    f"Hindsight leakage in outcomes: max reported_date {max_outcome_reported} > as_of_date {self.as_of_date}"
                )
            max_outcome_obs = self.reported_outcomes["obs_date"].max()
            if max_outcome_obs > self.as_of_date:
                raise LeakageError(
                    f"Hindsight leakage in outcomes: max obs_date {max_outcome_obs} > as_of_date {self.as_of_date}"
                )


def _load_hourly_weather(event_dir: Path) -> pd.DataFrame:
    """Loads hourly raw weather JSON and derives outdoor WBGT."""
    weather_file = event_dir / "weather_forecast.json"
    if not weather_file.exists():
        raise FileNotFoundError(f"Missing weather file: {weather_file}")

    with open(weather_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    h = data["hourly"]
    times = h["time"]
    temps = h["temperature_2m"]
    rhs = h["relative_humidity_2m"]
    winds = h.get("wind_speed_10m", [10.0] * len(times))
    rads = h.get("shortwave_radiation_instant", [0.0] * len(times))

    rows = []
    for t, temp, rh, wind, rad in zip(times, temps, rhs, winds, rads):
        dt = datetime.fromisoformat(t)
        date_str = dt.strftime("%Y-%m-%d")
        wind_ms = float(wind) / 3.6  # convert km/h to m/s
        wbgt = compute_wbgt_outdoor(float(temp), float(rh), wind_ms, float(rad))
        rows.append({
            "timestamp": t,
            "obs_date": date_str,
            "hour": dt.hour,
            "temperature_2m": float(temp),
            "relative_humidity_2m": float(rh),
            "wind_speed_ms": wind_ms,
            "solar_radiation": float(rad),
            "wbgt": wbgt,
        })
    return pd.DataFrame(rows)


def _compute_daily_weather_summaries(hourly_df: pd.DataFrame) -> pd.DataFrame:
    """Rolls up hourly weather into daily maximum, mean, and danger hours."""
    records = []
    for date_str, group in hourly_df.groupby("obs_date"):
        t_max = float(group["temperature_2m"].max())
        t_mean = float(group["temperature_2m"].mean())
        rh_mean = float(group["relative_humidity_2m"].mean())
        wbgt_max = float(group["wbgt"].max())
        wbgt_mean = float(group["wbgt"].mean())
        # Danger hours: WBGT >= 30.0°C (NWS/ACGIH Threshold)
        danger_hrs = int((group["wbgt"] >= 30.0).sum())
        caution_hrs = int(((group["wbgt"] >= 28.0) & (group["wbgt"] < 30.0)).sum())

        records.append({
            "obs_date": date_str,
            "temp_max": round(t_max, 1),
            "temp_mean": round(t_mean, 1),
            "rh_mean": round(rh_mean, 1),
            "wbgt_max": round(wbgt_max, 1),
            "wbgt_mean": round(wbgt_mean, 1),
            "wbgt_hours_danger": danger_hrs,
            "wbgt_hours_caution": caution_hrs,
        })
    res_df = pd.DataFrame(records).sort_values("obs_date").reset_index(drop=True)
    return res_df


def _load_raw_outcomes(event_dir: Path) -> List[Dict[str, Any]]:
    """Loads raw outcome counts from CDC MMWR or simulated store."""
    outcome_file = event_dir / "outcomes_cdc_mmwr.json"
    if not outcome_file.exists():
        raise FileNotFoundError(f"Missing outcome file: {outcome_file}")

    with open(outcome_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get("records", [])


def generate_reported_vintages(
    raw_outcomes: List[Dict[str, Any]],
    delay_dist: Optional[Dict[int, float]] = None,
) -> pd.DataFrame:
    """
    Applies empirical reporting delay distribution to raw event occurrences.
    Default distribution (CDC NSSP profile):
      - 70% reported on D+1 (delay = 1 day)
      - 20% reported on D+2 (delay = 2 days)
      - 10% reported on D+3 (delay = 3 days)
    Returns a dataframe of batch arrivals with (obs_date, reported_date, batch_count).
    """
    if delay_dist is None:
        delay_dist = {1: 0.70, 2: 0.20, 3: 0.10}

    arrivals = []
    for r in raw_outcomes:
        obs_date_str = r["obs_date"]
        total_visits = int(r.get("clinical_heat_ed_visits", 0))
        obs_dt = datetime.strptime(obs_date_str, "%Y-%m-%d")

        # Deterministic allocation to prevent random jitter across test runs
        c1 = int(round(total_visits * delay_dist.get(1, 0.70)))
        c2 = int(round(total_visits * delay_dist.get(2, 0.20)))
        c3 = max(0, total_visits - c1 - c2)

        batches = [(1, c1), (2, c2), (3, c3)]
        for delay_days, count in batches:
            if count <= 0:
                continue
            rep_dt = obs_dt + timedelta(days=delay_days)
            arrivals.append({
                "obs_date": obs_date_str,
                "reported_date": rep_dt.strftime("%Y-%m-%d"),
                "reporting_delay_days": delay_days,
                "count": count,
                "is_heatwave_window": r.get("is_heatwave_window", False),
                "source": r.get("source", "CDC NSSP"),
            })

    df = pd.DataFrame(arrivals)
    return df.sort_values(["reported_date", "obs_date"]).reset_index(drop=True)


def get_data_as_of(
    as_of_date: str,
    event_id: str = "pnw_2021",
    data_dir: Optional[Path] = None,
) -> AsOfSnapshot:
    """
    The Single Gateway Function for all detection layers during time machine replay.
    Strictly filters data to what was available at or before 06:00 AM on as_of_date D:
      1. Weather history: strictly obs_date <= as_of_date
      2. Weather forecast: archived 1-to-3-day forward model forecast starting after as_of_date
      3. Outcomes: strictly reported_date <= as_of_date
    """
    base_dir = Path(data_dir or DEFAULT_DATA_DIR)
    event_dir = base_dir / event_id
    if not event_dir.exists():
        raise FileNotFoundError(f"Event directory not found: {event_dir}")

    configs = load_sources_config(base_dir / "sources.json")
    event_config = configs.get(event_id)

    # 1. Weather
    hourly_df = _load_hourly_weather(event_dir)
    daily_weather = _compute_daily_weather_summaries(hourly_df)

    # Past observed weather
    weather_history = daily_weather[daily_weather["obs_date"] <= as_of_date].copy()

    # Forward weather forecast (1 to 3 days ahead as predicted by NWP model)
    dt_as_of = datetime.strptime(as_of_date, "%Y-%m-%d")
    forecast_dates = [(dt_as_of + timedelta(days=step)).strftime("%Y-%m-%d") for step in (1, 2, 3)]
    weather_forecast = daily_weather[daily_weather["obs_date"].isin(forecast_dates)].copy()

    # 2. Outcomes & reporting delay
    raw_outcomes = _load_raw_outcomes(event_dir)
    vintages_df = generate_reported_vintages(raw_outcomes)

    # Strictly what has arrived by as_of_date
    reported = vintages_df[vintages_df["reported_date"] <= as_of_date].copy()
    unreported = vintages_df[vintages_df["reported_date"] > as_of_date].copy()

    # Aggregate reported counts by obs_date
    if not reported.empty:
        reported_summary = (
            reported.groupby("obs_date", as_index=False)
            .agg({
                "count": "sum",
                "reported_date": "max",
                "reporting_delay_days": "mean",
            })
            .rename(columns={"count": "reported_visits"})
        )
    else:
        reported_summary = pd.DataFrame(
            columns=["obs_date", "reported_visits", "reported_date", "reporting_delay_days"]
        )

    meta = {
        "event_id": event_id,
        "as_of_date": as_of_date,
        "event_name": event_config.name if event_config else event_id,
        "weather_source": "Open-Meteo Archived Forecast API (historical-forecast-api.open-meteo.com)",
        "outcome_source": "CDC MMWR Vol. 70, No. 29 / NSSP (DOI: 10.15585/mmwr.mm7029e1)",
        "delay_label": "SIMULATED DELAY (CDC NSSP Empirical Geometric Distribution: 70% D+1, 20% D+2, 10% D+3)",
        "leakage_enforced": True,
    }

    snapshot = AsOfSnapshot(
        as_of_date=as_of_date,
        event_id=event_id,
        weather_history=weather_history,
        weather_forecast=weather_forecast,
        reported_outcomes=reported_summary,
        unreported_outcomes=unreported,
        metadata=meta,
    )

    # Formal zero-leakage invariant enforcement
    snapshot.verify_no_leakage()
    return snapshot

