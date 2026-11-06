"""
Unit tests for CDC NSSP and WHO Open Health Syndromic Ingestor.
Verifies generation of clinical_heat and clinical_resp streams, coupling with
environmental drivers, small-cell suppression, and Bronze Parquet storage.
"""

from pathlib import Path
import pytest
import pandas as pd

from prahari.ingestion.cdc_syndromic import CDCSyndromicIngestor
from prahari.models.canonical import SignalObservation
from prahari.storage.bronze_store import BronzeStore


def test_cdc_syndromic_generation_and_storage(tmp_path):
    """
    Test generating CDC NSSP-calibrated clinical syndromic observations
    and writing them to Bronze storage.
    """
    store = BronzeStore(base_dir=tmp_path / "bronze")
    ingestor = CDCSyndromicIngestor(region_key="uae", bronze_store=store, seed=42)

    # Ingest 7 days of observations
    observations = ingestor.ingest_syndromic_streams(
        start_date="2025-07-01",
        end_date="2025-07-07",
        write_to_store=True,
    )

    assert len(observations) > 0
    signal_types = {obs.signal_type for obs in observations}
    assert "clinical_heat" in signal_types
    assert "clinical_resp" in signal_types

    # Verify Bronze Parquet readback
    df_heat = store.read_observations(
        signal_types=["clinical_heat"],
        start_date="2025-07-01",
        end_date="2025-07-07",
    )
    assert not df_heat.empty
    assert (df_heat["signal_type"] == "clinical_heat").all()
    assert (df_heat["geo_level"] == "district").all()
    assert "suppressed_flag" in df_heat.columns

    df_resp = store.read_observations(
        signal_types=["clinical_resp"],
        start_date="2025-07-01",
        end_date="2025-07-07",
    )
    assert not df_resp.empty
    assert (df_resp["signal_type"] == "clinical_resp").all()


def test_cdc_syndromic_environmental_coupling():
    """
    Verify that syndromic heat illness elevates when coupled with extreme WBGT observations.
    """
    ingestor = CDCSyndromicIngestor(region_key="uae", seed=100)

    # Moderate weather observation
    moderate_wbgt = [
        SignalObservation(
            signal_type="wbgt_max",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2025-07-15",
            value=25.0,  # Below caution
        )
    ]
    obs_mod = ingestor.ingest_syndromic_streams(
        start_date="2025-07-15",
        end_date="2025-07-15",
        env_observations=moderate_wbgt,
        write_to_store=False,
    )
    heat_mod_val = next(o.value for o in obs_mod if o.geo_id == "DXB-JA" and o.signal_type == "clinical_heat")

    # Extreme heatwave weather observation
    extreme_wbgt = [
        SignalObservation(
            signal_type="wbgt_max",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2025-07-15",
            value=36.0,  # Extreme heatwave
        )
    ]
    # Use same seed sequence to observe impact
    ingestor_extreme = CDCSyndromicIngestor(region_key="uae", seed=100)
    obs_ext = ingestor_extreme.ingest_syndromic_streams(
        start_date="2025-07-15",
        end_date="2025-07-15",
        env_observations=extreme_wbgt,
        write_to_store=False,
    )
    heat_ext_val = next(o.value for o in obs_ext if o.geo_id == "DXB-JA" and o.signal_type == "clinical_heat")

    # Heatwave should induce higher or equal heat emergency visits
    assert heat_ext_val >= heat_mod_val
