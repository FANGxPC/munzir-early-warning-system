"""
PRAHARI Health & Resilience Impact Calculator
=============================================
Calculates modelled epidemiological burden averted, lost workdays saved,
false alarm fatigue costs, and net economic benefits for the UAE / Dubai
heat-health surveillance operational theater.

All figures are explicitly marked as modelled projections with traceable assumptions.
"""

from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
import math
import numpy as np

from prahari.impact.models import (
    AssumptionParameter,
    WorkforceAssumptions,
    EconomicAssumptions,
    ClinicalAssumptions,
    DetectionPerformanceParams,
    ImpactCalculatorRequest,
    ScenarioImpact,
    ScenarioBounds,
    SensitivityCell,
    SensitivityMatrix,
    ImpactEstimate,
)


class HealthResilienceImpactCalculator:
    """
    Mathematical health and economic impact projection engine.
    Translates early warning lead time and sensitivity into:
      1. Workdays averted per season
      2. High-severity incidents prevented (heat stroke / ED admissions)
      3. Bounded operational response costs (alert fatigue overhead)
      4. Net economic value delivered under low, central, and high scenarios.
    """

    def __init__(
        self,
        workforce: Optional[WorkforceAssumptions] = None,
        economic: Optional[EconomicAssumptions] = None,
        clinical: Optional[ClinicalAssumptions] = None,
        detection: Optional[DetectionPerformanceParams] = None,
    ):
        self.workforce = workforce or WorkforceAssumptions()
        self.economic = economic or EconomicAssumptions()
        self.clinical = clinical or ClinicalAssumptions()
        self.detection = detection or DetectionPerformanceParams()

    def get_assumptions_audit(self) -> Dict[str, AssumptionParameter]:
        """Returns traceable dictionary of all model assumptions with published citations."""
        return {
            "workforce_size": AssumptionParameter(
                value=float(self.workforce.workforce_size),
                unit="workers",
                label="Monitored Outdoor Workforce Size",
                source="Dubai Statistics Center & MOHRE Labor Registry (Construction & Logistics)",
                min_value=1000.0,
                max_value=1000000.0,
                description="Total exposed workforce across the 4 active monitoring districts.",
            ),
            "baseline_heat_illness_rate": AssumptionParameter(
                value=self.workforce.baseline_heat_illness_rate,
                unit="fraction/season",
                label="Baseline Heat Illness Rate",
                source="ILO (2019) 'Working on a warmer planet' & Lancet Countdown MENA",
                min_value=0.001,
                max_value=0.20,
                description="Expected seasonal rate of heat distress / thermal exhaustion without predictive alerting.",
            ),
            "workdays_lost_per_incident": AssumptionParameter(
                value=self.workforce.workdays_lost_per_incident,
                unit="days/incident",
                label="Average Lost Workdays per Incident",
                source="OSHA / NIOSH Occupational Heat Stress Health Economics Review",
                min_value=0.5,
                max_value=30.0,
                description="Direct sick leave and reduced-capacity recovery days per heat incident.",
            ),
            "severe_case_fraction": AssumptionParameter(
                value=self.workforce.severe_case_fraction,
                unit="fraction of cases",
                label="Severe Heat Case Fraction",
                source="Emergency Medicine Heat Stroke vs Heat Exhaustion Cohort Analysis",
                min_value=0.001,
                max_value=0.15,
                description="Proportion of heat distress cases escalating to severe hyperthermia or hospitalisation.",
            ),
            "cost_per_lost_workday_aed": AssumptionParameter(
                value=self.economic.cost_per_lost_workday_aed,
                unit="AED/day",
                label="Economic Cost per Lost Workday",
                source="UAE MOHRE Median Daily Wage + Employer Idle Machinery & Shift Substitution Overhead",
                min_value=50.0,
                max_value=5000.0,
                description="Comprehensive economic value lost per worker per absent workday.",
            ),
            "severe_case_medical_cost_aed": AssumptionParameter(
                value=self.economic.severe_case_medical_cost_aed,
                unit="AED/case",
                label="Severe Case Emergency Care Cost",
                source="Dubai Health Authority (DHA) Inpatient DRG Tariff for Critical Heat Shock",
                min_value=1000.0,
                max_value=100000.0,
                description="Direct acute medical care, emergency transport, and ICU stabilization cost.",
            ),
            "hourly_inspector_cost_aed": AssumptionParameter(
                value=self.economic.hourly_inspector_cost_aed,
                unit="AED/hour",
                label="Occupational Safety Triage Cost",
                source="Dubai Municipality / EHS Environmental Health Officer Hourly Burden Rate",
                min_value=20.0,
                max_value=1000.0,
                description="Cost of clinical triage nurse or safety officer response time.",
            ),
            "response_hours_per_false_alarm": AssumptionParameter(
                value=self.economic.response_hours_per_false_alarm,
                unit="hours/alert",
                label="Staff Hours per False Alarm Investigation",
                source="Standard Operating Procedure for Workplace Health Inspection Triage",
                min_value=0.5,
                max_value=40.0,
                description="Hours spent reviewing and triaging an alert determined to be non-actionable.",
            ),
            "preventability_coefficient": AssumptionParameter(
                value=self.clinical.preventability_coefficient,
                unit="fraction preventable",
                label="Intervention Preventability Factor",
                source="Occupational Heat Intervention Trials (MOHRE Rest & Hydration Regimens)",
                min_value=0.05,
                max_value=0.99,
                description="Fraction of potential heat illness cases averted given proactive lead time >2 days.",
            ),
            "validated_lead_time_days": AssumptionParameter(
                value=self.detection.validated_lead_time_days,
                unit="days",
                label="Validated Fusion Lead Time",
                source="Munzir Phase 6 Empirical Rolling-Origin Backtest (+2.6d over fixed baseline)",
                min_value=0.1,
                max_value=14.0,
                description="Days of advance notice delivered ahead of peak community/worksite heat stress.",
            ),
            "validated_sensitivity": AssumptionParameter(
                value=self.detection.validated_sensitivity,
                unit="fraction",
                label="Validated Detection Sensitivity",
                source="Munzir Phase 6 100+ Outbreak Injection Study",
                min_value=0.1,
                max_value=1.0,
                description="Proportion of genuine heat/outbreak surges successfully triggered.",
            ),
            "false_alarm_rate_monthly": AssumptionParameter(
                value=self.detection.false_alarm_rate_monthly,
                unit="alerts/district/month",
                label="False Alarm Rate",
                source="Munzir Phase 6 Empirical Evaluation (65% lower than CDC EARS C2)",
                min_value=0.0,
                max_value=10.0,
                description="Empirically validated false alarm frequency under L5 corroboration rules.",
            ),
        }

    def _compute_single_scenario(
        self,
        name: str,
        desc: str,
        workforce: WorkforceAssumptions,
        economic: EconomicAssumptions,
        clinical: ClinicalAssumptions,
        detection: DetectionPerformanceParams,
        preventability_override: Optional[float] = None,
        baseline_rate_multiplier: float = 1.0,
        economic_cost_multiplier: float = 1.0,
        response_cost_multiplier: float = 1.0,
    ) -> ScenarioImpact:
        """Computes impact metrics for a single scenario configuration."""
        eff_baseline_rate = max(0.0001, min(0.5, workforce.baseline_heat_illness_rate * baseline_rate_multiplier))
        total_baseline_cases = workforce.workforce_size * eff_baseline_rate

        cases_detected = total_baseline_cases * detection.validated_sensitivity

        if preventability_override is not None:
            eff_preventability = preventability_override
        else:
            # Preventability increases with lead time beyond 2.0 days
            lead_time_delta = max(0.0, detection.validated_lead_time_days - 2.0)
            eff_preventability = min(
                0.95,
                clinical.preventability_coefficient
                + lead_time_delta * clinical.preventability_per_day_lead_time,
            )

        cases_prevented = cases_detected * eff_preventability
        workdays_averted = cases_prevented * workforce.workdays_lost_per_incident
        severe_averted = cases_prevented * workforce.severe_case_fraction

        workday_cost = economic.cost_per_lost_workday_aed * economic_cost_multiplier
        medical_cost = economic.severe_case_medical_cost_aed * economic_cost_multiplier

        workday_savings_aed = workdays_averted * workday_cost
        medical_savings_aed = severe_averted * medical_cost
        gross_economic_benefit_aed = workday_savings_aed + medical_savings_aed

        total_false_alarms = (
            detection.false_alarm_rate_monthly
            * detection.monitored_districts
            * detection.season_months
        )
        response_hours_spent = total_false_alarms * economic.response_hours_per_false_alarm
        false_alarm_response_cost_aed = (
            response_hours_spent
            * economic.hourly_inspector_cost_aed
            * response_cost_multiplier
        )

        net_economic_benefit_aed = gross_economic_benefit_aed - false_alarm_response_cost_aed
        bcr = gross_economic_benefit_aed / max(1.0, false_alarm_response_cost_aed)
        fatigue_overhead_pct = (
            false_alarm_response_cost_aed / max(1.0, gross_economic_benefit_aed)
        ) * 100.0

        return ScenarioImpact(
            scenario_name=name,
            description=desc,
            total_baseline_cases=round(total_baseline_cases, 1),
            cases_detected=round(cases_detected, 1),
            cases_prevented=round(cases_prevented, 1),
            lost_workdays_averted=round(workdays_averted, 1),
            severe_incidents_averted=round(severe_averted, 1),
            workday_economic_savings_aed=round(workday_savings_aed, 2),
            medical_cost_savings_aed=round(medical_savings_aed, 2),
            gross_economic_benefit_aed=round(gross_economic_benefit_aed, 2),
            total_false_alarms=round(total_false_alarms, 1),
            response_hours_spent=round(response_hours_spent, 1),
            false_alarm_response_cost_aed=round(false_alarm_response_cost_aed, 2),
            net_economic_benefit_aed=round(net_economic_benefit_aed, 2),
            benefit_cost_ratio=round(bcr, 2),
            alert_fatigue_overhead_pct=round(fatigue_overhead_pct, 2),
        )

    def compute_scenarios(self) -> ScenarioBounds:
        """Computes Low (conservative), Central (expected), and High (optimistic) scenarios."""
        # 1. Central: Validated baseline parameters
        central = self._compute_single_scenario(
            name="Central Expected Scenario",
            desc="Modelled baseline using validated detection parameters and standard MOHRE guidance.",
            workforce=self.workforce,
            economic=self.economic,
            clinical=self.clinical,
            detection=self.detection,
        )

        # 2. Low: Conservative assumptions (lower baseline rate, lower preventability, higher false alarm triage cost)
        low = self._compute_single_scenario(
            name="Conservative Lower Bound",
            desc="Lower baseline heat illness (1.8%), 40% preventability, and higher triage cost per alarm.",
            workforce=self.workforce,
            economic=self.economic,
            clinical=self.clinical,
            detection=self.detection,
            preventability_override=0.40,
            baseline_rate_multiplier=0.72,  # 2.5% -> 1.8%
            economic_cost_multiplier=0.85,
            response_cost_multiplier=1.30,
        )

        # 3. High: Optimistic assumptions (elevated heat wave season, 82% preventability, higher wage valuations)
        high = self._compute_single_scenario(
            name="Optimistic Upper Bound",
            desc="Severe heat season (3.2% incidence), 82% preventability with rapid worksite adherence.",
            workforce=self.workforce,
            economic=self.economic,
            clinical=self.clinical,
            detection=self.detection,
            preventability_override=0.82,
            baseline_rate_multiplier=1.28,  # 2.5% -> 3.2%
            economic_cost_multiplier=1.20,
            response_cost_multiplier=0.85,
        )

        return ScenarioBounds(
            low_conservative=low,
            central_expected=central,
            high_optimistic=high,
        )

    def compute_sensitivity_matrix(self) -> SensitivityMatrix:
        """
        Computes 2D sensitivity grid varying lead time (1.0 to 5.0 days)
        and intervention preventability (30% to 85%).
        """
        lead_time_steps = [1.0, 2.0, 3.0, 3.4, 4.0, 5.0]
        preventability_steps = [0.30, 0.45, 0.60, 0.65, 0.75, 0.85]

        grid: List[List[SensitivityCell]] = []

        for lt in lead_time_steps:
            row: List[SensitivityCell] = []
            det_variant = self.detection.model_copy(update={"validated_lead_time_days": lt})
            for prev in preventability_steps:
                scen = self._compute_single_scenario(
                    name=f"LT={lt}d_Prev={int(prev*100)}%",
                    desc="",
                    workforce=self.workforce,
                    economic=self.economic,
                    clinical=self.clinical,
                    detection=det_variant,
                    preventability_override=prev,
                )
                row.append(
                    SensitivityCell(
                        lead_time_days=lt,
                        preventability_pct=round(prev * 100.0, 1),
                        workdays_averted=scen.lost_workdays_averted,
                        net_benefit_aed=scen.net_economic_benefit_aed,
                    )
                )
            grid.append(row)

        return SensitivityMatrix(
            lead_time_steps=lead_time_steps,
            preventability_steps=[round(p * 100.0, 1) for p in preventability_steps],
            grid=grid,
        )

    def compute_monte_carlo_distribution(
        self, n_samples: int = 1000, seed: int = 42
    ) -> Dict[str, Any]:
        """
        Runs Monte Carlo simulation across assumption ranges to replace single-point
        estimates with credible uncertainty distributions (median and 90% interval).
        Incorporates direct operational intervention staging costs alongside false alarm triage.
        """
        import numpy as np
        rng = np.random.RandomState(seed)

        # Sample parameters uniformly across conservative and optimistic bounds
        s_base_rate = rng.uniform(0.015, 0.040, n_samples)
        s_preventability = rng.uniform(0.45, 0.85, n_samples)
        s_workdays = rng.uniform(2.0, 5.0, n_samples)
        s_wage = rng.uniform(350.0, 600.0, n_samples)
        s_hosp = rng.uniform(8000.0, 18000.0, n_samples)
        s_severe_frac = rng.uniform(0.015, 0.045, n_samples)
        s_inspector = rng.uniform(90.0, 160.0, n_samples)
        # Operational worksite staging cost per monitored worker across season (AED 2.0 to 6.0 / worker)
        s_op_cost_per_worker = rng.uniform(2.0, 6.0, n_samples)

        workforce = float(self.workforce.workforce_size)
        sensitivity = float(self.detection.validated_sensitivity)

        baseline_cases = workforce * s_base_rate
        cases_detected = baseline_cases * sensitivity
        cases_prevented = cases_detected * s_preventability
        workdays_saved = cases_prevented * s_workdays
        severe_averted = cases_prevented * s_severe_frac

        gross_benefit = (workdays_saved * s_wage) + (severe_averted * s_hosp)

        # Response costs: false alarm triage + operational staging
        total_false_alarms = self.detection.false_alarm_rate_monthly * self.detection.monitored_districts * self.detection.season_months
        response_cost = (total_false_alarms * 4.0 * s_inspector) + (workforce * s_op_cost_per_worker)

        net_benefit = gross_benefit - response_cost
        bcr = gross_benefit / np.maximum(100.0, response_cost)

        def pct(arr: np.ndarray) -> Dict[str, float]:
            return {
                "median": round(float(np.percentile(arr, 50)), 2),
                "p05": round(float(np.percentile(arr, 5)), 2),
                "p95": round(float(np.percentile(arr, 95)), 2),
                "mean": round(float(np.mean(arr)), 2),
            }

        return {
            "n_samples": n_samples,
            "seed": seed,
            "cases_prevented": pct(cases_prevented),
            "workdays_saved": pct(workdays_saved),
            "severe_averted": pct(severe_averted),
            "gross_benefit_aed": pct(gross_benefit),
            "total_program_cost_aed": pct(response_cost),
            "net_benefit_aed": pct(net_benefit),
            "benefit_cost_ratio": pct(bcr),
            "methodology_note": (
                "Monte Carlo output incorporates realistic operational intervention staging costs "
                "alongside false alarm triage, replacing the uncalibrated single-point ratio with a 90% confidence distribution."
            ),
        }

    def calculate(
        self, request: Optional[ImpactCalculatorRequest] = None
    ) -> ImpactEstimate:
        """Executes full impact calculation pipeline returning audited projections."""
        if request:
            if request.workforce:
                self.workforce = request.workforce
            if request.economic:
                self.economic = request.economic
            if request.clinical:
                self.clinical = request.clinical
            if request.detection:
                self.detection = request.detection

        scenarios = self.compute_scenarios()
        sensitivity = self.compute_sensitivity_matrix()
        assumptions = self.get_assumptions_audit()
        mc_dist = self.compute_monte_carlo_distribution()

        return ImpactEstimate(
            is_modelled_estimate=True,
            calculated_at=datetime.now(timezone.utc).isoformat(),
            central_estimate=scenarios.central_expected,
            scenarios=scenarios,
            sensitivity=sensitivity,
            assumptions_audit=assumptions,
            monte_carlo_distribution=mc_dist,
        )

