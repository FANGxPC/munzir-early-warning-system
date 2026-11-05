"""Tests for BronzeStore parquet operations."""

import tempfile
from pathlib import Path
import pytest
from prahari.models.canonical import SignalObservation
from prahari.storage.bronze_store import BronzeStore


def test_bronze_store_write_and_read():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = BronzeStore(base_dir=Path(tmpdir))

        obs_list = [
            SignalObservation(
                signal_type="wbgt_max",
                geo_level="district",
                geo_id="DXB-JA",
                obs_date="2026-06-01",
                value=32.4,
                denominator=380000.0,
            ),
            SignalObservation(
                signal_type="clinical_resp",
                geo_level="district",
                geo_id="DXB-JA",
                obs_date="2026-06-01",
                value=15.0,
                denominator=380000.0,
            ),
            SignalObservation(
                signal_type="clinical_resp",
                geo_level="district",
                geo_id="DXB-JA",
                obs_date="2026-06-02",
                value=18.0,
                denominator=380000.0,
            ),
        ]

        written = store.write_observations(obs_list)
        assert written == 3

        df = store.read_observations()
        assert len(df) == 3
        assert set(df["signal_type"].unique()) == {"wbgt_max", "clinical_resp"}

        # Filter by date
        df_filtered = store.read_observations(start_date="2026-06-02", end_date="2026-06-02")
        assert len(df_filtered) == 1
        assert df_filtered.iloc[0]["obs_date"] == "2026-06-02"


def test_bronze_store_privacy_validation():
    with pytest.raises(ValueError, match="Privacy violation"):
        SignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=10.0,
            patient_name="John Doe",  # Forbidden personal identifier
        )

