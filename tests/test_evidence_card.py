"""
Tests for Evidence Card Generation (Phase 4 Exit Criteria).
Verifies that each flagship scenario produces a complete Evidence Card in < 2.0 seconds.
"""

import pytest
import time
from prahari.detection.l5_policy import PrahariAlert, AlertSeverity
from prahari.decision.evidence_card import EvidenceCardGenerator, EvidenceCard


def test_evidence_card_generation_latency_exit_criteria():
    """
    PHASE 4 EXIT CRITERION:
    Each flagship scenario produces an evidence card with action, owner,
    evidence and assumptions in under 2 seconds via the API.
    """
    generator = EvidenceCardGenerator()

    # Flagship 1: Worksite heat hazard
    alert_heat = PrahariAlert(
        alert_type="heat_cluster",
        severity=AlertSeverity.WARNING,
        probability=0.96,
        ci_low=0.86,
        ci_high=1.00,
        geo_ids=["SITE-JA-01"],
        obs_date="2025-08-20",
        signal_contributions={"clinical": 1.29, "workplace": 0.85, "environmental": 2.21},
    )

    t0 = time.perf_counter()
    card_heat: EvidenceCard = generator.generate(alert_heat)
    duration_heat_sec = time.perf_counter() - t0

    assert duration_heat_sec < 2.0, f"Heat card generation took {duration_heat_sec:.3f}s (exceeds 2.0s limit)"
    assert card_heat.lead_role == "Site Safety Officer"
    assert len(card_heat.recommended_actions) >= 3
    assert len(card_heat.assumptions) >= 2
    assert len(card_heat.what_rose) >= 1
    assert card_heat.primary_driver_group in ["environmental", "clinical", "workplace"]

    # Flagship 2: District respiratory surge
    alert_resp = PrahariAlert(
        alert_type="respiratory_surge",
        severity=AlertSeverity.WARNING,
        probability=0.93,
        ci_low=0.83,
        ci_high=1.00,
        geo_ids=["DXB-JA"],
        obs_date="2024-11-20",
        signal_contributions={"clinical": 1.48, "environmental": 3.42},
    )

    t0 = time.perf_counter()
    card_resp: EvidenceCard = generator.generate(alert_resp)
    duration_resp_sec = time.perf_counter() - t0

    assert duration_resp_sec < 2.0
    assert card_resp.lead_role == "District Health Officer"
    assert len(card_resp.recommended_actions) >= 3
    assert len(card_resp.citations) >= 1

    # Flagship 3: Facility infectious cluster
    alert_inf = PrahariAlert(
        alert_type="infectious_cluster",
        severity=AlertSeverity.ALERT,
        probability=0.97,
        ci_low=0.87,
        ci_high=1.00,
        geo_ids=["SITE-JA-02"],
        obs_date="2026-03-27",
        signal_contributions={"clinical": 0.94, "workplace": 0.20},
    )

    t0 = time.perf_counter()
    card_inf: EvidenceCard = generator.generate(alert_inf)
    duration_inf_sec = time.perf_counter() - t0

    assert duration_inf_sec < 2.0
    assert "District Surveillance Officer" in card_inf.lead_role or "Site Safety Officer" in card_inf.lead_role
    assert len(card_inf.recommended_actions) >= 3
    assert len(card_inf.assumptions) >= 1


def test_evidence_card_serializability():
    """Verify that EvidenceCard converts to a clean dictionary suitable for REST API responses."""
    generator = EvidenceCardGenerator()
    alert = PrahariAlert(
        alert_type="heat_cluster",
        severity=AlertSeverity.WARNING,
        probability=0.88,
        ci_low=0.78,
        ci_high=0.98,
        geo_ids=["SITE-AQ-01"],
        obs_date="2025-08-20",
    )

    card = generator.generate(alert)
    data = card.to_dict()

    assert isinstance(data, dict)
    assert data["alert_id"] == alert.alert_id
    assert data["severity"] == "warning"
    assert isinstance(data["raci_matrix"], dict)
    assert "responsible" in data["raci_matrix"]
    assert "accountable" in data["raci_matrix"]
    assert isinstance(data["recommended_actions"], list)
    assert isinstance(data["narrative_summary"], str)
    assert data["generation_time_ms"] < 2000.0

