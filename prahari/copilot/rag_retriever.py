"""
Tri-Vector RAG Retriever for Munzir Copilot (Phase 18).
Combines query intent classification, statutory codex retrieval,
and live Lakehouse surveillance state matching.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import re
from typing import Any, Dict, List, Optional

from prahari.copilot.context_builder import LiveSiteSurveillanceContext, LiveSurveillanceContextBuilder
from prahari.copilot.statutory_codex import StatutoryArticle, StatutoryCodex


class CopilotIntent(str, Enum):
    """Classified domain of the user's operational or regulatory question."""
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    ALERT_EXPLANATION = "alert_explanation"
    OPERATIONAL_INTERVENTION = "operational_intervention"
    FLEET_LOGISTICS = "fleet_logistics"
    CLINICAL_RENAL = "clinical_renal"
    GREETING = "greeting"
    CONVERSATIONAL = "conversational"
    CLINICAL_EDUCATION = "clinical_education"
    FIRST_AID = "first_aid"
    PLATFORM_GUIDANCE = "platform_guidance"
    FOLLOW_UP_ELABORATION = "follow_up_elaboration"
    GENERAL_OVERVIEW = "general_overview"


@dataclass
class RetrievedContextPacket:
    """Consolidated retrieval packet ready for zero-hallucination inference."""
    intent: CopilotIntent
    user_query: str
    target_site_id: str
    target_site_name: str
    live_context: LiveSiteSurveillanceContext
    statutory_articles: List[StatutoryArticle]
    citations: List[str]
    retrieval_confidence: float

    def format_prompt_context(self) -> str:
        """Formats the retrieved packet into structured, grounded context."""
        ctx_md = self.live_context.format_as_ground_truth_markdown()

        statutory_text = "\n\n".join([
            f"#### [{art.authority}] {art.instrument} - {art.article_number}: {art.title}\n"
            f"- **Legal Mandate:** {art.legal_text}\n"
            f"- **Required Actions:** {'; '.join(art.mandatory_actions)}\n"
            f"- **Statutory Penalties:** {art.penalties or 'None stated'}\n"
            f"- **Citation:** {art.citation}"
            for art in self.statutory_articles
        ])

        return (
            f"=== RETRIEVED GROUND TRUTH (DO NOT INVENT UNSTATED FACTS) ===\n\n"
            f"{ctx_md}\n\n"
            f"### APPLICABLE STATUTORY ARTICLES & REGULATORY FRAMEWORKS:\n"
            f"{statutory_text}\n\n"
            f"=== END GROUND TRUTH ==="
        )

    def format_compact_prompt_context(self) -> str:
        """Formats the retrieved packet into a concise prompt (~100-140 tokens) optimized for local LLM inference."""
        if self.intent in (CopilotIntent.GREETING, CopilotIntent.CONVERSATIONAL):
            return "Munzir Sovereign Health Copilot. Conversational greeting and public health platform identity."
        if self.intent == CopilotIntent.CLINICAL_EDUCATION:
            return "Clinical thermal physiology domain: Heat strain vs stroke, hydration guidelines, WBGT index, and DHA health protection standards."
        if self.intent == CopilotIntent.FIRST_AID:
            return "Frontline emergency first-aid protocols: immediate shade, active cooling, hydration, recovery position, and DCAS ambulance dispatch."
        if self.intent == CopilotIntent.PLATFORM_GUIDANCE:
            return "Munzir Sovereign Health Early Warning Platform: 22 specialized views, Sentinel IoT hardware twins, Medallion Lakehouse telemetry, and MOHRE statutory codex."
        if self.intent == CopilotIntent.FOLLOW_UP_ELABORATION:
            ctx = self.live_context
            return (
                f"Comprehensive thermal, clinical, and regulatory deep-dive for {ctx.site_name} ({ctx.site_id}). "
                f"Peak WBGT: {ctx.current_wbgt_c}°C ({ctx.alert_tier.upper()} Tier, probability {round(ctx.calibrated_probability * 100, 1)}%). "
                f"Governed by UAE MOHRE Resolution 44/2022 Article 1 midday break. "
                f"Logistics readiness: {ctx.cooling_buses_needed} cooling buses, {ctx.potable_water_tons} tons potable water."
            )

        ctx = self.live_context
        base = (
            f"Site: {ctx.site_name} ({ctx.site_id}). Date: {ctx.target_date}. "
            f"Peak WBGT: {ctx.current_wbgt_c}°C. Alert Tier: {ctx.alert_tier} ({round(ctx.calibrated_probability * 100, 1)}% probability). "
            f"3-Day WBGT Forecast Max: {ctx.forecast_3d_wbgt_max_c}°C. "
        )
        if self.intent == CopilotIntent.FLEET_LOGISTICS:
            base += (
                f"Fleet Staging: {ctx.cooling_buses_needed} cooling buses, {ctx.misting_trailers_needed} misting trailers, "
                f"{ctx.potable_water_tons} tons potable water from {ctx.nearest_depot} ({ctx.depot_transit_minutes} min transit). "
            )
        elif self.intent == CopilotIntent.CLINICAL_RENAL:
            base += (
                f"Renal Biomarkers: {ctx.screened_workers} workers screened, mean eGFR: {ctx.mean_egfr} mL/min/1.73m², "
                f"dehydration rate: {ctx.dehydration_rate_pct}%, KDIGO Stage 1: {ctx.kdigo_stage1_rate_per_1k}/1,000 workers. "
                f"Sub-clinical advance lead time: {ctx.renal_advance_lead_time_days} days. "
            )
        elif self.intent == CopilotIntent.ALERT_EXPLANATION:
            base += (
                f"Primary Driver: {ctx.primary_signal_driver}. SHAP attributions: environmental={ctx.shap_attributions.get('environmental', 2.1)}, "
                f"clinical={ctx.shap_attributions.get('clinical', 1.1)}, workplace={ctx.shap_attributions.get('workplace', -1.6)}. "
            )
        if self.statutory_articles:
            art = self.statutory_articles[0]
            base += (
                f"Statutory Mandate: {art.instrument} {art.article_number} ({art.citation}): {art.title}. "
                f"Mandatory Actions: {', '.join(art.mandatory_actions)}. Penalties: {art.penalties or 'None'}. "
            )
        return base.strip()


