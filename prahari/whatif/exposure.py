"""
Deterministic Work Schedule Exposure-Hours Computation Engine.
Computes working-hour heat exposure directly from real WBGT time series.
All schedule shifting, break extension, and shade mitigation metrics are
calculated deterministically without stochastic estimation.
"""

from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timezone
import json
import numpy as np
import pandas as pd

from prahari.config import (
    WBGT_CAUTION,
    WBGT_EXTREME_CAUTION,
    WBGT_DANGER,
    CACHE_DIR,
    REGIONAL_PROFILES,
)
from prahari.ingestion.wbgt import compute_wbgt_outdoor
from prahari.whatif.config import load_assumptions_config


class WorkSchedule:
    """
    Defines working hours and break periods for outdoor workforce shifts.
    Hours are represented in local time (0-23).
    """

    def __init__(
        self,
        name: str,
        start_hour: float = 7.0,
        end_hour: float = 16.0,
        break_start: float = 12.5,  # 12:30 PM (MOHRE standard)
        break_end: float = 14.0,    # 2:00 PM
        split_shift_start_2: Optional[float] = None,
        split_shift_end_2: Optional[float] = None,
    ):
        self.name = name
        self.start_hour = start_hour
        self.end_hour = end_hour
        self.break_start = break_start
        self.break_end = break_end
        self.split_shift_start_2 = split_shift_start_2
        self.split_shift_end_2 = split_shift_end_2

    def is_working_hour(self, hour: float) -> bool:
        """Determines if a given hour (0-23) falls within active working shift."""
        # Standard primary shift
        if self.start_hour <= hour < self.end_hour:
            # Check if within midday break
            if self.break_start <= hour < self.break_end:
                return False
            return True

        # Secondary split shift (e.g. evening shift after midday ban)
        if self.split_shift_start_2 is not None and self.split_shift_end_2 is not None:
            if self.split_shift_start_2 <= hour < self.split_shift_end_2:
                return True

        return False

    @property
    def daily_working_hours(self) -> float:
        """Computes total active working hours in a standard day."""
        hours = 0.0
        for h in range(24):
            if self.is_working_hour(float(h)):
                hours += 1.0
        return hours


