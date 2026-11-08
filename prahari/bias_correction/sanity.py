"""
Sensor Telemetry Sanity and Data Quality Screening Engine.
Enforces physical thermodynamic boundaries, detects stuck sensor faults,
and filters known capacitive polymer hygrometer condensation saturation events.
"""

from typing import Dict, List, Any, Tuple
import pandas as pd
import numpy as np

from prahari.bias_correction.config import (
    SANITY_BOUNDS,
    DHT22_SATURATION_RH,
    DHT22_SATURATION_MAX_HOURS,
    GLOBE_MIN_OFFSET_C,
    GLOBE_MAX_OFFSET_C,
    STUCK_SENSOR_MAX_REPEATS,
)


class SensorSanityFilter:
    """
    Applies multi-stage physical and statistical quality gates to raw
    Sentinel ESP32 on-site telemetry before calibration and bias correction.
    """

    @staticmethod
    def filter_telemetry(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, Any]]:
        """
        Filters raw hourly telemetry DataFrame.
        Expected columns: ['timestamp', 'node_id', 'air_temp_c', 'rh_pct', 'globe_temp_c', 'wbgt_c']

        Returns:
            Tuple of (cleaned_df, filter_audit_report)
        """
        if df.empty:
            return df.copy(), {
                "total_records": 0,
                "valid_records": 0,
                "filtered_records": 0,
                "filtered_pct": 0.0,
                "breakdown": {
                    "range_violations": 0,
                    "thermal_implausibility": 0,
                    "stuck_sensor": 0,
                    "dht22_condensation_saturation": 0,
                },
            }

        cleaned = df.copy()
        cleaned = cleaned.sort_values(by=["node_id", "timestamp"]).reset_index(drop=True)

        n_total = len(cleaned)
        mask_valid = pd.Series(True, index=cleaned.index)

        range_dropped = 0
        thermal_dropped = 0
        stuck_dropped = 0
        saturation_dropped = 0

        # Stage 1: Absolute Physical Range Checks
        for col, (low, high) in SANITY_BOUNDS.items():
            if col in cleaned.columns:
                col_invalid = (cleaned[col] < low) | (cleaned[col] > high) | cleaned[col].isna()
                range_dropped += int(col_invalid.sum())
                mask_valid = mask_valid & (~col_invalid)

        # Stage 2: Thermodynamic Plausibility Checks (Tg vs Ta)
        if "globe_temp_c" in cleaned.columns and "air_temp_c" in cleaned.columns:
            delta_t = cleaned["globe_temp_c"] - cleaned["air_temp_c"]
            thermal_invalid = (delta_t < GLOBE_MIN_OFFSET_C) | (delta_t > GLOBE_MAX_OFFSET_C)
            # Only count rows that were not already dropped by range checks
            new_thermal = thermal_invalid & mask_valid
            thermal_dropped += int(new_thermal.sum())
            mask_valid = mask_valid & (~thermal_invalid)

        # Stage 3: Stuck Sensor Detection (Repeated identical values)
        for node_id, group in cleaned.groupby("node_id"):
            for col in ["air_temp_c", "rh_pct", "globe_temp_c"]:
                if col not in group.columns:
                    continue
                vals = group[col].values
                indices = group.index.values
                run_len = 1
                for i in range(1, len(vals)):
                    if abs(vals[i] - vals[i - 1]) < 1e-4:
                        run_len += 1
                        if run_len >= STUCK_SENSOR_MAX_REPEATS:
                            idx = indices[i]
                            if mask_valid.loc[idx]:
                                stuck_dropped += 1
                                mask_valid.loc[idx] = False
                    else:
                        run_len = 1

        # Stage 4: DHT22 Condensation Saturation Filter
        # Capacitive hygrometers saturate at 99%+ RH when dew forms and stay pegged
        if "rh_pct" in cleaned.columns:
            for node_id, group in cleaned.groupby("node_id"):
                rh_vals = group["rh_pct"].values
                indices = group.index.values
                sat_hours = 0
                for i in range(len(rh_vals)):
                    if rh_vals[i] >= DHT22_SATURATION_RH:
                        sat_hours += 1
                        if sat_hours > DHT22_SATURATION_MAX_HOURS:
                            idx = indices[i]
                            if mask_valid.loc[idx]:
                                saturation_dropped += 1
                                mask_valid.loc[idx] = False
                    else:
                        sat_hours = 0

        valid_df = cleaned[mask_valid].copy().reset_index(drop=True)
        n_valid = len(valid_df)
        n_filtered = n_total - n_valid

        audit = {
            "total_records": n_total,
            "valid_records": n_valid,
            "filtered_records": n_filtered,
            "filtered_pct": round(float(n_filtered / n_total * 100.0) if n_total > 0 else 0.0, 2),
            "breakdown": {
                "range_violations": range_dropped,
                "thermal_implausibility": thermal_dropped,
                "stuck_sensor": stuck_dropped,
                "dht22_condensation_saturation": saturation_dropped,
            },
        }

        return valid_df, audit
