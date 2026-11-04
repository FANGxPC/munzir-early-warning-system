"""
Data Defects and Real-World Reporting Noise Simulator.
Injects reporting delays, missing observation days, geolocation degradation,
small-cell suppression flags, and feed dropouts to test robustness and DQ scoring.
"""

from typing import List, Dict, Any, Optional
import numpy as np
from prahari.config import SMALL_CELL_K
from prahari.models.canonical import SignalObservation


class DataDefectEngine:
    """
    Applies realistic reporting delays, missing data, and location degradation.
    """

    def __init__(
        self,
        seed: int = 42,
        missing_rate: float = 0.03,
        degrade_geo_rate: float = 0.05,
        disable_clinical_feed: bool = False,
    ):
        self.rng = np.random.RandomState(seed)
        self.missing_rate = missing_rate
        self.degrade_geo_rate = degrade_geo_rate
        self.disable_clinical_feed = disable_clinical_feed

    def apply_defects(self, observations: List[SignalObservation]) -> List[SignalObservation]:
        """
        Processes a list of raw observations, injecting reporting latency,
        dropping records according to missing rate, marking small-cell suppressions,
        and flagging low location confidence.
        """
        defected: List[SignalObservation] = []

        for obs in observations:
            # Check demo missing feed toggle
            if self.disable_clinical_feed and obs.signal_type.startswith("clinical_"):
                continue

            # Random missing reporting day
            if self.rng.rand() < self.missing_rate:
                continue

            obs_copy = obs.model_copy()

            # 1. Reporting latency distribution:
            # Weather/WBGT has near-zero latency (~1-3 hours).
            # Clinical and sickness absence reports lag by 0-5 days (mean ~28 hours).
            if obs_copy.signal_type.startswith("wbgt") or obs_copy.signal_type in ["pm25", "pm10"]:
                latency_hrs = float(np.clip(self.rng.exponential(scale=2.0), 0.5, 8.0))
            else:
                latency_hrs = float(np.clip(self.rng.lognormal(mean=3.2, sigma=0.6), 4.0, 120.0))

            obs_copy.source_latency_hrs = round(latency_hrs, 1)

            # 2. Completeness score:
            # Degrades if latency is high or reporting entities are sporadic
            comp = 1.0 - min(0.4, (latency_hrs / 120.0) * 0.4)
            if self.rng.rand() < 0.05:
                # Stochastic missing clinic in district
                comp -= float(self.rng.uniform(0.1, 0.3))
            obs_copy.completeness_score = round(float(np.clip(comp, 0.2, 1.0)), 2)

            # 3. Small-cell suppression flag:
            # If value is a count (e.g. 1 to 10), flag as suppressed
            if obs_copy.signal_type not in ["wbgt_max", "wbgt_hours_danger", "wbgt_hours_caution", "pm25", "pm10"]:
                if 1 <= obs_copy.value <= SMALL_CELL_K:
                    obs_copy.suppressed_flag = True
                else:
                    obs_copy.suppressed_flag = False

            # 4. Geolocation fallback degradation:
            if obs_copy.geo_level == "site" and self.rng.rand() < self.degrade_geo_rate:
                obs_copy.location_confidence = "district_only"

            defected.append(obs_copy)

        return defected