class ExposureCalculator:
    """
    Deterministic exposure-hours recomputation engine.
    Takes authentic WBGT time series and re-evaluates heat exposure
    under modified operational schedules and physical shade interventions.
    """

    @classmethod
    def load_site_wbgt_series(
        cls,
        site_id: str = "SITE-JA-01",
        start_date: str = "2024-06-01",
        end_date: str = "2024-06-30",
    ) -> pd.DataFrame:
        """
        Loads authentic hourly meteorological series from Open-Meteo cache
        and computes outdoor WBGT for each hour.
        """
        # Lookup site coordinates
        site_info = None
        for s in REGIONAL_PROFILES.get("uae", {}).get("sites", []):
            if s["id"] == site_id:
                site_info = s
                break

        lat = site_info["lat"] if site_info else 24.9857
        lon = site_info["lon"] if site_info else 55.0272

        # Find matching cached weather files and sort by file size descending (to pick largest full range file)
        pattern = f"weather_{lat:.4f}_{lon:.4f}*.json"
        matches = sorted(list((CACHE_DIR / "open_meteo").glob(pattern)), key=lambda p: p.stat().st_size, reverse=True)
        if not matches:
            # Fallback to general Jebel Ali file
            matches = sorted(list((CACHE_DIR / "open_meteo").glob("weather_24.9857_55.0272*.json")), key=lambda p: p.stat().st_size, reverse=True)

        if not matches:
            raise FileNotFoundError(f"No cached weather found for site {site_id} ({lat}, {lon})")

        data = json.loads(matches[0].read_text(encoding="utf-8"))["hourly"]

        # Parse and filter dates
        records = []
        for i, t in enumerate(data["time"]):
            dt_str = t[:10]
            if start_date <= dt_str <= end_date:
                ta = float(data["temperature_2m"][i])
                rh = float(data["relative_humidity_2m"][i])
                ws = float(data["wind_speed_10m"][i])
                sr = float(data["shortwave_radiation"][i])
                wbgt = compute_wbgt_outdoor(ta, rh, ws, sr)

                dt = datetime.fromisoformat(t)
                records.append({
                    "timestamp": t,
                    "date": dt_str,
                    "hour": dt.hour,
                    "temperature_2m": ta,
                    "relative_humidity_2m": rh,
                    "wind_speed_10m": ws,
                    "shortwave_radiation": sr,
                    "wbgt": wbgt,
                })

        if not records:
            return pd.DataFrame(columns=[
                "timestamp", "date", "hour", "temperature_2m",
                "relative_humidity_2m", "wind_speed_10m", "shortwave_radiation", "wbgt"
            ])
        return pd.DataFrame(records)

    @classmethod
    def compute_schedule_exposure(
        cls,
        df_wbgt: pd.DataFrame,
        schedule: WorkSchedule,
        shade_wbgt_delta_c: float = 0.0,
        workforce_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Deterministically computes exposure-hours above standard occupational thresholds
        for a given workforce schedule and shade offset.
        """
        if df_wbgt.empty:
            return {
                "total_working_hours": 0.0,
                "exposure_hours_caution": 0.0,
                "exposure_hours_extreme": 0.0,
                "exposure_hours_danger": 0.0,
                "mean_wbgt_working": 0.0,
                "max_wbgt_working": 0.0,
                "worker_hours_caution": 0.0,
                "worker_hours_extreme": 0.0,
                "worker_hours_danger": 0.0,
                "daily_breakdown": [],
            }

        df = df_wbgt.copy()
        # Filter strictly for hours where workers are on shift
        df["is_working"] = df["hour"].apply(schedule.is_working_hour)
        work_records = df[df["is_working"]].copy()

        # Apply physical shade reduction to effective WBGT
        work_records["wbgt_effective"] = (work_records["wbgt"] - shade_wbgt_delta_c).round(2)

        # Threshold checks
        work_records["is_caution"] = work_records["wbgt_effective"] >= WBGT_CAUTION
        work_records["is_extreme"] = work_records["wbgt_effective"] >= WBGT_EXTREME_CAUTION
        work_records["is_danger"] = work_records["wbgt_effective"] >= WBGT_DANGER

        total_working_hours = float(len(work_records))
        hours_caution = float(work_records["is_caution"].sum())
        hours_extreme = float(work_records["is_extreme"].sum())
        hours_danger = float(work_records["is_danger"].sum())

        mean_wbgt = float(work_records["wbgt_effective"].mean()) if not work_records.empty else 0.0
        max_wbgt = float(work_records["wbgt_effective"].max()) if not work_records.empty else 0.0

        worker_hours_caution = hours_caution * workforce_size
        worker_hours_extreme = hours_extreme * workforce_size
        worker_hours_danger = hours_danger * workforce_size

        # Daily profile aggregation
        daily_list = []
        for d, grp in work_records.groupby("date"):
            daily_list.append({
                "date": d,
                "working_hours": len(grp),
                "hours_danger": int(grp["is_danger"].sum()),
                "hours_caution": int(grp["is_caution"].sum()),
                "mean_wbgt": round(float(grp["wbgt_effective"].mean()), 2),
                "max_wbgt": round(float(grp["wbgt_effective"].max()), 2),
            })

        return {
            "schedule_name": schedule.name,
            "workforce_size": workforce_size,
            "total_working_hours": total_working_hours,
            "exposure_hours_caution": hours_caution,
            "exposure_hours_extreme": hours_extreme,
            "exposure_hours_danger": hours_danger,
            "mean_wbgt_working": round(mean_wbgt, 2),
            "max_wbgt_working": round(max_wbgt, 2),
            "worker_hours_caution": worker_hours_caution,
            "worker_hours_extreme": worker_hours_extreme,
            "worker_hours_danger": worker_hours_danger,
            "shade_reduction_applied_c": shade_wbgt_delta_c,
            "daily_breakdown": daily_list,
        }

    @classmethod
    def compare_interventions_deterministic(
        cls,
        df_wbgt: pd.DataFrame,
        baseline_schedule: WorkSchedule,
        scenario_schedule: WorkSchedule,
        shade_delta_c: float = 0.0,
        workforce_size: int = 1000,
    ) -> Dict[str, Any]:
        """
        Produces exact, deterministic comparison between baseline schedule
        and an intervention scenario.
        """
        baseline = cls.compute_schedule_exposure(
            df_wbgt,
            baseline_schedule,
            shade_wbgt_delta_c=0.0,
            workforce_size=workforce_size,
        )
        scenario = cls.compute_schedule_exposure(
            df_wbgt,
            scenario_schedule,
            shade_wbgt_delta_c=shade_delta_c,
            workforce_size=workforce_size,
        )

        danger_hours_averted = baseline["exposure_hours_danger"] - scenario["exposure_hours_danger"]
        danger_worker_hours_averted = baseline["worker_hours_danger"] - scenario["worker_hours_danger"]

        danger_reduction_pct = 0.0
        if baseline["exposure_hours_danger"] > 0:
            danger_reduction_pct = round(
                (danger_hours_averted / baseline["exposure_hours_danger"]) * 100.0, 2
            )

        caution_hours_averted = baseline["exposure_hours_caution"] - scenario["exposure_hours_caution"]
        caution_reduction_pct = 0.0
        if baseline["exposure_hours_caution"] > 0:
            caution_reduction_pct = round(
                (caution_hours_averted / baseline["exposure_hours_caution"]) * 100.0, 2
            )

        return {
            "baseline": baseline,
            "scenario": scenario,
            "exposure_reduction": {
                "danger_hours_averted": round(danger_hours_averted, 1),
                "danger_hours_reduction_pct": danger_reduction_pct,
                "danger_worker_hours_averted": danger_worker_hours_averted,
                "caution_hours_averted": round(caution_hours_averted, 1),
                "caution_hours_reduction_pct": caution_reduction_pct,
                "mean_wbgt_drop_c": round(baseline["mean_wbgt_working"] - scenario["mean_wbgt_working"], 2),
                "max_wbgt_drop_c": round(baseline["max_wbgt_working"] - scenario["max_wbgt_working"], 2),
            }
        }
