"""Tests for Health & Workplace Simulator and Ground Truth Event injection."""

from prahari.config import get_region_config
from prahari.models.canonical import SignalObservation
from prahari.simulator.events import InjectedScenarioCatalog
from prahari.simulator.generator import HealthWorkplaceSimulator


def test_injected_scenarios_generation():
    profile = get_region_config("uae")
    events = InjectedScenarioCatalog.generate_scenarios(
        start_date="2026-05-01",
        end_date="2026-08-31",
        region_profile=profile,
        seed=42,
    )

    assert len(events) >= 5
    scenario_types = {e.scenario_type for e in events}
    assert "heat_cluster" in scenario_types
    assert "respiratory_surge" in scenario_types
    assert "infectious_cluster" in scenario_types
    assert "decoy_backlog" in scenario_types
    assert "decoy_holiday" in scenario_types


def test_simulator_end_to_end():
    simulator = HealthWorkplaceSimulator(region_key="uae", seed=42)

    # Fake input weather observations for 2 days
    env_obs = [
        SignalObservation(
            signal_type="wbgt_max",
            geo_level="site",
            geo_id="SITE-JA-01",
            obs_date="2026-06-01",
            value=33.5,
        ),
        SignalObservation(
            signal_type="wbgt_max",
            geo_level="site",
            geo_id="SITE-JA-01",
            obs_date="2026-06-02",
            value=34.0,
        ),
        SignalObservation(
            signal_type="pm25",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=65.0,
        ),
        SignalObservation(
            signal_type="pm25",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-02",
            value=85.0,
        ),
    ]

    obs, incidents, truth = simulator.simulate(
        start_date="2026-06-01",
        end_date="2026-06-02",
        env_observations=env_obs,
    )

    assert len(obs) > 0
    sig_types = {o.signal_type for o in obs}
    assert "clinical_resp" in sig_types
    assert "clinical_gi" in sig_types
    assert "clinical_fever" in sig_types
    assert "absence_heat" in sig_types

    # Check incidents were generated and classified
    if incidents:
        inc = incidents[0]
        assert inc.predicted_category in ["heat", "respiratory_chemical", "injury", "other"]
        assert inc.confidence > 0.0

