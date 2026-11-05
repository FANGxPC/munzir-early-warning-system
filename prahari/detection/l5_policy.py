"""
L5 Layer: Anti-Alert-Fatigue Policy Engine.
Implements multi-signal corroboration rules, severity tiers (Watch/Warning/Alert),
hysteresis, deduplication, and data-quality gates preventing false alarms on backlog dumps.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Any, Optional, Set, Tuple
from uuid import uuid4

from prahari.detection.l4_fusion import FusionPrediction


class AlertSeverity(str, Enum):
    NONE = "none"
    WATCH = "watch"       # Low severity: monitor and verify feeds
    WARNING = "warning"   # Medium severity: targeted preventive actions (hydration, advisories)
    ALERT = "alert"       # High severity: rapid response team / site work-rest stoppages


@dataclass
class PrahariAlert:
    """Standardized decision-ready alert emitted by PRAHARI L5 policy."""
    alert_id: str = field(default_factory=lambda: f"ALT-{str(uuid4())[:8].upper()}")
    incident_id: str = ""
    alert_type: str = "cluster"          # heat_cluster, respiratory_surge, infectious_cluster, data_artefact
    severity: AlertSeverity = AlertSeverity.WATCH
    probability: float = 0.5
    ci_low: float = 0.4
    ci_high: float = 0.6
    geo_ids: List[str] = field(default_factory=list)
    obs_date: str = "2026-06-01"
    signal_contributions: Dict[str, float] = field(default_factory=dict)
    dq_status: str = "healthy"
    owner_role: str = "District Surveillance Officer"
    recommended_action: str = "Monitor feeds"
    is_suppressed_decoy: bool = False


# Munzir (منذر) Brand Alias
MunzirAlert = PrahariAlert


class L5AlertPolicyEngine:
    """
    Evaluates calibrated probabilities against multi-signal corroboration,
    data quality gates, and hysteresis rules to prevent alert fatigue.
    """

    def __init__(
        self,
        p_watch: float = 0.35,
        p_warning: float = 0.65,
        p_alert: float = 0.82,
        min_corroborating_groups: int = 2,
        completeness_gate_threshold: float = 0.60,
        backlog_latency_threshold_hrs: float = 48.0,
    ):
        self.p_watch = p_watch
        self.p_warning = p_warning
        self.p_alert = p_alert
        self.min_corroborating_groups = min_corroborating_groups
        self.completeness_gate_threshold = completeness_gate_threshold
        self.backlog_latency_threshold_hrs = backlog_latency_threshold_hrs

        # Active tracking for hysteresis and deduplication
        # geo_id -> consecutive days above p_watch
        self.consecutive_elevated_days: Dict[str, int] = {}
        # geo_id -> active incident_id
        self.active_incidents: Dict[str, str] = {}

    def evaluate(
        self,
        prediction: FusionPrediction,
        geo_id: str,
        obs_date: str,
        l3_clusters: Optional[List[Any]] = None,
        is_backlog_dump: bool = False,
        feed_completeness: Optional[float] = None,
        source_latency_hrs: Optional[float] = None,
        target_scenario_hint: Optional[str] = None,
    ) -> PrahariAlert:
        """
        Unified evaluation interface extracting contextual parameters.
        Returns PrahariAlert (with severity NONE if below Watch threshold).
        """
        fv = prediction.feature_vector or {}
        comp = feed_completeness if feed_completeness is not None else float(fv.get("dq_completeness_score", 1.0))
        lat_hrs = source_latency_hrs if source_latency_hrs is not None else float(fv.get("dq_source_latency_hrs", 1.0))

        # Check L3 cluster significance for geo_id
        l3_sig = False
        if l3_clusters:
            for cl in l3_clusters:
                if hasattr(cl, "member_geo_ids") and geo_id in cl.member_geo_ids and getattr(cl, "is_significant", False):
                    l3_sig = True
                    break

        alert = self.evaluate_alert(
            prediction=prediction,
            geo_id=geo_id,
            obs_date=obs_date,
            l3_is_significant=l3_sig,
            is_backlog_dump=is_backlog_dump,
            feed_completeness=comp,
            source_latency_hrs=lat_hrs,
            target_scenario_hint=target_scenario_hint,
        )

        if alert is None:
            return PrahariAlert(
                severity=AlertSeverity.NONE,
                probability=prediction.probability,
                ci_low=prediction.ci_low,
                ci_high=prediction.ci_high,
                geo_ids=[geo_id],
                obs_date=obs_date,
                signal_contributions=prediction.shap_contributions,
                dq_status="healthy",
                recommended_action="Normal monitoring baseline",
            )
        return alert

    def evaluate_alert(
        self,
        prediction: FusionPrediction,
        geo_id: str,
        obs_date: str,
        l3_is_significant: bool = False,
        is_backlog_dump: bool = False,
        feed_completeness: float = 1.0,
        source_latency_hrs: float = 1.0,
        target_scenario_hint: Optional[str] = None,
    ) -> Optional[PrahariAlert]:
        """
        Processes fusion predictions through anti-fatigue policy gates.
        Returns PrahariAlert if Watch/Warning/Alert tier is reached, else None.
        """
        prob = prediction.probability
        shap_groups = prediction.shap_contributions

        # 1. Backlog Dump Decoy Gate (Anti-Fatigue)
        # If latency spiked > 48h or flagged as backlog artefact, suppress Alert/Warning
        if is_backlog_dump or source_latency_hrs >= self.backlog_latency_threshold_hrs:
            return PrahariAlert(
                alert_type="data_artefact",
                severity=AlertSeverity.WATCH,
                probability=prob,
                ci_low=prediction.ci_low,
                ci_high=prediction.ci_high,
                geo_ids=[geo_id],
                obs_date=obs_date,
                signal_contributions=shap_groups,
                dq_status="Data Artefact — Reporting Backlog Dump (Alert Suppressed)",
                owner_role="Data Quality Officer",
                recommended_action="Verify reporting facility queue; do not deploy field units",
                is_suppressed_decoy=True,
            )

        # Base probability check: below Watch threshold -> No alert
        if prob < self.p_watch:
            self.consecutive_elevated_days[geo_id] = 0
            self.active_incidents.pop(geo_id, None)
            return None

        # 1b. Epidemiological Validity Gate:
        # An outbreak alert requires positive contribution from primary health/sickness signal
        is_site = "SITE" in geo_id
        if is_site:
            has_health_signal = (
                shap_groups.get("workplace", 0.0) > 0.08
                or shap_groups.get("clinical", 0.0) > 0.08
            )
        else:
            has_health_signal = shap_groups.get("clinical", 0.0) > 0.08

        if not has_health_signal:
            self.consecutive_elevated_days[geo_id] = 0
            self.active_incidents.pop(geo_id, None)
            return None

        # 2. Multi-Signal Corroboration Rule
        # Count independent elevated signal groups with positive attribution
        elevated_groups = [
            grp for grp, val in shap_groups.items()
            if val > 0.05 and grp in ["clinical", "workplace", "environmental", "spatiotemporal"]
        ]
        n_corroborating = len(elevated_groups)

        # 3. Consecutive Days Tracking (Hysteresis)
        prev_consecutive = self.consecutive_elevated_days.get(geo_id, 0)
        curr_consecutive = prev_consecutive + 1
        self.consecutive_elevated_days[geo_id] = curr_consecutive

        # Deduplication incident ID
        if geo_id not in self.active_incidents:
            self.active_incidents[geo_id] = f"INC-{obs_date.replace('-', '')}-{geo_id}"
        incident_id = self.active_incidents[geo_id]

        # 4. Severity Tier Assignment
        # Default tier: WATCH
        severity = AlertSeverity.WATCH

        # Can only reach WARNING if prob >= p_warning AND >= 2 signal groups agree!
        if prob >= self.p_warning and n_corroborating >= self.min_corroborating_groups:
            severity = AlertSeverity.WARNING

        # Can only reach ALERT if prob >= p_alert AND (cluster significant OR sustained 2+ days)
        if prob >= self.p_alert and n_corroborating >= self.min_corroborating_groups:
            if l3_is_significant or curr_consecutive >= 2:
                severity = AlertSeverity.ALERT

        # 5. Data Quality Gate: Cap severity if completeness is low
        dq_status = "healthy"
        if feed_completeness < self.completeness_gate_threshold:
            if severity in [AlertSeverity.WARNING, AlertSeverity.ALERT]:
                severity = AlertSeverity.WATCH
            dq_status = f"Low Confidence — Missing Data ({feed_completeness*100:.0f}% completeness)"

        # 6. Role and Action Mapping
        alert_type, owner_role, action = self._resolve_alert_context(
            geo_id=geo_id,
            shap_groups=shap_groups,
            severity=severity,
            scenario_hint=target_scenario_hint,
        )

        return PrahariAlert(
            incident_id=incident_id,
            alert_type=alert_type,
            severity=severity,
            probability=prob,
            ci_low=prediction.ci_low,
            ci_high=prediction.ci_high,
            geo_ids=[geo_id],
            obs_date=obs_date,
            signal_contributions=shap_groups,
            dq_status=dq_status,
            owner_role=owner_role,
            recommended_action=action,
            is_suppressed_decoy=False,
        )

    def _resolve_alert_context(
        self,
        geo_id: str,
        shap_groups: Dict[str, float],
        severity: AlertSeverity,
        scenario_hint: Optional[str] = None,
    ) -> Tuple[str, str, str]:
        """Resolves alert category, responsible role, and proportionate action."""
        is_site = "SITE" in geo_id

        # Determine dominant driver
        env_shap = shap_groups.get("environmental", 0.0)
        work_shap = shap_groups.get("workplace", 0.0)
        clin_shap = shap_groups.get("clinical", 0.0)

        if is_site and (env_shap > 0.1 or work_shap > 0.1 or scenario_hint == "heat_cluster"):
            # Flagship 1: Worksite heat hazard
            owner = "Site Safety Officer"
            if severity == AlertSeverity.ALERT:
                action = "Mandatory work-rest cycles (15 min rest/hr), shade stations, pause unshaded roof/steel tasks"
            elif severity == AlertSeverity.WARNING:
                action = "Issue site heat advisory, enforce hydration breaks every 30 minutes, buddy system"
            else:
                action = "Monitor WBGT index forecast and prepare electrolyte hydration points"
            return "heat_cluster", owner, action

        elif clin_shap > 0.1 and env_shap > 0.1:
            # Flagship 2: Pollution-driven respiratory surge
            owner = "District Health Officer"
            if severity in [AlertSeverity.ALERT, AlertSeverity.WARNING]:
                action = "Issue public respiratory advisory, distribute N95 masks to outdoor laborers, prepare clinic nebulizer surge"
            else:
                action = "Monitor PM2.5 forecast and track pharmacy asthma inhaler dispense rates"
            return "respiratory_surge", owner, action

        else:
            # Flagship 3: Unexplained point-source infectious cluster
            owner = "District Surveillance Officer (Rapid Response Team)"
            if severity == AlertSeverity.ALERT:
                action = "Deploy Rapid Response Team for field investigation, food/water sampling at facility canteen"
            elif severity == AlertSeverity.WARNING:
                action = "Contact facility occupational nurse, initiate active syndromic case finding, test water tank"
            else:
                action = "Verify laboratory positivity feed and track clinic GI admission trend"
            return "infectious_cluster", owner, action
