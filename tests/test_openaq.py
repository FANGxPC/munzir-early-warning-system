"""Tests for OpenAQ v3 ground station ingestion client."""

import tempfile
from pathlib import Path
from prahari.ingestion.openaq import OpenAQClient, ingest_openaq_stations


def test_openaq_station_synthesis():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = OpenAQClient(cache_dir=Path(tmpdir), use_offline_fallback=True)

        results = client.fetch_station_measurements(
            station_id="OPENAQ-DXB-01",
            lat=25.2600,
            lon=55.3000,
            start_date="2026-06-01",
            end_date="2026-06-05",
        )

        assert len(results) >= 4  # allowing for station downtime
        sample = results[0]
        assert "pm25" in sample
        assert "pm10" in sample
        assert sample["pm25"] > 0.0


def test_ingest_openaq_stations():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = OpenAQClient(cache_dir=Path(tmpdir), use_offline_fallback=True)

        obs = ingest_openaq_stations(
            region_key="uae",
            start_date="2026-07-01",
            end_date="2026-07-02",
            client=client,
        )

        assert len(obs) > 0
        assert all(o.signal_type == "openaq_pm25" for o in obs)
        assert all(o.location_confidence == "exact" for o in obs)

