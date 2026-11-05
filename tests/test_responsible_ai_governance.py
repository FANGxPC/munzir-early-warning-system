"""
Unit & Integration Tests for PRAHARI Responsible AI, Safety & Governance (Phase 8)
Verifies:
  1. Complete documentation pack integrity (Model card, datasheets, TRIPOD+AI, DPIA, limitations).
  2. Runtime safety controls: alert caps, corroboration rules, DQ gating.
  3. Deterministic fail-safe rollback to CDC EARS C2 mode if ML components fail.
  4. Fenced zero-hallucination verification of generative text.
  5. Technical misuse prevention: minimum cohort N >= 50, rate-only views, sub-site gang lockouts.
  6. Automated Governance Scorecard achieving 100% compliance.
"""

from pathlib import Path
import pytest

from prahari.governance.safety_monitor import GovernanceSafetyMonitor, GovernanceScorecard


@pytest.fixture
def monitor():
    return GovernanceSafetyMonitor()


def test_model_card_and_datasheets_documentation_integrity():
    """Verify that Model Card and all 5 feed datasheets exist and contain required Gebru/Mitchell sections."""
    docs_dir = Path(__file__).resolve().parent.parent / "docs"
    model_card = docs_dir / "model_card.md"
    assert model_card.exists(), "Missing docs/model_card.md"

    text_card = model_card.read_text(encoding="utf-8")
    assert "Intended Use" in text_card
    assert "Out-of-Scope" in text_card or "Prohibited Uses" in text_card
    assert "Brier Score" in text_card
    assert "Subgroup Fairness" in text_card or "Demographic Equity" in text_card
    assert "TreeSHAP" in text_card

    datasheet_dir = docs_dir / "datasheets"
    assert datasheet_dir.exists(), "Missing docs/datasheets directory"

    required_datasheets = [
        "open_meteo.md",
        "openaq.md",
        "clinical_syndromic.md",
        "occupational_workplace.md",
        "pharmacy_lab.md",
    ]

    for ds in required_datasheets:
        path = datasheet_dir / ds
        assert path.exists(), f"Missing datasheet: {ds}"
        text_ds = path.read_text(encoding="utf-8")
        assert "Motivation" in text_ds
        assert "Composition" in text_ds
        assert "Known Biases" in text_ds


def test_tripod_decide_ai_compliance():
    """Verify TRIPOD+AI 27-item prediction model reporting and DECIDE-AI alignment."""
    doc_path = Path(__file__).resolve().parent.parent / "docs" / "tripod_decide_ai.md"
    assert doc_path.exists(), "Missing docs/tripod_decide_ai.md"

    content = doc_path.read_text(encoding="utf-8")
    assert "TRIPOD+AI" in content
    assert "DECIDE-AI" in content
    assert "Stage 2" in content
    assert "Isotonic regression" in content


def test_safety_controls_documentation_integrity():
    """Verify docs/safety_controls.md documents all 7 operational safety barriers."""
    doc_path = Path(__file__).resolve().parent.parent / "docs" / "safety_controls.md"
    assert doc_path.exists(), "Missing docs/safety_controls.md"

    content = doc_path.read_text(encoding="utf-8")
    assert "Data Quality" in content
    assert "Corroboration Rule" in content
    assert "Alert Caps" in content
    assert "CDC EARS-Only Mode" in content
    assert "Zero-Hallucination" in content
    assert "Human-in-the-Loop" in content


def test_dpia_and_security_architecture_documentation():
    """Verify docs/dpia.md and docs/security_architecture.md cover Azure Key Vault, Managed Identity, and PDPL."""
    dpia_path = Path(__file__).resolve().parent.parent / "docs" / "dpia.md"
    sec_path = Path(__file__).resolve().parent.parent / "docs" / "security_architecture.md"

    assert dpia_path.exists()
    assert sec_path.exists()

    dpia_text = dpia_path.read_text(encoding="utf-8")
    assert "UAE Federal Decree-Law No. 45 of 2021" in dpia_text
    assert "Small-Cell Suppression" in dpia_text
    assert "Differential Privacy" in dpia_text

    sec_text = sec_path.read_text(encoding="utf-8")
    assert "Azure Key Vault" in sec_text
    assert "Managed Identity" in sec_text
    assert "TLS 1.3" in sec_text


def test_limitations_plain_statement():
    """Verify plain language disclosure of synthetic outcomes, modelled WBGT, and geolocation fallback."""
    doc_path = Path(__file__).resolve().parent.parent / "docs" / "limitations.md"
    assert doc_path.exists(), "Missing docs/limitations.md"

    content = doc_path.read_text(encoding="utf-8")
    assert "Synthetic Outcome" in content
    assert "Modelled WBGT Physics" in content
    assert "Geolocation Fallback" in content
    assert "Reporting Delays" in content


def test_safety_monitor_alert_caps(monitor):
    """Verify that alert caps consolidate multiple alerts for the same district into a digest."""
    incoming_alerts = [
        {"geo_id": "DXB-JA", "alert_tier": "warning", "syndrome": "heat"},
        {"geo_id": "DXB-JA", "alert_tier": "alert", "syndrome": "heat"},  # Excess alert for same district
        {"geo_id": "DXB-AQ", "alert_tier": "warning", "syndrome": "respiratory"},
    ]

    filtered = monitor.evaluate_alert_caps(incoming_alerts, max_active_alerts_per_district=1)

    assert len(filtered) == 3
    # First DXB-JA warning is preserved
    assert filtered[0]["geo_id"] == "DXB-JA"
    assert filtered[0]["alert_tier"] == "warning"
    assert "is_consolidated" not in filtered[0]

    # Second DXB-JA alert is capped and consolidated
    assert filtered[1]["geo_id"] == "DXB-JA"
    assert filtered[1]["is_consolidated"] is True
    assert filtered[1]["alert_tier"] == "watch"
    assert "alert cap exceeded" in filtered[1]["consolidation_reason"]

    # DXB-AQ alert is preserved
    assert filtered[2]["geo_id"] == "DXB-AQ"
    assert filtered[2]["alert_tier"] == "warning"


