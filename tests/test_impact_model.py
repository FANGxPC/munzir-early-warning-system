"""
Unit & Integration Tests for PRAHARI Health & Resilience Impact Model (Phase 7)
"""

import pytest
from prahari.impact.models import (
    WorkforceAssumptions,
    EconomicAssumptions,
    ClinicalAssumptions,
    DetectionPerformanceParams,
    ImpactCalculatorRequest,
)
from prahari.impact.calculator import HealthResilienceImpactCalculator
from prahari.impact.policy_report import DistrictPolicyEvidenceGenerator


def test_default_assumptions_integrity():
    """Verify that all default model parameters have explicit bibliographic sources and bounds."""
    calc = HealthResilienceImpactCalculator()
    audit = calc.get_assumptions_audit()

    assert len(audit) >= 11
    assert "workforce_size" in audit
    assert "baseline_heat_illness_rate" in audit
    assert "preventability_coefficient" in audit
    assert "cost_per_lost_workday_aed" in audit
    assert "hourly_inspector_cost_aed" in audit
    assert "validated_lead_time_days" in audit
    assert "validated_sensitivity" in audit
    assert "false_alarm_rate_monthly" in audit

    for param_key, param in audit.items():
        assert param.source != "", f"Missing source citation for parameter: {param_key}"
        assert param.unit != "", f"Missing unit for parameter: {param_key}"
        assert param.value > 0.0, f"Non-positive value for parameter: {param_key}"


def test_central_impact_calculation():
    """Verify mathematical consistency and bounds of central expected impact projection."""
    calc = HealthResilienceImpactCalculator()
    result = calc.calculate()

    assert result.is_modelled_estimate is True
    assert "MODELLED ESTIMATE" in result.disclaimer

    central = result.central_estimate
    assert central.total_baseline_cases > 0
    assert central.cases_detected <= central.total_baseline_cases
    assert central.cases_prevented <= central.cases_detected
    assert central.lost_workdays_averted > 0
    assert central.severe_incidents_averted > 0

    # Economic metrics
    assert central.gross_economic_benefit_aed > 0
    assert central.false_alarm_response_cost_aed > 0
    assert central.net_economic_benefit_aed > 0
    assert central.net_economic_benefit_aed < central.gross_economic_benefit_aed

    # Alert fatigue cost must be bounded and small (<5% of gross economic benefit)
    assert central.alert_fatigue_overhead_pct < 5.0, (
        f"Alert fatigue overhead too high: {central.alert_fatigue_overhead_pct}%"
    )
    assert central.benefit_cost_ratio > 20.0, (
        f"Benefit-to-cost ratio lower than expected: {central.benefit_cost_ratio}"
    )


def test_scenario_bounds_ordering():
    """Verify that conservative <= expected <= optimistic ordering strictly holds."""
    calc = HealthResilienceImpactCalculator()
    result = calc.calculate()

    low = result.scenarios.low_conservative
    central = result.scenarios.central_expected
    high = result.scenarios.high_optimistic

    # Net benefit ordering
    assert low.net_economic_benefit_aed < central.net_economic_benefit_aed < high.net_economic_benefit_aed
    # Workdays averted ordering
    assert low.lost_workdays_averted < central.lost_workdays_averted < high.lost_workdays_averted
    # Cases prevented ordering
    assert low.cases_prevented < central.cases_prevented < high.cases_prevented


def test_sensitivity_matrix_monotonicity():
    """Verify that 2D sensitivity matrix behaves monotonically with lead time and preventability."""
    calc = HealthResilienceImpactCalculator()
    sensitivity = calc.compute_sensitivity_matrix()

    assert len(sensitivity.lead_time_steps) == 6
    assert len(sensitivity.preventability_steps) == 6
    assert len(sensitivity.grid) == 6

    # Test row-wise monotonicity: For a fixed lead time, increasing preventability increases net benefit
    for row in sensitivity.grid:
        for j in range(len(row) - 1):
            assert row[j].net_benefit_aed <= row[j + 1].net_benefit_aed
            assert row[j].workdays_averted <= row[j + 1].workdays_averted

    # Test column-wise monotonicity: For a fixed preventability, increasing lead time increases net benefit
    for col_idx in range(len(sensitivity.preventability_steps)):
        for row_idx in range(len(sensitivity.lead_time_steps) - 1):
            cell_current = sensitivity.grid[row_idx][col_idx]
            cell_next = sensitivity.grid[row_idx + 1][col_idx]
            assert cell_current.net_benefit_aed <= cell_next.net_benefit_aed


def test_user_editable_custom_request():
    """Verify that custom assumptions scale outcomes appropriately."""
    calc = HealthResilienceImpactCalculator()

    # Scale workforce down to 10,000 workers (1/5th of default 50,000)
    req = ImpactCalculatorRequest(
        workforce=WorkforceAssumptions(workforce_size=10000),
        economic=EconomicAssumptions(cost_per_lost_workday_aed=500.0),
    )
    result = calc.calculate(req)

    # 10,000 workers with 2.5% rate = 250 baseline cases
    assert result.central_estimate.total_baseline_cases == 250.0
    # Audit trail must reflect custom input
    assert result.assumptions_audit["workforce_size"].value == 10000.0


def test_district_policy_evidence_generator():
    """Verify privacy-preserving aggregate policy evidence report generation."""
    gen = DistrictPolicyEvidenceGenerator(random_seed=42)
    report = gen.generate_policy_evidence_report(month_name="August 2024")

    assert report.reporting_period == "August 2024"
    assert report.total_monitored_workforce == 50000
    assert len(report.districts) == 4

    for dist in report.districts:
        assert dist.extreme_wbgt_hours_gt_32c > 100.0
        assert dist.data_suppression_applied is True
        # Small-cell suppression: either 0 (suppressed) or > 10
        assert dist.attributable_heat_stress_cases_suppressed == 0 or dist.attributable_heat_stress_cases_suppressed > 10

    # Verify statutory recommendations
    assert len(report.policy_recommendations) >= 3
    for rec in report.policy_recommendations:
        assert len(rec.target_districts) > 0
        assert rec.statutory_justification != ""
        assert rec.priority_level != ""

    # Verify Markdown export
    md = gen.export_markdown_brief(report)
    assert "# PRAHARI Regulatory Policy Evidence Brief" in md
    assert "MOHRE Statutory Midday Work Ban" in md
    assert "Differential Privacy" in md


def test_policy_report_summary():
    """Verify executive summary metrics calculations."""
    gen = DistrictPolicyEvidenceGenerator(random_seed=42)
    summary = gen.generate_summary()

    assert summary.total_extreme_heat_hours > 400.0
    assert summary.highest_risk_district != ""
    assert summary.total_preventable_cases_projected > 0.0
    assert summary.estimated_avoidable_economic_loss_aed > 0.0