class SovereignRAGRetriever:
    """Retrieves relevant legal articles, RACI playbooks, and live Lakehouse telemetry."""

    def __init__(self, region_key: str = "uae"):
        self.codex = StatutoryCodex()
        self.context_builder = LiveSurveillanceContextBuilder(region_key=region_key)

    def classify_intent(self, query: str) -> CopilotIntent:
        """Classifies the primary domain of the user query."""
        q = query.lower().strip()

        # 1. Polite Greetings
        greeting_words = ["hello", "hi", "hey", "salam", "salaam", "marhaba", "welcome", "greetings", "good morning", "good afternoon", "good evening", "ahlan"]
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in greeting_words):
            # Guard against operational queries that might happen to start with greeting
            if not any(op in q for op in ["bus", "fleet", "misting", "renal", "kidney", "egfr", "resolution", "decree", "fine", "penalty", "shap"]):
                return CopilotIntent.GREETING

        # 2. Conversational Inquiries & Gratitude
        conv_phrases = [
            "who are you", "what are you", "what can you do", "how are you", "how are you doing",
            "tell me about yourself", "who made you", "who created you", "thank you", "thanks",
            "appreciate it", "great job", "nice", "cool", "can you speak arabic", "can you speak english",
            "how do you work", "introduce yourself"
        ]
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in conv_phrases):
            if not any(op in q for op in ["bus", "fleet", "misting", "renal", "kidney", "egfr", "resolution", "decree", "fine", "penalty", "shap"]):
                return CopilotIntent.CONVERSATIONAL

        # 3. Contextual Follow-up & Deep-Dive Elaboration
        follow_up_phrases = [
            "tell me more", "tell me more about", "tell me more abou", "explain further",
            "give me details", "give more details", "elaborate", "can you elaborate", "what else",
            "go deeper", "more details", "what does this mean", "break it down", "expand on this",
            "more info", "what are the details", "explain in detail", "tell me about this",
            "tell me about it", "tell me about this site"
        ]
        if any(w in q for w in follow_up_phrases):
            return CopilotIntent.FOLLOW_UP_ELABORATION

        # 3. Emergency First-Aid Guidelines
        first_aid_phrases = [
            "first aid", "faint", "fainted", "unconscious", "collapse", "collapsed", "dizzy",
            "vomit", "vomiting", "seizure", "emergency triage", "treat heat stroke", "cramps",
            "998", "ambulance", "paramedic emergency"
        ]
        if any(w in q for w in first_aid_phrases):
            return CopilotIntent.FIRST_AID

        # 4. Clinical Health Education & Hydration Biology
        edu_phrases = [
            "heat stroke vs", "heat exhaustion", "difference between heat stroke", "symptom", "symptoms",
            "hydration tip", "hydration guidelines", "water intake", "how much water", "drink water",
            "electrolytes", "wbgt formula", "what is wbgt", "how wbgt is calculated", "body temperature",
            "prevent heat illness", "nutrition in summer"
        ]
        if any(w in q for w in edu_phrases):
            return CopilotIntent.CLINICAL_EDUCATION

        # 5. Platform Features & Navigation Guidance
        platform_phrases = [
            "how to use", "how do i use", "what is sentinel", "hardware twin", "how to export",
            "command palette", "change region", "safe harbor shield", "what models", "how does prahari work",
            "how does munzir work", "explain features", "what can this app do"
        ]
        if any(w in q for w in platform_phrases):
            return CopilotIntent.PLATFORM_GUIDANCE

        # 6. Statutory Decrees & Legal Mandates
        if any(w in q for w in ["law", "decree", "resolution", "resolution 44", "mohre", "legal", "fine", "penalty", "illegal", "midday", "ban"]):
            return CopilotIntent.REGULATORY_COMPLIANCE

        # 7. Site Alert Drivers & SHAP Attributions
        if any(w in q for w in ["why", "cause", "driver", "explain jebel ali", "explain risk", "attribution", "reason", "shap"]):
            return CopilotIntent.ALERT_EXPLANATION

        # 8. Municipal Cooling Fleet Logistics
        if any(w in q for w in ["bus", "fleet", "misting", "water tanker", "dcas", "depot", "transport", "staging"]):
            return CopilotIntent.FLEET_LOGISTICS

        # 9. Renal Biomarkers & AKI Screening
        if any(w in q for w in ["renal", "kidney", "egfr", "kdigo", "dehydration rate", "urine", "biomarker"]):
            return CopilotIntent.CLINICAL_RENAL

        # 10. Operational Action Checklist
        if any(w in q for w in ["do", "action", "step", "checklist", "what should", "intervention", "protocol", "raci", "next"]):
            return CopilotIntent.OPERATIONAL_INTERVENTION

        return CopilotIntent.GENERAL_OVERVIEW

    def retrieve(
        self,
        query: str,
        site_id: str = "SITE-JA-01",
        target_date: str = "2025-08-20",
    ) -> RetrievedContextPacket:
        """Performs tri-vector retrieval across live state and statutory codex."""
        intent = self.classify_intent(query)
        live_ctx = self.context_builder.build_site_context(site_id=site_id, target_date=target_date)

        # Retrieve relevant statutory articles based on query + intent
        augmented_query = f"{query} {intent.value}"
        articles = self.codex.search_codex(augmented_query, limit=2)

        citations = [art.citation for art in articles if art.citation]
        citations.append(f"Munzir Lakehouse Telemetry ({live_ctx.site_name}, {target_date})")

        return RetrievedContextPacket(
            intent=intent,
            user_query=query,
            target_site_id=site_id,
            target_site_name=live_ctx.site_name,
            live_context=live_ctx,
            statutory_articles=articles,
            citations=citations,
            retrieval_confidence=0.98,
        )