def test_safety_monitor_corroboration_rule(monitor):
    """Verify single-signal spikes are hard-capped at watch."""
    # Single-signal elevation must cap Warning or Alert at Watch
    assert monitor.enforce_corroboration_rule(raw_tier="warning", corroborating_signal_count=1) == "watch"
    assert monitor.enforce_corroboration_rule(raw_tier="alert", corroborating_signal_count=1) == "watch"
    assert monitor.enforce_corroboration_rule(raw_tier="watch", corroborating_signal_count=1) == "watch"

    # Multi-signal corroboration retains elevated tiers
    assert monitor.enforce_corroboration_rule(raw_tier="warning", corroborating_signal_count=2) == "warning"
    assert monitor.enforce_corroboration_rule(raw_tier="alert", corroborating_signal_count=3) == "alert"


def test_safety_monitor_dq_gating(monitor):
    """Verify that degraded data quality widens conformal uncertainty bands and caps severity."""
    # Nominal DQ (0.92)
    interval, tier, badge = monitor.apply_dq_gating(
        composite_dq=0.92, base_interval=[0.60, 0.80], base_tier="warning"
    )
    assert interval == [0.60, 0.80]
    assert tier == "warning"
    assert badge == "NORMAL"

    # Degraded DQ (0.50)
    deg_interval, deg_tier, deg_badge = monitor.apply_dq_gating(
        composite_dq=0.50, base_interval=[0.60, 0.80], base_tier="warning"
    )
    assert deg_interval[0] < 0.60
    assert deg_interval[1] > 0.80
    assert deg_tier == "watch"
    assert deg_badge == "LOW_DATA_QUALITY"


def test_safety_monitor_ml_health_check_and_ears_rollback(monitor):
    """Verify automatic deterministic rollback to CDC EARS C2 baseline if ML fusion fails."""
    # ML healthy
    res_healthy = monitor.evaluate_ml_health_and_fallback(model_available=True, features={"f1": 1.0})
    assert res_healthy["is_fallback_mode"] is False
    assert res_healthy["active_engine"] == "LIGHTGBM_CALIBRATED_FUSION"

    # ML failure (model weights corrupted or missing)
    res_failure = monitor.evaluate_ml_health_and_fallback(
        model_available=False,
        features=None,
        historical_baseline_counts=[10.0, 11.0, 12.0, 10.0, 11.0, 12.0, 11.0, 10.0, 12.0, 35.0],
    )
    assert res_failure["is_fallback_mode"] is True
    assert res_failure["fallback_reason"] == "ML_HEALTH_FAILURE_ROLLBACK"
    assert res_failure["active_engine"] == "CDC_EARS_C2_DETERMINISTIC"
    assert res_failure["aberration_detected"] is True
    assert res_failure["ears_score"] > 2.0
    assert "OPERATIONAL SAFETY FALLBACK ACTIVE" in res_failure["governance_notice"]


def test_fenced_llm_zero_hallucination_gate(monitor):
    """Verify rejection of generative narratives containing ungrounded phantom numbers."""
    evidence_numbers = [3.4, 92.5, 32.5, 48.0, 450.0]

    # Valid narrative: uses only evidence numbers or permitted calendar years
    valid_text = (
        "In 2025, PRAHARI observed 48.0 cases vs 32.5 expected with 3.4 days lead time and 92.5% sensitivity."
    )
    is_valid, msg = monitor.verify_fenced_narrative(valid_text, evidence_numbers)
    assert is_valid is True
    assert "verified compliant" in msg

    # Hallucinated narrative: invents a fake statistic '99.8%' or '7.5 days'
    hallucinated_text = (
        "Model predicts outbreak with 99.8% certainty and 7.5 days lead time."
    )
    is_invalid, err_msg = monitor.verify_fenced_narrative(hallucinated_text, evidence_numbers)
    assert is_invalid is False
    assert "Rejected hallucinated numerical token" in err_msg


def test_misuse_prevention_cohort_size_and_subsite_lockout(monitor):
    """Verify rejection of queries targeting small cohorts (N < 50), sub-site gangs, or clinical data."""
    # Cohort < 50
    ok, msg = monitor.validate_misuse_boundaries(user_role="employer_safety", workforce_size=35)
    assert ok is False
    assert "Workforce cohort size 35 < 50 minimum" in msg

    # Sub-site gang breakdown request
    ok, msg = monitor.validate_misuse_boundaries(
        user_role="employer_safety", workforce_size=100, requested_gang_breakdown=True
    )
    assert ok is False
    assert "Sub-site, shift, or gang-level disaggregation is prohibited" in msg

    # Employer attempting to access clinical syndromic data
    ok, msg = monitor.validate_misuse_boundaries(
        user_role="employer_safety", workforce_size=100, requested_clinical_data=True
    )
    assert ok is False
    assert "HTTP 403" in msg


def test_governance_scorecard_evaluation(monitor):
    """Verify that the Governance Scorecard evaluates all 7 controls with 100% compliance."""
    scorecard = monitor.generate_scorecard()

    assert scorecard.overall_status == "ALL_CONTROLS_VERIFIED"
    assert scorecard.total_controls_checked == 7
    assert scorecard.controls_passed == 7
    assert scorecard.compliance_score_pct == 100.0

    for control in scorecard.controls:
        assert control.status == "PASSED"
        assert control.governance_doc_link != ""
        assert control.automated_test_link != ""

