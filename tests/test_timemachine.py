"""
Tests for Phase 12 Time Machine Historical Replay Engine.
Verifies zero hindsight leakage, reporting delay distribution integrity,
detector calibration, API routes, and operational timeliness metrics.
"""

import argparse
from datetime import datetime
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from prahari.api.app import app
from prahari.cli.main import cmd_timemachine
from prahari.timemachine.config import load_sources_config
from prahari.timemachine.data_loader import (
    get_data_as_of,
    generate_reported_vintages,
    LeakageError,
    AsOfSnapshot,
)
from prahari.timemachine.detector import TimeMachineDetector
from prahari.timemachine.engine import TimeMachineEngine
from prahari.timemachine.metrics import compute_replay_metrics


def test_sources_configuration_integrity():
    """Verify sources.json loads and contains required benchmark events and metadata."""
    configs = load_sources_config()
    assert "pnw_2021" in configs
    assert "dubai_2024" in configs

    pnw = configs["pnw_2021"]
    assert pnw.observed_peak_date == "2021-06-28"
    assert pnw.observed_peak_value == 1038
    assert pnw.weather_source["is_as_of_forecast"] is True
    assert "10.15585/mmwr.mm7029e1" in pnw.outcome_source.get("doi", "")


def test_get_data_as_of_strict_leakage_enforcement():
    """
    CRITICAL INVARIANT TEST:
    Proves that get_data_as_of NEVER returns any record with obs_date or reported_date
    after the simulated as-of date D.
    """
    as_of = "2021-06-26"
    snapshot = get_data_as_of(as_of, event_id="pnw_2021")

    # 1. Weather history check
    assert not snapshot.weather_history.empty
    max_weather_obs = snapshot.weather_history["obs_date"].max()
    assert max_weather_obs <= as_of, f"Weather leakage detected: {max_weather_obs} > {as_of}"

    # 2. Forward weather forecast check
    if not snapshot.weather_forecast.empty:
        min_forecast_date = snapshot.weather_forecast["obs_date"].min()
        assert min_forecast_date > as_of, f"Forecast date {min_forecast_date} must be strictly after {as_of}"

    # 3. Reported outcome check
    assert not snapshot.reported_outcomes.empty
    max_outcome_rep = snapshot.reported_outcomes["reported_date"].max()
    assert max_outcome_rep <= as_of, f"Reporting leakage detected: {max_outcome_rep} > {as_of}"

    max_outcome_obs = snapshot.reported_outcomes["obs_date"].max()
    assert max_outcome_obs <= as_of, f"Outcome occurrence leakage: {max_outcome_obs} > {as_of}"

    # 4. Method call verification
    snapshot.verify_no_leakage()


def test_leakage_error_on_injected_future_record():
    """Verifies that AsOfSnapshot raises LeakageError if future data is maliciously inserted."""
    snapshot = get_data_as_of("2021-06-25", event_id="pnw_2021")
    # Manually tamper with weather history to include tomorrow's date
    tampered_history = snapshot.weather_history.copy()
    tampered_history.loc[0, "obs_date"] = "2021-06-28"
    snapshot.weather_history = tampered_history

    with pytest.raises(LeakageError):
        snapshot.verify_no_leakage()


def test_reporting_delay_distribution_conservation():
    """
    Verifies that the empirical reporting delay distribution (70% D+1, 20% D+2, 10% D+3)
    conserves total count and maps dates properly.
    """
    raw_sample = [
        {"obs_date": "2021-06-25", "clinical_heat_ed_visits": 100, "is_heatwave_window": True},
        {"obs_date": "2021-06-26", "clinical_heat_ed_visits": 50, "is_heatwave_window": True},
    ]
    df = generate_reported_vintages(raw_sample)
    assert len(df) == 6  # 3 batches per day
    assert df["count"].sum() == 150  # Conservation of total cases

    # Check that minimum reporting delay is at least 1 day
    assert (df["reporting_delay_days"] >= 1).all()


def test_timemachine_replay_execution_and_timeliness():
    """
    Executes end-to-end historical replay on PNW 2021 Heat Dome.
    Verifies that Munzir achieves earlier lead time than static threshold.
    """
    engine = TimeMachineEngine("pnw_2021")
    results, metrics = engine.run_replay()

    assert len(results) >= 60
    assert metrics.event_id == "pnw_2021"
    assert metrics.observed_peak_date == "2021-06-28"

    # Operational Lead Time verification
    assert metrics.lead_time_vs_peak_days >= 3.0, (
        f"Expected at least 3.0 days lead time vs peak, got {metrics.lead_time_vs_peak_days}"
    )
    assert metrics.first_munzir_alert_date < metrics.first_threshold_alert_date, (
        "Munzir must alert earlier than the static 35°C temperature threshold"
    )
    assert metrics.lead_time_vs_threshold_days >= 1.0

    # Sensitivity and false alarm bounds
    assert metrics.sensitivity_pct >= 80.0
    assert metrics.ppv_pct >= 60.0
    assert metrics.false_alarm_rate_per_month <= 2.5


def test_timemachine_api_endpoints():
    """Tests FastAPI REST endpoints for Time Machine replay."""
    client = TestClient(app)

    # 1. Events catalog
    resp1 = client.get("/api/v1/timemachine/events")
    assert resp1.status_code == 200
    events = resp1.json()["events"]
    assert any(e["event_id"] == "pnw_2021" for e in events)

    # 2. Replay trace
    resp2 = client.get("/api/v1/timemachine/replay?event=pnw_2021")
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert "metrics" in data2
    assert "timeline" in data2
    assert data2["metrics"]["lead_time_vs_peak_days"] >= 3.0

    # 3. As-of snapshot
    resp3 = client.get("/api/v1/timemachine/as-of?event=pnw_2021&date=2021-06-26")
    assert resp3.status_code == 200
    data3 = resp3.json()
    assert data3["as_of_date"] == "2021-06-26"
    assert "decision" in data3
    assert "visible_reported_outcomes" in data3


def test_timemachine_cli_execution(tmp_path):
    """Tests CLI command execution for timemachine."""
    json_out = tmp_path / "test_replay.json"
    html_out = tmp_path / "test_replay.html"

    args = argparse.Namespace(
        event="pnw_2021",
        start_date="2021-06-20",
        end_date="2021-07-02",
        out_json=str(json_out),
        out_html=str(html_out),
    )
    cmd_timemachine(args)

    assert json_out.exists()
    assert html_out.exists()
    content = html_out.read_text(encoding="utf-8")
    assert "Munzir Time Machine Replay" in content
    assert "SINGLE CASE STUDY DISCLOSURE" in content

