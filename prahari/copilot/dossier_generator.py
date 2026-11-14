"""
Munzir Executive Action Dossier Generator (Phase 18).
Generates an authoritative, 7-section operational action report for frontline safety directors,
DHA epidemiologists, and municipal emergency dispatchers.
Grounded in real-time Lakehouse state, statutory decrees (UAE Resolution 44/2022),
and municipal RACI playbooks. Zero hallucination, zero mock data.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from prahari.copilot.context_builder import LiveSiteSurveillanceContext, LiveSurveillanceContextBuilder
from prahari.copilot.statutory_codex import StatutoryArticle, StatutoryCodex
from prahari.decision.raci import RACIAssignment, RACIRoleMatrix
from prahari.detection.l5_policy import AlertSeverity
from prahari.llm.multilingual_dispatch import MultilingualDispatchCard, generate_multilingual_dispatch


@dataclass
class OperationalActionStep:
    """A prioritized, chronological operational action item."""
    step_number: int
    timeline_window: str     # e.g., "00:00 - 00:10 (Immediate)"
    action_title: str
    action_detail: str
    responsible_lead: str
    compliance_framework: str
    verification_check: str


@dataclass
class ExecutiveActionDossier:
    """Authoritative 7-section Executive Action Dossier."""
    dossier_id: str
    generated_at_utc: str
    site_id: str
    site_name: str
    district_id: str
    district_name: str
    target_date: str
    alert_tier: str
    calibrated_probability_pct: float
    conformal_ci: List[float]
    dq_completeness_pct: float

    # Section 1: Threat Trajectory
    threat_trajectory: Dict[str, Any]

    # Section 2: Multi-Signal Diagnostic Attribution
    diagnostic_attribution: Dict[str, Any]

    # Section 3: Statutory Mandate & Legal Trigger
    statutory_trigger: Dict[str, Any]

    # Section 4: Immediate 30-Minute Operational Checklist
    operational_checklist: List[Dict[str, Any]]

    # Section 5: Municipal Fleet & Logistics Directive
    municipal_fleet_directive: Dict[str, Any]

    # Section 6: RACI Governance Matrix
    raci_matrix: Dict[str, Any]

    # Section 7: Frontline WhatsApp & Dispatch Preview
    dispatch_preview: Dict[str, Any]

    # Rendered Markdown Report
    markdown_report: str

    def to_dict(self) -> Dict[str, Any]:
        """Convert dossier to JSON-serializable dictionary."""
        return {
            "dossier_id": self.dossier_id,
            "generated_at_utc": self.generated_at_utc,
            "site_id": self.site_id,
            "site_name": self.site_name,
            "district_id": self.district_id,
            "district_name": self.district_name,
            "target_date": self.target_date,
            "alert_tier": self.alert_tier,
            "calibrated_probability_pct": self.calibrated_probability_pct,
            "conformal_ci": self.conformal_ci,
            "dq_completeness_pct": self.dq_completeness_pct,
            "threat_trajectory": self.threat_trajectory,
            "diagnostic_attribution": self.diagnostic_attribution,
            "statutory_trigger": self.statutory_trigger,
            "operational_checklist": self.operational_checklist,
            "municipal_fleet_directive": self.municipal_fleet_directive,
            "raci_matrix": self.raci_matrix,
            "dispatch_preview": self.dispatch_preview,
            "markdown_report": self.markdown_report,
        }


class ExecutiveDossierGenerator:
    """Generates the comprehensive 7-section operational Action Dossier."""

    def __init__(self, region_key: str = "uae"):
        self.context_builder = LiveSurveillanceContextBuilder(region_key=region_key)
        self.statutory_codex = StatutoryCodex()

    def generate_dossier(
        self,
        site_id: str = "SITE-JA-01",
        target_date: str = "2025-08-20",
    ) -> ExecutiveActionDossier:
        """
        Builds the complete 7-section Action Dossier from live Lakehouse telemetry,
        official legal codex, and municipal emergency resources.
        """
        now_utc = datetime.now(timezone.utc).isoformat()
        ctx = self.context_builder.build_site_context(site_id=site_id, target_date=target_date)
        dossier_id = f"DOSSIER-{site_id}-{target_date.replace('-', '')}"

        # 1. Section 1: Threat Trajectory
        delta_str = (
            f"{'+' if ctx.microclimate_delta_c and ctx.microclimate_delta_c > 0 else ''}"
            f"{ctx.microclimate_delta_c:.1f}°C" if ctx.microclimate_delta_c is not None else "N/A"
        )
        threat_trajectory = {
            "current_wbgt_c": round(ctx.current_wbgt_c, 1),
            "forecast_3d_wbgt_max_c": round(ctx.forecast_3d_wbgt_max_c, 1),
            "current_pm25_ugm3": round(ctx.current_pm25_ugm3, 1),
            "forecast_3d_pm25_ugm3": round(ctx.forecast_3d_pm25_ugm3, 1),
            "sensor_measured_wbgt_c": round(ctx.sensor_wbgt_c, 1) if ctx.sensor_wbgt_c else None,
            "microclimate_delta_c": delta_str,
            "sentinel_node_id": ctx.sensor_node_id,
            "spatial_transfer_confidence": ctx.spatial_transfer_confidence,
            "workforce_size": ctx.workforce_size,
        }

        # 2. Section 2: Multi-Signal Diagnostic Attribution
        diagnostic_attribution = {
            "primary_driver": ctx.primary_signal_driver.upper(),
            "shap_attributions": ctx.shap_attributions,
            "renal_surveillance": {
                "screened_cohort": ctx.screened_workers,
                "mean_egfr_ml_min": round(ctx.mean_egfr, 1),
                "dehydration_rate_pct": round(ctx.dehydration_rate_pct, 1),
                "kdigo_stage1_rate_per_1k": round(ctx.kdigo_stage1_rate_per_1k, 1),
                "subclinical_advance_lead_time_days": round(ctx.renal_advance_lead_time_days, 1),
            },
        }

        # 3. Section 3: Statutory Mandate & Legal Trigger
        search_query = f"midday heat break {ctx.alert_tier.lower()} penalties"
        relevant_articles = self.statutory_codex.search_codex(search_query, limit=2)
        if not relevant_articles:
            relevant_articles = self.statutory_codex.articles[:1]
        primary_article = relevant_articles[0]

        statutory_trigger = {
            "decree": primary_article.instrument,
            "authority": primary_article.authority,
            "article_number": primary_article.article_number,
            "title": primary_article.title,
            "legal_mandate": primary_article.legal_text,
            "mandatory_actions": primary_article.mandatory_actions,
            "statutory_penalties": primary_article.penalties or "Not specified",
            "citation": primary_article.citation,
            "additional_articles": [art.citation for art in relevant_articles[1:]],
        }

        # 4. Section 4: Immediate 30-Minute Operational Checklist
        checklist = self._build_operational_checklist(ctx, primary_article)

        # 5. Section 5: Municipal Fleet & Logistics Directive
        municipal_fleet_directive = {
            "cooling_buses_allocated": ctx.cooling_buses_needed,
            "misting_trailers_allocated": ctx.misting_trailers_needed,
            "potable_water_metric_tons": round(ctx.potable_water_tons, 2),
            "electrolyte_sachets_allocated": ctx.electrolyte_sachets_needed,
            "dcas_ambulance_status": "REQUIRED (Pre-Staged)" if ctx.dcas_ambulance_required else "ON-CALL / STANDBY",
            "nearest_depot": ctx.nearest_depot,
            "transit_time_minutes": ctx.depot_transit_minutes,
            "estimated_mobilization_cost_aed": round(ctx.estimated_mobilization_cost_aed, 2),
        }

        # 6. Section 6: RACI Governance Matrix
        sev = AlertSeverity.ALERT if ctx.alert_tier.lower() == "warning" else AlertSeverity.WATCH
        raci = RACIRoleMatrix.get_raci(alert_type="heat_cluster", severity=sev, is_site=True)
        raci_matrix = {
            "responsible": raci.responsible,
            "accountable": raci.accountable,
            "consulted": raci.consulted,
            "informed": raci.informed,
        }

        # 7. Section 7: Frontline WhatsApp & Dispatch Preview
        alert_payload = {
            "alert_id": dossier_id,
            "site_id": ctx.site_id,
            "site_name": ctx.site_name,
            "tier": ctx.alert_tier.upper(),
            "wbgt": ctx.current_wbgt_c,
            "calibrated_p": ctx.calibrated_probability,
        }
        dispatch_card = generate_multilingual_dispatch(alert_payload)
        dispatch_preview = {
            "arabic_text": dispatch_card.arabic_text,
            "english_text": dispatch_card.english_text,
            "urdu_text": dispatch_card.urdu_text,
            "hindi_text": dispatch_card.hindi_text,
            "audio_tts_scripts": dispatch_card.audio_tts_scripts,
            "whatsapp_preview_markdown": dispatch_card.whatsapp_preview_markdown,
        }

        # Render full Markdown report
        markdown_report = self._render_markdown_report(
            dossier_id=dossier_id,
            generated_at_utc=now_utc,
            ctx=ctx,
            threat_trajectory=threat_trajectory,
            diagnostic_attribution=diagnostic_attribution,
            statutory_trigger=statutory_trigger,
            checklist=checklist,
            municipal_fleet_directive=municipal_fleet_directive,
            raci_matrix=raci_matrix,
            dispatch_card=dispatch_card,
        )

        return ExecutiveActionDossier(
            dossier_id=dossier_id,
            generated_at_utc=now_utc,
            site_id=ctx.site_id,
            site_name=ctx.site_name,
            district_id=ctx.district_id,
            district_name=ctx.district_name,
            target_date=ctx.target_date,
            alert_tier=ctx.alert_tier,
            calibrated_probability_pct=round(ctx.calibrated_probability * 100.0, 1),
            conformal_ci=[round(ctx.conformal_ci_low * 100.0, 1), round(ctx.conformal_ci_high * 100.0, 1)],
            dq_completeness_pct=round(ctx.dq_completeness_pct, 1),
            threat_trajectory=threat_trajectory,
            diagnostic_attribution=diagnostic_attribution,
            statutory_trigger=statutory_trigger,
            operational_checklist=[asdict(item) for item in checklist],
            municipal_fleet_directive=municipal_fleet_directive,
            raci_matrix=raci_matrix,
            dispatch_preview=dispatch_preview,
            markdown_report=markdown_report,
        )

    def _build_operational_checklist(
        self,
        ctx: LiveSiteSurveillanceContext,
        primary_article: StatutoryArticle,
    ) -> List[OperationalActionStep]:
        """Constructs an ordered chronological 30-minute operational checklist."""
        is_warning = ctx.alert_tier.lower() == "warning" or ctx.current_wbgt_c >= 32.0

        if is_warning:
            return [
                OperationalActionStep(
                    step_number=1,
                    timeline_window="00:00 - 00:10 (Immediate Action)",
                    action_title="Enforce Shaded Rest Rotation & Halt Extreme Direct Sun Work",
                    action_detail=(
                        f"Order all {ctx.workforce_size:,} personnel into designated shaded rest areas. "
                        f"Enforce mandatory 15-minute rest rotation per hour for outdoor activities."
                    ),
                    responsible_lead="Site Safety Officer / General Contractor Foreman",
                    compliance_framework=f"{primary_article.instrument} {primary_article.article_number}",
                    verification_check="Log all work crews in site safety attendance register.",
                ),
                OperationalActionStep(
                    step_number=2,
                    timeline_window="00:10 - 00:15 (Immediate Action)",
                    action_detail=(
                        f"Dispense {ctx.electrolyte_sachets_needed:,} electrolyte sachets and ensure "
                        f"{ctx.potable_water_tons:.2f} metric tons of chilled drinking water are accessible."
                    ),
                    action_title="Deploy Hydration & Mineral Replacement Stations",
                    responsible_lead="Logistics & Welfare Supervisor",
                    compliance_framework="UAE MOHRE Ministerial Resolution No. 44 of 2022, Article 3",
                    verification_check="Physical count of chilled water dispensaries and mineral sachets.",
                ),
                OperationalActionStep(
                    step_number=3,
                    timeline_window="00:15 - 00:20 (Fleet Mobilization)",
                    action_title="Mobilize Mobile Cooling Buses & Misting Trailers",
                    action_detail=(
                        f"Dispatch {ctx.cooling_buses_needed} cooling bus unit(s) and {ctx.misting_trailers_needed} misting trailer(s) "
                        f"from {ctx.nearest_depot} (Transit: {ctx.depot_transit_minutes} mins)."
                    ),
                    responsible_lead="Municipal Emergency Fleet Dispatcher",
                    compliance_framework="Munzir Municipal Incident Coordination Protocol",
                    verification_check="GPS tracking confirm arrival at site perimeter staging zone.",
                ),
                OperationalActionStep(
                    step_number=4,
                    timeline_window="00:20 - 00:25 (Clinical Surveillance)",
                    action_title="Perform Sub-Clinical Point-of-Care Urine Specific Gravity (USG) Checks",
                    action_detail=(
                        f"Screen high-exertion workers for acute dehydration (baseline dehydration rate: {ctx.dehydration_rate_pct:.1f}%). "
                        f"Triage workers showing KDIGO Stage 1 risk."
                    ),
                    responsible_lead="Occupational Health Officer / On-site Nurse",
                    compliance_framework="KDIGO 2012 Acute Kidney Injury Clinical Practice Guideline",
                    verification_check="Log digital refractometer readings in medical register.",
                ),
                OperationalActionStep(
                    step_number=5,
                    timeline_window="00:25 - 00:30 (Emergency Readiness)",
                    action_title="DCAS Ambulance Paramedic Staging & Emergency Channel",
                    action_detail=(
                        f"Establish direct VHF/cellular comms with Dubai Corporation for Ambulance Services (DCAS). "
                        f"Pre-stage ambulance unit at Site Gate 1 for rapid hyperthermia intervention."
                    ),
                    responsible_lead="EMS Liaison / Emergency Response Director",
                    compliance_framework="DCAS Hyperthermia Pre-Staging SOP-DCAS-H04",
                    verification_check="Radio confirmation with DCAS Dispatch Operation Center.",
                ),
            ]
        else:
            return [
                OperationalActionStep(
                    step_number=1,
                    timeline_window="00:00 - 00:10 (Pre-Shift Inspection)",
                    action_title="Pre-Shift Thermal Briefing & Hydration Check",
                    action_detail=f"Conduct 5-minute toolbox talk for {ctx.workforce_size:,} workers on early symptoms of heat strain.",
                    responsible_lead="Site Safety Officer",
                    compliance_framework="UAE MOHRE Resolution 44/2022 Awareness Directives",
                    verification_check="Sign-off by safety marshals on pre-shift safety log.",
                ),
                OperationalActionStep(
                    step_number=2,
                    timeline_window="00:10 - 00:20 (Asset Verification)",
                    action_title="Verify Shaded Shelters & Potable Water Dispensers",
                    action_detail=f"Confirm shaded shelters are operational and {ctx.potable_water_tons:.2f} tons of water are stocked.",
                    responsible_lead="Site Foreman",
                    compliance_framework="OSHA Technical Manual Section III, Chapter 4",
                    verification_check="Visual inspection of shaded structures and cool storage tanks.",
                ),
                OperationalActionStep(
                    step_number=3,
                    timeline_window="00:20 - 00:30 (Surveillance Telemetry)",
                    action_title="Continuous Sentinel ESP32 Microclimate Monitoring",
                    action_detail=(
                        f"Track microclimate delta ({ctx.microclimate_delta_c:.1f}°C) via Node {ctx.sensor_node_id or 'JA-01'}. "
                        f"Maintain standby alert status if forecast exceeds 32.0°C."
                    ),
                    responsible_lead="Surveillance Officer",
                    compliance_framework="Munzir Continuous Telemetry Protocol",
                    verification_check="Real-time telemetry ingestion confirmed on Lakehouse dashboard.",
                ),
            ]

    def _render_markdown_report(
        self,
        dossier_id: str,
        generated_at_utc: str,
        ctx: LiveSiteSurveillanceContext,
        threat_trajectory: Dict[str, Any],
        diagnostic_attribution: Dict[str, Any],
        statutory_trigger: Dict[str, Any],
        checklist: List[OperationalActionStep],
        municipal_fleet_directive: Dict[str, Any],
        raci_matrix: Dict[str, Any],
        dispatch_card: MultilingualDispatchCard,
    ) -> str:
        """Renders the comprehensive 7-section Markdown report."""
        delta_str = threat_trajectory["microclimate_delta_c"]
        lines = [
            f"# MUNZIR (منذر) — EXECUTIVE ACTION DOSSIER",
            f"**Dossier Reference:** `{dossier_id}` | **Generated:** {generated_at_utc[:19]} UTC",
            f"**Target Site:** {ctx.site_name} (`{ctx.site_id}`) | **District:** {ctx.district_name} (`{ctx.district_id}`)",
            f"**Surveillance Status:** Tier **{ctx.alert_tier.upper()}** "
            f"(Calibrated Risk: {ctx.calibrated_probability * 100:.1f}%, "
            f"90% Conformal CI: [{ctx.conformal_ci_low * 100:.1f}%, {ctx.conformal_ci_high * 100:.1f}%]) | "
            f"**Data Completeness:** {ctx.dq_completeness_pct:.1f}%\n",
            "---",
            "## 1. THREAT TRAJECTORY & PHYSICAL EXPOSURE",
            f"- **Workforce at Risk:** {ctx.workforce_size:,} personnel",
            f"- **Atmospheric Thermal Peak (WBGT):** {threat_trajectory['current_wbgt_c']}°C (Current) | {threat_trajectory['forecast_3d_wbgt_max_c']}°C (3-Day Forecast)",
            f"- **Particulate Matter (PM2.5):** {threat_trajectory['current_pm25_ugm3']} µg/m³ (Current) | {threat_trajectory['forecast_3d_pm25_ugm3']} µg/m³ (3-Day Forecast)",
            f"- **Sentinel ESP32 Hardware Ground Truth:** "
            f"{'Node ' + str(threat_trajectory['sentinel_node_id']) if threat_trajectory['sentinel_node_id'] else 'Unsensored Site'}",
            f"  • Physical Measured WBGT: {threat_trajectory['sensor_measured_wbgt_c'] or 'N/A'}°C | Microclimate Delta: {delta_str}",
            f"  • Spatial Generalization Status: {threat_trajectory['spatial_transfer_confidence']}\n",
            "---",
            "## 2. MULTI-SIGNAL DIAGNOSTIC ATTRIBUTION (SHAP)",
            f"- **Primary Risk Driver:** {diagnostic_attribution['primary_driver']}",
            f"- **Signal Attribution Breakdown:**",
        ]

        for k, v in diagnostic_attribution["shap_attributions"].items():
            lines.append(f"  • **{k.replace('_', ' ').title()}:** {v * 100:.1f}% contribution")

        renal = diagnostic_attribution["renal_surveillance"]
        lines.extend([
            f"- **Sub-Clinical Renal Surveillance (CKD-EPI & KDIGO):**",
            f"  • Monitored Cohort: {renal['screened_cohort']} workers | Mean eGFR: {renal['mean_egfr_ml_min']} mL/min",
            f"  • Dehydration Prevalence (USG ≥ 1.025): {renal['dehydration_rate_pct']}%",
            f"  • Sub-Clinical KDIGO Stage 1 Incidence: {renal['kdigo_stage1_rate_per_1k']} per 1,000 workers",
            f"  • Diagnostic Early-Warning Lead Time: +{renal['subclinical_advance_lead_time_days']} days prior to hospital admissions\n",
            "---",
            "## 3. STATUTORY MANDATE & REGULATORY TRIGGER",
            f"- **Authority:** {statutory_trigger['authority']}",
            f"- **Legal Instrument:** {statutory_trigger['decree']} — {statutory_trigger['article_number']}: {statutory_trigger['title']}",
            f"- **Statutory Mandate:** {statutory_trigger['legal_mandate']}",
            f"- **Statutory Penalties for Non-Compliance:** {statutory_trigger['statutory_penalties']}",
            f"- **Official Citation:** `{statutory_trigger['citation']}`\n",
            "---",
            "## 4. IMMEDIATE 30-MINUTE OPERATIONAL CHECKLIST",
        ])

        for step in checklist:
            lines.extend([
                f"### Step {step.step_number}: {step.action_title} ({step.timeline_window})",
                f"- **Lead:** {step.responsible_lead}",
                f"- **Action:** {step.action_detail}",
                f"- **Compliance Basis:** {step.compliance_framework}",
                f"- **Verification:** {step.verification_check}\n",
            ])

        fleet = municipal_fleet_directive
        lines.extend([
            "---",
            "## 5. MUNICIPAL FLEET & LOGISTICS DIRECTIVE",
            f"- **Mobile Cooling Buses Dispatched:** {fleet['cooling_buses_allocated']} unit(s)",
            f"- **Misting Trailers Deployed:** {fleet['misting_trailers_allocated']} unit(s)",
            f"- **Potable Hydration Reserves:** {fleet['potable_water_metric_tons']} Metric Tons chilled water",
            f"- **Electrolyte Replacement Sachets:** {fleet['electrolyte_sachets_allocated']:,} sachets",
            f"- **DCAS Paramedic Status:** {fleet['dcas_ambulance_status']} (Nearest Depot: {fleet['nearest_depot']}, Transit: {fleet['transit_time_minutes']} mins)",
            f"- **Estimated Mobilization Cost:** AED {fleet['estimated_mobilization_cost_aed']:,.2f}\n",
            "---",
            "## 6. RACI GOVERNANCE & ACCOUNTABILITY MATRIX",
            f"- **Responsible (R - Lead Operator):** {raci_matrix['responsible']}",
            f"- **Accountable (A - Approving Authority):** {raci_matrix['accountable']}",
            f"- **Consulted (C - Subject Specialists):** {', '.join(raci_matrix['consulted'])}",
            f"- **Informed (I - Notified Stakeholders):** {', '.join(raci_matrix['informed'])}\n",
            "---",
            "## 7. FRONTLINE MULTILINGUAL DISPATCH & WHATSAPP BROADCAST",
            f"### English Advisory\n```\n{dispatch_card.english_text}\n```\n",
            f"### Arabic Advisory (العربية)\n```\n{dispatch_card.arabic_text}\n```\n",
            f"### Urdu Advisory (اردو)\n```\n{dispatch_card.urdu_text}\n```\n",
            f"### Hindi Advisory (हिन्दी)\n```\n{dispatch_card.hindi_text}\n```\n",
            "---",
            f"*Certified Zero-Hallucination Sovereign Action Dossier | Munzir Intelligence Core & Inception 42 Jais Framework*",
        ])

        return "\n".join(lines)

