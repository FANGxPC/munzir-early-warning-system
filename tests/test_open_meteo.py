"""Tests for Open-Meteo ingestion client."""

import tempfile
from pathlib import Path
from prahari.ingestion.open_meteo import OpenMeteoClient, ingest_environmental_data


def test_open_meteo_client_offline_synthesis():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = OpenMeteoClient(cache_dir=Path(tmpdir), use_offline_fallback=True)

        # Dubai coordinates
        lat, lon = 25.1328, 55.2341
        start_date = "2026-06-01"
        end_date = "2026-06-03"

        weather_df = client.fetch_weather(lat, lon, start_date, end_date)
        assert not weather_df.empty
        # 3 days * 24 hours = 72 hours
        assert len(weather_df) >= 72
        assert "temperature_2m" in weather_df.columns
        assert "shortwave_radiation" in weather_df.columns

        aq_df = client.fetch_air_quality(lat, lon, start_date, end_date)
        assert not aq_df.empty
        assert "pm2_5" in aq_df.columns
        assert "pm10" in aq_df.columns


def test_ingest_environmental_data():
    with tempfile.TemporaryDirectory() as tmpdir:
        client = OpenMeteoClient(cache_dir=Path(tmpdir), use_offline_fallback=True)

        obs, w_df, aq_df = ingest_environmental_data(
            client=client,
            geo_id="SITE-JA-01",
            geo_level="site",
            lat=24.9920,
            lon=55.0410,
            start_date="2026-07-01",
            end_date="2026-07-02",
            denominator=3200.0,
        )

        assert len(obs) > 0
        sig_types = {o.signal_type for o in obs}
        assert "wbgt_max" in sig_types
        assert "pm25" in sig_types
        assert "pm10" in sig_types
        assert all(o.geo_id == "SITE-JA-01" for o in obs)

