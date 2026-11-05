"""
Tests for Decision Support Playbook Engine (Phase 4).
Verifies YAML playbook schema loading, trigger matching, and proportionality enforcement.
"""

import pytest
from pathlib import Path
from prahari.detection.l5_policy import AlertSeverity
from prahari.decision.playbook_engine import PlaybookEngine, Playbook, TIER_HIERARCHY


def test_playbook_engine_loads_all_yaml_files():
    """Verify that all playbooks in playbooks/ load without schema validation errors."""
    engine = PlaybookEngine()
    playbooks = engine.list_playbooks()

    # Must contain at least 6 playbooks as required by Phase 4 specification
    assert len(playbooks) >= 6

    expected_ids = {
        "heat_worksite_warning",
        "heat_worksite_alert",
        "respiratory_surge_warning",
        "respiratory_surge_alert",
        "infectious_cluster_warning",
        "infectious_cluster_alert",
        "data_artefact_watch",
    }

    loaded_ids = {pb.id for pb in playbooks}
    for eid in expected_ids:
        assert eid in loaded_ids, f"Playbook '{eid}' missing from loaded library!"


def test_playbook_trigger_matching():
    """Verify exact trigger matching for flagship scenarios and severity tiers."""
    engine = PlaybookEngine()

    # Flagship 1: Worksite heat hazard
    pb_heat = engine.get_playbook("heat_cluster", AlertSeverity.WARNING, is_site=True)
    assert pb_heat.id == "heat_worksite_warning"
    assert "Site Safety Officer" in pb_heat.responsible.get("lead", "")
    assert len(pb_heat.actions) >= 3

    # Flagship 2: District respiratory surge
    pb_resp = engine.get_playbook("respiratory_surge", AlertSeverity.ALERT, is_site=False)
    assert pb_resp.id == "respiratory_surge_alert"
    assert "District Health Officer" in pb_resp.responsible.get("lead", "")

    # Flagship 3: Facility infectious cluster
    pb_inf = engine.get_playbook("infectious_cluster", AlertSeverity.WARNING, is_site=True)
    assert pb_inf.id == "infectious_cluster_warning"

    # Decoy: Backlog dump
    pb_decoy = engine.get_playbook("data_artefact", AlertSeverity.WATCH)
    assert pb_decoy.id == "data_artefact_watch"


def test_proportionality_ladder_enforcement():
    """
    CRITICAL DECISION SUPPORT TEST:
    The engine must NEVER recommend a stronger action than the evidence tier allows.
    Watch -> monitor only.
    Warning -> targeted preventive.
    Alert -> field response.
    """
    engine = PlaybookEngine()

    # Watch tier: can only allow monitor
    assert engine.enforce_proportionality(AlertSeverity.WATCH, "monitor") is True
    assert engine.enforce_proportionality(AlertSeverity.WATCH, "targeted_preventive") is False
    assert engine.enforce_proportionality(AlertSeverity.WATCH, "field_response") is False

    # Warning tier: can allow monitor and targeted_preventive, but NOT field_response
    assert engine.enforce_proportionality(AlertSeverity.WARNING, "monitor") is True
    assert engine.enforce_proportionality(AlertSeverity.WARNING, "targeted_preventive") is True
    assert engine.enforce_proportionality(AlertSeverity.WARNING, "field_response") is False

    # Alert tier: can allow field_response
    assert engine.enforce_proportionality(AlertSeverity.ALERT, "field_response") is True

    # If an alert is WATCH, but matched playbook has field_response actions,
    # get_proportionate_actions must downgrade to monitoring
    pb_alert = engine.get_playbook("heat_cluster", AlertSeverity.ALERT, is_site=True)
    actions = engine.get_proportionate_actions(pb_alert, AlertSeverity.WATCH)
    assert len(actions) > 0
    assert "disruptive intervention withheld" in actions[0].lower() or "monitoring" in actions[0].lower()

