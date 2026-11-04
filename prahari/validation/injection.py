"""
Synthetic Outbreak Injection Study Engine.
Generates 100+ parameterized ground truth events and benign decoys across
varied magnitudes, durations, and geographies to evaluate detection sensitivity,
lead times, timeliness curves (AMOC), and false-alarm suppression.
Satisfies Phase 6 Step 2.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from prahari.config import REGIONAL_PROFILES
from prahari.models.canonical import InjectedEventTruth


class SyntheticInjectionStudy:
    """
    Orchestrates programmatic outbreak injection studies with varied parameters:
    - Peak magnitude (1.5x to 5.0x baseline)
    - Growth duration (1 to 7 days to peak)
    - Total event window (5 to 14 days)
    - Diverse geographic sectors (Urban, Industrial, Rural, Outdoor worksites, Indoor facilities)
    - Realistic benign decoy artefacts
    """

    def __init__(self, region_key: str = "uae", seed: int = 42):
        self.region_key = region_key
        self.region_config = REGIONAL_PROFILES.get(region_key, REGIONAL_PROFILES["uae"])
        self.seed = seed
        self.rng = np.random.RandomState(seed)

    def generate_injection_study(
        self,
        n_events: int = 100,
        start_date: str = "2026-01-01",
        end_date: str = "2026-10-31",
    ) -> List[InjectedEventTruth]:
        """
        Generates a balanced catalog of >= n_events synthetic outbreak injections and decoys.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = max((end_dt - start_dt).days, 60)

        districts = [d["id"] for d in self.region_config.get("districts", [])]
        outdoor_sites = [s["id"] for s in self.region_config.get("sites", []) if "outdoor" in s.get("site_type", "")]
        all_sites = [s["id"] for s in self.region_config.get("sites", [])]

        if not outdoor_sites:
            outdoor_sites = all_sites[:3]

        scenario_types = [
            ("heat_cluster", 0.30),
            ("respiratory_surge", 0.30),
            ("infectious_cluster", 0.25),
            ("decoy_backlog_dump", 0.08),
            ("decoy_benign_heat", 0.07),
        ]

        catalog: List[InjectedEventTruth] = []

        for i in range(n_events):
            # Select scenario type according to distribution
            r_val = self.rng.uniform(0, 1)
            cum = 0.0
            chosen_type = "heat_cluster"
            for st, p in scenario_types:
                cum += p
                if r_val <= cum:
                    chosen_type = st
                    break

            is_decoy = chosen_type.startswith("decoy_")

            # Determine location based on scenario realism
            if chosen_type == "heat_cluster":
                target_geo = self.rng.choice(outdoor_sites)
                primary_sig = "absence_heat"
            elif chosen_type == "respiratory_surge":
                target_geo = self.rng.choice(districts)
                primary_sig = "clinical_resp"
            elif chosen_type == "infectious_cluster":
                # Mix of dense worker canteens and residential districts
                target_geo = self.rng.choice(districts + all_sites)
                primary_sig = "clinical_gi"
            elif chosen_type == "decoy_backlog_dump":
                target_geo = self.rng.choice(districts)
                primary_sig = "clinical_fever"
            else:  # decoy_benign_heat
                target_geo = self.rng.choice(outdoor_sites)
                primary_sig = "wbgt_max"

            # Temporal scheduling
            # Stagger events across evaluation window
            offset_days = int(self.rng.uniform(5, total_days - 15))
            ev_start = start_dt + timedelta(days=offset_days)
            growth_days = int(self.rng.choice([2, 3, 4, 5, 6]))
            total_duration = growth_days + int(self.rng.choice([3, 4, 5, 6, 7]))

            ev_peak = ev_start + timedelta(days=growth_days)
            ev_end = ev_start + timedelta(days=total_duration)

            # Magnitudes
            if is_decoy:
                multiplier = 1.0  # Decoys have no real clinical surge or are artificial one-day dumps
            else:
                multiplier = round(float(self.rng.uniform(1.6, 4.8)), 2)

            ev = InjectedEventTruth(
                event_id=f"INJ-{i+1:03d}-{chosen_type[:4].upper()}",
                scenario_type=chosen_type,
                target_geo_id=target_geo,
                start_date=ev_start.strftime("%Y-%m-%d"),
                peak_date=ev_peak.strftime("%Y-%m-%d"),
                end_date=ev_end.strftime("%Y-%m-%d"),
                peak_multiplier=multiplier,
                affected_signals=[primary_sig],
                is_decoy=is_decoy,
                description=f"Injected {chosen_type} at {target_geo} (Multiplier: {multiplier}x, Growth: {growth_days}d)",
            )
            catalog.append(ev)

        return catalog

    def inject_signals_into_dataframe(
        self,
        base_df: pd.DataFrame,
        injection_catalog: List[InjectedEventTruth],
    ) -> pd.DataFrame:
        """
        Applies parameterized outbreak surges and decoys onto a baseline observations dataframe.
        """
        df = base_df.copy()
        # Fast dictionary lookup for modifications
        rows = df.to_dict(orient="records")

        # Index row positions by (geo_id, obs_date, signal_type)
        idx_map: Dict[tuple, int] = {}
        for idx, r in enumerate(rows):
            k = (r["geo_id"], r["obs_date"], r["signal_type"])
            idx_map[k] = idx

        for ev in injection_catalog:
            if ev.is_decoy and "backlog" in ev.scenario_type:
                # Decoy backlog: single day surge with extreme source latency
                k = (ev.target_geo_id, ev.start_date, "clinical_fever")
                if k in idx_map:
                    row_idx = idx_map[k]
                    rows[row_idx]["value"] = round(rows[row_idx]["value"] * 3.5, 1)
                    rows[row_idx]["source_latency_hrs"] = 52.0  # High latency backlog dump
                continue

            if ev.is_decoy:
                # Benign heat decoy or step shift without illness
                continue

            # Real outbreak injection: triangular / bell-curve surge between start, peak, and end
            start_dt = datetime.strptime(ev.start_date, "%Y-%m-%d")
            peak_dt = datetime.strptime(ev.peak_date, "%Y-%m-%d")
            end_dt = datetime.strptime(ev.end_date, "%Y-%m-%d")
            growth_span = max((peak_dt - start_dt).days, 1)
            decay_span = max((end_dt - peak_dt).days, 1)

            curr = start_dt
            while curr <= end_dt:
                d_str = curr.strftime("%Y-%m-%d")
                if curr <= peak_dt:
                    frac = (curr - start_dt).days / growth_span
                else:
                    frac = 1.0 - ((curr - peak_dt).days / decay_span)
                frac = max(0.0, min(1.0, frac))

                surge_factor = 1.0 + (ev.peak_multiplier - 1.0) * frac

                for sig in ev.affected_signals:
                    k = (ev.target_geo_id, d_str, sig)
                    if k in idx_map:
                        row_idx = idx_map[k]
                        rows[row_idx]["value"] = round(rows[row_idx]["value"] * surge_factor, 1)

                curr += timedelta(days=1)

        return pd.DataFrame(rows)
