"""
Tests for L3 Prospective Space-Time Cluster Scan (Kulldorff-style over H3 cells).
"""

import pytest
import numpy as np
import pandas as pd
from prahari.detection.l3_spacetime import ProspectiveSpaceTimeScan, L3ClusterResult
from prahari.harmonisation.spatial import get_h3_index


def test_l3_cluster_detection_significant():
    """
    Simulate a concentrated space-time cluster in an H3 cell over 3 days.
    Verify the prospective scanner flags the cluster with high LLR and p <= 0.05.
    """
    scanner = ProspectiveSpaceTimeScan(
        max_duration_days=5,
        max_k_ring=1,
        n_permutations=99,
        significance_threshold=0.05,
    )

    # Use realistic set of regional districts
    geos = {
        "DXB-JA": (25.01, 55.08),  # Jebel Ali
        "DXB-AQ": (25.13, 55.23),  # Al Quoz
        "DXB-DR": (25.27, 55.32),  # Deira
        "DXB-BD": (25.25, 55.30),  # Bur Dubai
        "DXB-BB": (25.18, 55.27),  # Business Bay
        "DXB-DS": (25.10, 55.17),  # Dubai South
        "DXB-RK": (25.22, 55.33),  # Ras Al Khor
        "DXB-HT": (24.80, 56.12),  # Hatta
    }

    dates = pd.date_range("2026-01-01", periods=60).strftime("%Y-%m-%d").tolist()
    records = []

    np.random.seed(42)
    for d in dates:
        for g_id, (lat, lon) in geos.items():
            h3_idx = get_h3_index(lat, lon, resolution=7)
            # Baseline is 5 cases/day
            val = np.random.poisson(5)

            # Inject sharp outbreak cluster at DXB-JA during last 3 days
            if g_id == "DXB-JA" and d in dates[-3:]:
                val = 45  # 9x elevation!

            records.append({
                "obs_date": d,
                "geo_id": g_id,
                "h3_index": h3_idx,
                "value": float(val),
                "location_confidence": "exact",
                "signal_type": "clinical_gi",
            })

    df = pd.DataFrame(records)

    clusters: list[L3ClusterResult] = scanner.scan(
        observations_df=df,
        current_date_str=dates[-1],
        study_window_days=60,
        signal_type="clinical_gi",
    )

    assert len(clusters) > 0
    top_cluster = clusters[0]
    assert "DXB-JA" in top_cluster.member_geo_ids
    assert top_cluster.relative_risk > 2.0
    assert top_cluster.llr > 5.0
    assert top_cluster.p_value <= 0.05
    assert top_cluster.is_significant is True


def test_l3_excludes_low_confidence_geolocations():
    """
    Ensure observations with low location confidence ('unknown') are filtered out
    and cannot bias spatial cluster definitions.
    """
    scanner = ProspectiveSpaceTimeScan(n_permutations=19)
    dates = ["2026-04-01", "2026-04-02"]
    df = pd.DataFrame([
        {"obs_date": "2026-04-01", "geo_id": "DXB-JA", "h3_index": "872bfb26affffff", "value": 10.0, "location_confidence": "unknown", "signal_type": "clinical_resp"},
        {"obs_date": "2026-04-02", "geo_id": "DXB-JA", "h3_index": "872bfb26affffff", "value": 50.0, "location_confidence": "unknown", "signal_type": "clinical_resp"},
    ])

    clusters = scanner.scan(df, current_date_str="2026-04-02", signal_type="clinical_resp")
    # Should not produce clusters from unknown geolocations
    assert len(clusters) == 0
