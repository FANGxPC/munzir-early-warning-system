"""
L3 Layer: Prospective Space-Time Permutation Cluster Scan.
Implements the Kulldorff prospective space-time permutation scan over H3 hexagonal
neighborhoods and district boundaries with Monte Carlo p-value calibration.
Reference: Kulldorff et al. (2005), Journal of the Royal Statistical Society.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple, Set
from datetime import datetime, timedelta
import math
import numpy as np
import pandas as pd
import h3

from prahari.harmonisation.spatial import get_h3_neighbors


@dataclass
class L3ClusterResult:
    """Standardized output for an identified space-time cluster."""
    cluster_id: str
    center_geo_id: str
    member_geo_ids: List[str]
    h3_cells: List[str]
    window_days: int
    start_date: str
    end_date: str
    observed_cases: float
    expected_cases: float
    relative_risk: float
    llr: float                     # Log-Likelihood Ratio
    p_value: float                 # Monte Carlo empirical p-value
    is_significant: bool           # True if p_value <= 0.05


class ProspectiveSpaceTimeScan:
    """
    Prospective Space-Time Permutation Cluster Scanner.
    Scans cylinders of varying spatial radius (H3 k-rings) and temporal durations (1-7 days).
    """

    def __init__(
        self,
        max_duration_days: int = 7,
        max_k_ring: int = 1,
        n_permutations: int = 99,
        significance_threshold: float = 0.05,
    ):
        self.max_duration_days = max_duration_days
        self.max_k_ring = max_k_ring
        self.n_permutations = n_permutations
        self.significance_threshold = significance_threshold

    def scan(
        self,
        observations_df: pd.DataFrame,
        current_date_str: str,
        study_window_days: int = 30,
        signal_type: Optional[str] = None,
    ) -> List[L3ClusterResult]:
        """
        Executes the space-time permutation scan ending on current_date_str.
        observations_df must contain:
          ['obs_date', 'geo_id', 'h3_index', 'value', 'location_confidence']
        """
        curr_dt = datetime.strptime(current_date_str, "%Y-%m-%d")
        start_study_dt = curr_dt - timedelta(days=study_window_days)
        start_study_str = start_study_dt.strftime("%Y-%m-%d")

        # Filter to study window and adequate location confidence
        df = observations_df[
            (observations_df["obs_date"] >= start_study_str)
            & (observations_df["obs_date"] <= current_date_str)
            & (observations_df["location_confidence"].isin(["exact", "district_only"]))
        ].copy()

        if signal_type:
            df = df[df["signal_type"] == signal_type]

        if df.empty or df["value"].sum() < 5.0:
            return []

        # Total count across study window
        c_total = float(df["value"].sum())

        # Marginal spatial counts C_z
        spatial_totals = df.groupby("geo_id")["value"].sum().to_dict()

        # Marginal temporal counts C_t
        temporal_totals = df.groupby("obs_date")["value"].sum().to_dict()

        # Candidate spatial zones:
        # Zone = center geo_id + neighbors (if H3 exists)
        geo_to_h3 = df[df["h3_index"].notna()].set_index("geo_id")["h3_index"].to_dict()
        unique_geos = df["geo_id"].unique().tolist()

        spatial_zones: List[Dict[str, Any]] = []
        for g_id in unique_geos:
            members = [g_id]
            h3_cells = []
            if g_id in geo_to_h3:
                center_h3 = geo_to_h3[g_id]
                h3_cells.append(center_h3)
                neighbors = get_h3_neighbors(center_h3, k_ring=self.max_k_ring)
                h3_cells.extend(neighbors)

                # Add any other geos sharing the H3 neighborhood
                for other_id, other_h3 in geo_to_h3.items():
                    if other_id != g_id and other_h3 in neighbors and other_id not in members:
                        members.append(other_id)

            spatial_zones.append({
                "center": g_id,
                "members": members,
                "h3_cells": list(set(h3_cells)),
            })

        # Temporal durations to evaluate
        durations = [d for d in [1, 2, 3, 5, 7] if d <= self.max_duration_days]

        candidate_cylinders = []

        # 1. Evaluate Observed Cylinders
        for zone in spatial_zones:
            center = zone["center"]
            members = zone["members"]
            h3_cells = zone["h3_cells"]

            # Spatial marginal for this zone
            c_z = sum(spatial_totals.get(m, 0.0) for m in members)
            if c_z <= 0:
                continue

            for dur in durations:
                win_start_dt = curr_dt - timedelta(days=dur - 1)
                win_start_str = win_start_dt.strftime("%Y-%m-%d")

                # Temporal marginal for this duration ending today
                c_d = sum(
                    temporal_totals.get((curr_dt - timedelta(days=i)).strftime("%Y-%m-%d"), 0.0)
                    for i in range(dur)
                )

                # Expected count inside cylinder: mu = (C_z * C_d) / C_total
                mu = (c_z * c_d) / max(c_total, 1.0)
                mu = max(mu, 0.01)

                # Observed count inside cylinder
                cyl_df = df[
                    (df["geo_id"].isin(members))
                    & (df["obs_date"] >= win_start_str)
                    & (df["obs_date"] <= current_date_str)
                ]
                obs_count = float(cyl_df["value"].sum())

                # Compute LLR
                llr = self._compute_llr(obs_count, mu, c_total)
                rr = (obs_count / mu) / max(0.001, (c_total - obs_count) / max(0.001, (c_total - mu)))

                if obs_count > mu and llr > 0.5:
                    candidate_cylinders.append({
                        "center": center,
                        "members": members,
                        "h3_cells": h3_cells,
                        "duration": dur,
                        "start_date": win_start_str,
                        "end_date": current_date_str,
                        "observed": obs_count,
                        "expected": mu,
                        "rr": rr,
                        "llr": llr,
                    })

        if not candidate_cylinders:
            return []

        # 2. Monte Carlo Significance Testing
        # Permute spatial IDs across dates to simulate the null hypothesis
        max_perm_llrs = []
        df_perm = df[["obs_date", "geo_id", "value"]].copy()

        rng = np.random.RandomState(42)
        unique_dates = df_perm["obs_date"].unique()

        for _ in range(self.n_permutations):
            # Shuffle geo_id labels preserving marginals
            shuffled_geos = rng.permutation(df_perm["geo_id"].values)
            df_perm["geo_shuffled"] = shuffled_geos

            # Fast evaluation of top cylinder under permutation
            best_perm_llr = 0.0
            # Sample subset of spatial zones for fast permutation calibration
            for cand in candidate_cylinders[:5]:
                members = cand["members"]
                mu = cand["expected"]
                start_str = cand["start_date"]

                perm_cyl = df_perm[
                    (df_perm["geo_shuffled"].isin(members))
                    & (df_perm["obs_date"] >= start_str)
                    & (df_perm["obs_date"] <= current_date_str)
                ]
                perm_obs = float(perm_cyl["value"].sum())
                perm_llr = self._compute_llr(perm_obs, mu, c_total)
                if perm_llr > best_perm_llr:
                    best_perm_llr = perm_llr

            max_perm_llrs.append(best_perm_llr)

        # 3. Compile Significant Clusters
        results: List[L3ClusterResult] = []
        cluster_counter = 1

        for cand in candidate_cylinders:
            llr_val = cand["llr"]
            # Empirical p-value
            exceeding = sum(1 for p_llr in max_perm_llrs if p_llr >= llr_val)
            p_val = float((exceeding + 1) / (self.n_permutations + 1))

            is_sig = p_val <= self.significance_threshold

            results.append(
                L3ClusterResult(
                    cluster_id=f"CLUSTER-{current_date_str.replace('-', '')}-{cluster_counter:02d}",
                    center_geo_id=cand["center"],
                    member_geo_ids=cand["members"],
                    h3_cells=cand["h3_cells"],
                    window_days=cand["duration"],
                    start_date=cand["start_date"],
                    end_date=cand["end_date"],
                    observed_cases=round(cand["observed"], 1),
                    expected_cases=round(cand["expected"], 1),
                    relative_risk=round(cand["rr"], 2),
                    llr=round(llr_val, 2),
                    p_value=round(p_val, 4),
                    is_significant=is_sig,
                )
            )
            cluster_counter += 1

        # Sort by LLR descending (most significant cluster first)
        results.sort(key=lambda x: x.llr, reverse=True)
        return results

    @staticmethod
    def _compute_llr(c: float, mu: float, C: float) -> float:
        """
        Log-Likelihood Ratio under the Poisson space-time permutation model:
        LLR = c * ln(c / mu) + (C - c) * ln((C - c) / (C - mu)) if c > mu else 0
        """
        if c <= mu or mu <= 0 or C <= c or C <= mu:
            return 0.0

        term1 = c * math.log(c / mu)
        term2 = (C - c) * math.log((C - c) / (C - mu))
        return float(max(0.0, term1 + term2))

