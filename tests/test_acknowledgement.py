"""
Tests for Human-in-the-Loop Acknowledgement and Operational Audit Logging (Phase 4).
"""

import pytest
from pathlib import Path
from prahari.decision.acknowledgement import (
    AcknowledgementManager,
    AlertStatus,
    AcknowledgementRecord,
    DISMISS_REASONS,
)


def test_acknowledgement_workflow_transitions(tmp_path):
    """Verify state transitions: PENDING -> ACKNOWLEDGED -> ACTED."""
    mgr = AcknowledgementManager(ack_dir=tmp_path)
    alert_id = "ALT-TEST-001"
    incident_id = "INC-20260101-JA"

    # Initial state is PENDING
    assert mgr.get_status(alert_id) == AlertStatus.PENDING

    # Step 1: Acknowledge
    rec_ack = mgr.acknowledge(
        alert_id=alert_id,
        incident_id=incident_id,
        user_role="District Health Officer",
        user_name="Dr. Tariq",
        comment="Reviewing syndromic respiratory rise",
    )
    assert rec_ack.status == AlertStatus.ACKNOWLEDGED
    assert mgr.get_status(alert_id) == AlertStatus.ACKNOWLEDGED

    # Step 2: Act
    rec_act = mgr.act(
        alert_id=alert_id,
        incident_id=incident_id,
        user_role="District Health Officer",
        action_taken="Issued public respiratory advisory and verified clinic nebulizers",
        user_name="Dr. Tariq",
    )
    assert rec_act.status == AlertStatus.ACTED
    assert mgr.get_status(alert_id) == AlertStatus.ACTED

    # Audit history contains both steps
    history = mgr.get_audit_history(alert_id)
    assert len(history) == 2
    assert history[0].status == AlertStatus.ACKNOWLEDGED
    assert history[1].status == AlertStatus.ACTED


def test_dismiss_with_mandatory_reason(tmp_path):
    """Verify that DISMISS requires a valid standardized justification reason."""
    mgr = AcknowledgementManager(ack_dir=tmp_path)
    alert_id = "ALT-DECOY-002"

    # Attempt to dismiss without valid reason must raise ValueError
    with pytest.raises(ValueError, match="Valid dismiss_reason is required"):
        mgr.dismiss(alert_id=alert_id, user_role="Data Quality Officer", dismiss_reason="")

    with pytest.raises(ValueError, match="Valid dismiss_reason is required"):
        mgr.dismiss(alert_id=alert_id, user_role="Data Quality Officer", dismiss_reason="invalid_arbitrary_reason")

    # Valid dismissal
    rec_dismiss = mgr.dismiss(
        alert_id=alert_id,
        user_role="Data Quality Officer",
        dismiss_reason="data_artefact_backlog",
        comment="Confirmed hospital EDI batch queue upload",
    )
    assert rec_dismiss.status == AlertStatus.DISMISSED
    assert mgr.get_status(alert_id) == AlertStatus.DISMISSED


def test_operational_metrics_calculation(tmp_path):
    """Verify computation of practical PPV and mean acknowledgement latency."""
    mgr = AcknowledgementManager(ack_dir=tmp_path)

    # 3 acted alerts, 1 dismissed as false positive
    mgr.act(alert_id="ALT-01", user_role="SSO", action_taken="Shade stations", latency_minutes=10.0)
    mgr.act(alert_id="ALT-02", user_role="SSO", action_taken="Hydration mandate", latency_minutes=20.0)
    mgr.act(alert_id="ALT-03", user_role="DHO", action_taken="Respiratory advisory", latency_minutes=30.0)
    mgr.dismiss(alert_id="ALT-04", user_role="DSO", dismiss_reason="false_positive_noise", latency_minutes=20.0)

    metrics = mgr.calculate_operational_metrics()
    assert metrics["acted_count"] == 3
    assert metrics["dismissed_count"] == 1
    assert metrics["mean_latency_minutes"] == 20.0  # (10+20+30+20) / 4 = 20.0
    assert metrics["practical_ppv"] == 0.75          # 3 / (3 + 1) = 0.75

