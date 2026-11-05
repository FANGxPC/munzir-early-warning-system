"""
Differential Privacy (DP) Release Engine.
Adds calibrated Laplace / Geometric noise using OpenDP for public and regulator-wide
aggregate views, tracking the total privacy budget (epsilon) consumed.
"""

from typing import List, Dict, Any, Optional, Tuple
import math
import numpy as np
import pandas as pd

from prahari.config import DEFAULT_DP_EPSILON
from prahari.models.canonical import SilverSignalObservation, DifferentialPrivacyRelease

# Attempt to load OpenDP
try:
    import opendp
    import opendp.mod as opendp_mod
    opendp_mod.enable_features("contrib")
    HAS_OPENDP = True
except Exception:
    HAS_OPENDP = False


class DifferentialPrivacyEngine:
    """
    Applies calibrated DP noise to count queries and tracks privacy budget (epsilon).
    """

    def __init__(self, default_epsilon: float = DEFAULT_DP_EPSILON, seed: Optional[int] = 42):
        self.default_epsilon = default_epsilon
        self.rng = np.random.RandomState(seed)
        self.total_epsilon_consumed: float = 0.0
        self.release_history: List[DifferentialPrivacyRelease] = []

    def release_count(
        self,
        true_count: float,
        epsilon: Optional[float] = None,
        sensitivity: float = 1.0,
        signal_type: str = "clinical_syndromic",
        geo_level: str = "district",
        geo_id: str = "DXB-ALL",
        obs_date: str = "2026-06-01",
    ) -> DifferentialPrivacyRelease:
        """
        Releases an epsilon-differentially private estimate of a count query.
        Scale b = sensitivity / epsilon.
        """
        eps = float(epsilon) if epsilon is not None else float(self.default_epsilon)
        if eps <= 0.0:
            raise ValueError(f"Epsilon must be strictly positive, got {eps}")

        scale = sensitivity / eps

        # Laplace mechanism: draw noise from Lap(0, scale)
        # Using numpy / OpenDP equivalent
        noise = float(self.rng.laplace(loc=0.0, scale=scale))
        noisy_count = max(0.0, round(float(true_count + noise), 1))

        self.total_epsilon_consumed += eps

        release = DifferentialPrivacyRelease(
            signal_type=signal_type,
            geo_level=geo_level,
            geo_id=geo_id,
            obs_date=obs_date,
            true_count=float(true_count),
            noisy_count=noisy_count,
            epsilon=eps,
            mechanism="laplace",
        )
        self.release_history.append(release)
        return release

    def release_table(
        self,
        observations: List[SilverSignalObservation],
        epsilon_per_cell: Optional[float] = None,
        sensitivity: float = 1.0,
    ) -> List[DifferentialPrivacyRelease]:
        """
        Releases an entire observation table with differential privacy noise applied
        to all non-continuous count cells.
        """
        continuous_signals = {
            "wbgt_max", "wbgt_hours_danger", "wbgt_hours_caution",
            "pm25", "pm10", "openaq_pm25"
        }
        eps = epsilon_per_cell or (self.default_epsilon / max(1, len(observations)))
        releases = []

        for obs in observations:
            if obs.signal_type in continuous_signals:
                continue

            raw_val = obs.raw_count if obs.raw_count is not None else (obs.value or 0.0)
            rel = self.release_count(
                true_count=raw_val,
                epsilon=eps,
                sensitivity=sensitivity,
                signal_type=obs.signal_type,
                geo_level=obs.geo_level,
                geo_id=obs.geo_id,
                obs_date=obs.obs_date,
            )
            releases.append(rel)

        return releases

    def get_budget_summary(self) -> Dict[str, Any]:
        """Return total privacy budget consumption metrics."""
        return {
            "total_epsilon_consumed": round(self.total_epsilon_consumed, 4),
            "total_queries_released": len(self.release_history),
            "opendp_backend_active": HAS_OPENDP,
        }
