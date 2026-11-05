"""
Small-Cell and Complementary Suppression Engine.
Enforces CMS-standard small cell suppression (1 <= count <= 10) and applies
complementary (secondary) suppression to prevent algebraic recovery from marginal totals.
"""

from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import pandas as pd

from prahari.config import SMALL_CELL_K
from prahari.models.canonical import SilverSignalObservation


def apply_small_cell_suppression(
    observations: List[SilverSignalObservation],
    k: int = SMALL_CELL_K,
) -> List[SilverSignalObservation]:
    """
    Primary suppression: Flags any cell with count 1 <= count <= k.
    Physical continuous measurements (e.g. WBGT temperature, PM2.5 concentrations)
    are not count-based personal attributes and are exempt.
    """
    continuous_signals = {
        "wbgt_max", "wbgt_hours_danger", "wbgt_hours_caution",
        "pm25", "pm10", "openaq_pm25"
    }

    result = []
    for obs in observations:
        obs_copy = obs.model_copy()

        if obs_copy.signal_type in continuous_signals:
            obs_copy.suppressed_flag = False
            obs_copy.suppression_type = "none"
        else:
            # Check if count is within 1 to k
            raw_val = obs_copy.raw_count if obs_copy.raw_count is not None else obs_copy.value
            if raw_val is not None and 1.0 <= raw_val <= float(k):
                obs_copy.suppressed_flag = True
                obs_copy.suppression_type = "primary"
                obs_copy.value = None  # Redact for external export
                obs_copy.rate_per_1000 = None
            else:
                obs_copy.suppressed_flag = False
                obs_copy.suppression_type = "none"

        result.append(obs_copy)

    return result


def apply_complementary_suppression(
    observations: List[SilverSignalObservation],
    group_keys: Optional[List[str]] = None,
    k: int = SMALL_CELL_K,
) -> List[SilverSignalObservation]:
    """
    Applies complementary (secondary) suppression across aggregation groups.
    If in any group (e.g. [obs_date, signal_type, geo_level]) exactly ONE cell
    is primarily suppressed, an attacker could subtract unsuppressed cells from
    the group total to recover the secret cell value.
    This function identifies such singletons and suppresses a second cell
    (the smallest available unsuppressed cell) to maintain 2+ degrees of freedom.
    """
    if not observations:
        return []

    # First apply primary suppression
    staged = apply_small_cell_suppression(observations, k=k)

    keys = group_keys or ["obs_date", "signal_type", "geo_level"]

    # Convert to list of dicts for group indexing
    records = [obs.model_dump() for obs in staged]
    df = pd.DataFrame(records)

    continuous_signals = {
        "wbgt_max", "wbgt_hours_danger", "wbgt_hours_caution",
        "pm25", "pm10", "openaq_pm25"
    }

    # Group by partition keys
    grouped = df.groupby(keys, group_keys=False)
    complementary_indices = set()

    for _, group in grouped:
        sig_type = group["signal_type"].iloc[0]
        if sig_type in continuous_signals:
            continue

        # Count how many cells are suppressed in this group
        suppressed_count = (group["suppressed_flag"] == True).sum()
        total_cells = len(group)

        # If exactly 1 cell is suppressed in a group with 2 or more cells:
        # We MUST apply complementary suppression to at least 1 other cell!
        if suppressed_count == 1 and total_cells >= 2:
            # Find eligible unsuppressed cells with positive values
            unsuppressed = group[group["suppressed_flag"] == False]
            if not unsuppressed.empty:
                # Pick the cell with the lowest raw_count (or value) to minimize information loss
                valid_candidates = unsuppressed[unsuppressed["raw_count"].notna() & (unsuppressed["raw_count"] > 0)]
                if not valid_candidates.empty:
                    chosen_idx = valid_candidates["raw_count"].idxmin()
                    complementary_indices.add(chosen_idx)
                else:
                    # Fallback to any unsuppressed cell
                    chosen_idx = unsuppressed.index[0]
                    complementary_indices.add(chosen_idx)

    # Apply complementary flags
    final_obs: List[SilverSignalObservation] = []
    for idx, obs in enumerate(staged):
        if idx in complementary_indices:
            obs_comp = obs.model_copy()
            obs_comp.suppressed_flag = True
            obs_comp.suppression_type = "complementary"
            obs_comp.value = None
            obs_comp.rate_per_1000 = None
            final_obs.append(obs_comp)
        else:
            final_obs.append(obs)

    return final_obs


class SuppressionEngine:
    """
    High-level interface for small-cell and complementary suppression.
    """

    def __init__(self, k: int = SMALL_CELL_K):
        self.k = k

    def process(
        self,
        observations: List[SilverSignalObservation],
        group_keys: Optional[List[str]] = None,
    ) -> List[SilverSignalObservation]:
        """
        Executes primary and complementary suppression on a set of observations.
        """
        return apply_complementary_suppression(observations, group_keys=group_keys, k=self.k)

    def verify_algebraic_privacy(
        self,
        observations: List[SilverSignalObservation],
        group_keys: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """
        Security verification audit:
        Verifies that in every group with published totals, no suppressed cell
        can be uniquely calculated via subtraction.
        Returns (is_secure, list_of_vulnerabilities).
        """
        keys = group_keys or ["obs_date", "signal_type", "geo_level"]
        df = pd.DataFrame([obs.model_dump() for obs in observations])
        continuous_signals = {
            "wbgt_max", "wbgt_hours_danger", "wbgt_hours_caution",
            "pm25", "pm10", "openaq_pm25"
        }

        vulnerabilities = []
        grouped = df.groupby(keys)

        for name, group in grouped:
            sig = group["signal_type"].iloc[0]
            if sig in continuous_signals:
                continue

            supp_count = (group["suppressed_flag"] == True).sum()
            total_cells = len(group)

            # A vulnerability exists if exactly 1 cell is suppressed out of >= 2 cells
            if supp_count == 1 and total_cells >= 2:
                vulnerabilities.append(
                    f"Vulnerability in partition {name}: Exactly 1 suppressed cell among {total_cells} total cells! Reconstructable by subtraction."
                )

        is_secure = (len(vulnerabilities) == 0)
        return is_secure, vulnerabilities

