"""
Tests for Fenced Epidemiological Narrative Generator (Phase 4).
Verifies deterministic synthesis, number verification gate, and hallucination fallback.
"""

import pytest
from prahari.detection.l5_policy import PrahariAlert, AlertSeverity
from prahari.decision.playbook_engine import Playbook, PlaybookTrigger
from prahari.decision.narrative import NarrativeGenerator, extract_numbers_from_obj


def test_deterministic_template_generation():
    """Verify clean deterministic narrative generation containing exact alert facts."""
    alert = PrahariAlert(
        alert_id="ALT-HEAT-101",
        incident_id="INC-20250820-JA",
        alert_type="heat_cluster",
        severity=AlertSeverity.WARNING,
        probability=0.96,
        ci_low=0.86,
        ci_high=1.00,
        geo_ids=["SITE-JA-01"],
        obs_date="2025-08-20",
        signal_contributions={"clinical": 1.29, "workplace": 0.85, "environmental": 2.21},
        dq_status="healthy",
        owner_role="Site Safety Officer",
    )

    playbook = Playbook(
        id="heat_worksite_warning",
        name="Worksite Heat-Health Warning",
        trigger=PlaybookTrigger(type="heat_cluster", severity="warning"),
        actions=["Mandatory hydration breaks", "Activate shaded rest stations"],
        responsible={"lead": "Site Safety Officer"},
        assumptions=["WBGT derived from physical weather modeling"],
    )

    evidence_summary = {
        "environmental_context": {"wbgt_max": 41.3, "wbgt_forecast_3d_max": 42.1},
        "dq_completeness_pct": 98.5,
    }

    narrative = NarrativeGenerator.generate_deterministic_template(alert, playbook, evidence_summary)

    assert "Munzir" in narrative and "Situational Briefing" in narrative
    assert "SITE-JA-01" in narrative
    assert "2025-08-20" in narrative
    assert "96.0%" in narrative
    assert "Site Safety Officer" in narrative
    assert "Mandatory hydration breaks" in narrative
    assert "41.3°C" in narrative


def test_fenced_llm_verification_accepts_clean_text():
    """Verify that a candidate narrative containing only verified numbers is accepted."""
    alert = PrahariAlert(
        probability=0.95,
        ci_low=0.85,
        ci_high=1.0,
        geo_ids=["DXB-JA"],
        obs_date="2024-11-20",
    )
    playbook = Playbook(
        id="resp_warning",
        name="Respiratory Warning",
        trigger=PlaybookTrigger(type="respiratory_surge", severity="warning"),
        actions=["Distribute masks"],
    )
    evidence_summary = {"environmental_context": {"pm25": 140.0}}

    # Safe text: all numbers (95%, 140, 2024-11-20) exist in facts
    safe_candidate = "On 2024-11-20 in DXB-JA, PM2.5 reached 140.0 with a 95% outbreak probability."

    result, was_accepted = NarrativeGenerator.generate_fenced_narrative(
        alert=alert,
        playbook=playbook,
        evidence_summary=evidence_summary,
        candidate_llm_text=safe_candidate,
    )

    assert was_accepted is True
    assert result == safe_candidate


def test_fenced_llm_verification_rejects_hallucinated_numbers_and_falls_back():
    """
    CRITICAL SAFETY GATE TEST:
    If candidate narrative invents numbers not present in the input JSON,
    it MUST be rejected and fall back safely to the deterministic template.
    """
    alert = PrahariAlert(
        probability=0.90,
        ci_low=0.80,
        ci_high=1.00,
        geo_ids=["SITE-JA-01"],
        obs_date="2025-08-20",
    )
    playbook = Playbook(
        id="heat_warning",
        name="Heat Warning",
        trigger=PlaybookTrigger(type="heat_cluster", severity="warning"),
        actions=["Hydration breaks"],
    )
    evidence_summary = {"environmental_context": {"wbgt_max": 40.0}}

    # Hallucinated numbers: '47.5°C' and '12 hospitalizations' were NEVER in facts!
    hallucinated_candidate = "Severe heat reached 47.5°C causing 12 hospitalizations at SITE-JA-01."

    result, was_accepted = NarrativeGenerator.generate_fenced_narrative(
        alert=alert,
        playbook=playbook,
        evidence_summary=evidence_summary,
        candidate_llm_text=hallucinated_candidate,
    )

    # Must reject LLM text and fall back to deterministic template
    assert was_accepted is False
    assert "47.5" not in result
    assert "12 hospitalizations" not in result
    assert "Munzir" in result and "Situational Briefing" in result

