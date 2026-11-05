"""
PRAHARI Health & Resilience Impact Data Models
==============================================
Pydantic schemas and dataclasses defining assumptions, detection parameters,
impact calculation projections, scenario bounds, and district policy evidence summaries.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class AssumptionParameter(BaseModel):
    """Represents a single assumption with its value, unit, and bibliographic source."""
    value: float
    unit: str
    label: str
    source: str
    is_user_editable: bool = True
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    description: str = ""


class WorkforceAssumptions(BaseModel):
    """Workforce demographic and epidemiological parameters."""
    workforce_size: int = Field(
        default=50000,
        ge=1000,
        le=1000000,
        description="Total outdoor/vulnerable workforce in monitored jurisdiction (workers)"
    )
    baseline_heat_illness_rate: float = Field(
        default=0.025,
        ge=0.001,
        le=0.20,
        description="Seasonal baseline heat-illness / thermal distress incidence rate (fraction)"
    )
    workdays_lost_per_incident: float = Field(
        default=3.5,
        ge=0.5,
        le=30.0,
        description="Average workdays lost per heat-illness or acute respiratory incident (days)"
    )
    severe_case_fraction: float = Field(
        default=0.025,
        ge=0.001,
        le=0.15,
        description="Fraction of cases escalating to severe illness (e.g. heat stroke, ICU/ED admission)"
    )


class EconomicAssumptions(BaseModel):
    """Monetary cost and valuation parameters (in AED)."""
    cost_per_lost_workday_aed: float = Field(
        default=450.0,
        ge=50.0,
        le=5000.0,
        description="Economic cost per lost workday (daily wage + employer replacement/downtime cost in AED)"
    )
    severe_case_medical_cost_aed: float = Field(
        default=12000.0,
        ge=1000.0,
        le=100000.0,
        description="Emergency treatment and hospitalisation cost per severe case (AED)"
    )
    hourly_inspector_cost_aed: float = Field(
        default=120.0,
        ge=20.0,
        le=1000.0,
        description="Hourly cost of occupational safety inspector or triage nurse (AED)"
    )
    response_hours_per_false_alarm: float = Field(
        default=4.0,
        ge=0.5,
        le=40.0,
        description="Hours spent investigating or triaging a false alarm"
    )


class ClinicalAssumptions(BaseModel):
    """Intervention efficacy parameters."""
    preventability_coefficient: float = Field(
        default=0.65,
        ge=0.05,
        le=0.99,
        description="Fraction of detected incidents preventable if intervention begins >2 days earlier"
    )
    preventability_per_day_lead_time: float = Field(
        default=0.15,
        ge=0.01,
        le=0.30,
        description="Additional preventability gained per extra day of validated lead time"
    )


class DetectionPerformanceParams(BaseModel):
    """Empirical detection parameters from Phase 6 validation."""
    validated_lead_time_days: float = Field(
        default=3.4,
        ge=0.1,
        le=14.0,
        description="Validated mean lead time ahead of outbreak peaks (days)"
    )
    validated_sensitivity: float = Field(
        default=0.925,
        ge=0.1,
        le=1.0,
        description="Validated true positive detection sensitivity (fraction)"
    )
    false_alarm_rate_monthly: float = Field(
        default=0.32,
        ge=0.0,
        le=10.0,
        description="Validated false alarms per district per month"
    )
    monitored_districts: int = Field(
        default=4,
        ge=1,
        le=50,
        description="Number of monitored geographical districts"
    )
    season_months: float = Field(
        default=4.0,
        ge=1.0,
        le=12.0,
        description="Duration of high-risk surveillance season in months (e.g. Jun-Sep)"
    )


class ImpactCalculatorRequest(BaseModel):
    """Request payload for the impact calculator."""
    workforce: Optional[WorkforceAssumptions] = None
    economic: Optional[EconomicAssumptions] = None
    clinical: Optional[ClinicalAssumptions] = None
    detection: Optional[DetectionPerformanceParams] = None


class ScenarioImpact(BaseModel):
    """Outcome projections for a single scenario (Low, Central, or High)."""
    scenario_name: str
    description: str
    total_baseline_cases: float
    cases_detected: float
    cases_prevented: float
    lost_workdays_averted: float
    severe_incidents_averted: float
    workday_economic_savings_aed: float
    medical_cost_savings_aed: float
    gross_economic_benefit_aed: float
    total_false_alarms: float
    response_hours_spent: float
    false_alarm_response_cost_aed: float
    net_economic_benefit_aed: float
    benefit_cost_ratio: float
    alert_fatigue_overhead_pct: float


class ScenarioBounds(BaseModel):
    """Low, Central, and High scenario projections showing uncertainty bounds."""
    low_conservative: ScenarioImpact
    central_expected: ScenarioImpact
    high_optimistic: ScenarioImpact


class SensitivityCell(BaseModel):
    """Single cell in 2D sensitivity grid."""
    lead_time_days: float
    preventability_pct: float
    workdays_averted: float
    net_benefit_aed: float


class SensitivityMatrix(BaseModel):
    """2D sensitivity matrix varying lead time and preventability."""
    lead_time_steps: List[float]
    preventability_steps: List[float]
    grid: List[List[SensitivityCell]]


class ImpactEstimate(BaseModel):
    """Complete impact estimate result with transparent assumption auditing."""
    is_modelled_estimate: bool = True
    disclaimer: str = (
        "MODELLED ESTIMATE: All projections are calculated using validated detection sensitivity, "
        "empirical lead times, and explicit user-editable operational assumptions. "
        "These figures represent expected epidemiological averted burden under early intervention, "
        "not observed retrospective clinical incidence."
    )
    calculated_at: str
    central_estimate: ScenarioImpact
    scenarios: ScenarioBounds
    sensitivity: SensitivityMatrix
    assumptions_audit: Dict[str, AssumptionParameter]


class DistrictExposureBurden(BaseModel):
    """Exposure burden metrics for a specific district."""
    district_id: str
    district_name: str
    extreme_wbgt_hours_gt_32c: float
    danger_wbgt_hours_gt_34c: float
    pm25_exceedance_days: int
    midday_high_heat_days: int
    attributable_heat_stress_cases_suppressed: int
    data_suppression_applied: bool = True
    privacy_protection_method: str = "k-anonymity (k<=10) + Laplace Differential Privacy (epsilon=1.0)"


class PolicyRecommendation(BaseModel):
    """Actionable regulatory recommendation supported by exposure evidence."""
    policy_domain: str
    action_title: str
    target_districts: List[str]
    statutory_justification: str
    expected_workforce_protection: str
    priority_level: str


class DistrictPolicyEvidence(BaseModel):
    """Complete district policy evidence summary for municipal regulators."""
    reporting_period: str
    jurisdiction: str
    total_monitored_workforce: int
    districts: List[DistrictExposureBurden]
    policy_recommendations: List[PolicyRecommendation]
    statutory_citations: List[str]
    disclaimer: str = (
        "REGULATORY EVIDENCE BRIEF: Aggregated under differential privacy and small-cell suppression. "
        "Intended for municipal policy, midday work ban enforcement, and public health resource staging."
    )


class PolicyReportSummary(BaseModel):
    """Executive summary of policy report for quick consumption."""
    reporting_period: str
    total_extreme_heat_hours: float
    highest_risk_district: str
    total_preventable_cases_projected: float
    recommended_inspections: int
    estimated_avoidable_economic_loss_aed: float

