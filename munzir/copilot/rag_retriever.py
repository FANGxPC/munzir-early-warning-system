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

from munzir.copilot.context_builder import LiveSiteSurveillanceContext, LiveSurveillanceContextBuilder
from munzir.copilot.statutory_codex import StatutoryArticle, StatutoryCodex


class CopilotIntent(str, Enum):
    """Classified domain of the user's operational or regulatory question."""
    REGULATORY_COMPLIANCE = "regulatory_compliance"
    ALERT_EXPLANATION = "alert_explanation"
    OPERATIONAL_INTERVENTION = "operational_intervention"
    FLEET_LOGISTICS = "fleet_logistics"
    CLINICAL_RENAL = "clinical_renal"
    ACTION_PLAN = "action_plan"
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
        """Formats the retrieved packet into a concise prompt optimized for local LLM inference."""
        ctx = self.live_context
        art = self.statutory_articles[0] if self.statutory_articles else None
        art_mandate = (
            f"{art.instrument} {art.article_number} ({', '.join(art.mandatory_actions)}. Penalties: {art.penalties})"
            if art
            else "UAE MOHRE Ministerial Resolution No. 44 of 2022 (Mandatory Midday Work Ban 12:30 PM - 3:00 PM; fines AED 5,000 - 50,000)"
        )

        if self.intent in (CopilotIntent.GREETING, CopilotIntent.CONVERSATIONAL):
            return (
                f"Active Worksite: {ctx.site_name} ({ctx.site_id}) on {ctx.target_date}. "
                f"Live Thermal Status: Peak WBGT {ctx.current_wbgt_c}°C ({ctx.alert_tier.upper()} Tier, {round(ctx.calibrated_probability * 100, 1)}% risk). "
                f"Workforce: {ctx.workforce_size:,} workers. "
                f"Fleet Readiness: {ctx.cooling_buses_needed} cooling buses, {ctx.misting_trailers_needed} misting trailers, {ctx.potable_water_tons:.1f}t water from {ctx.nearest_depot}. "
                f"Clinical: Mean eGFR {ctx.mean_egfr:.1f} mL/min, dehydration {ctx.dehydration_rate_pct:.1f}%, KDIGO Stage 1: {ctx.kdigo_stage1_rate_per_1k:.1f}/1,000. "
                f"Governing Decree: {art_mandate}."
            )
        if self.intent == CopilotIntent.ACTION_PLAN:
            return (
                f"Master Operational Heat Safety Plan for {ctx.site_name} ({ctx.site_id}) on {ctx.target_date}. "
                f"Peak WBGT: {ctx.current_wbgt_c}°C ({ctx.alert_tier.upper()} Tier, {round(ctx.calibrated_probability * 100, 1)}% risk). "
                f"Workforce: {ctx.workforce_size:,} workers. "
                f"Logistics readiness: {ctx.cooling_buses_needed} cooling buses, {ctx.misting_trailers_needed} misting trailers, "
                f"{ctx.potable_water_tons:.1f} tons potable water from {ctx.nearest_depot} ({ctx.depot_transit_minutes} min transit). "
                f"Statutory Mandate: {art_mandate}."
            )
        if self.intent == CopilotIntent.CLINICAL_EDUCATION:
            return (
                f"Clinical thermal physiology domain: Heat strain vs stroke, hydration guidelines (250 mL chilled water every 15-20 min), "
                f"WBGT index combining ambient, humidity, radiant heat and wind (ISO 7243/7933). "
                f"Active Site State: {ctx.site_name} (WBGT {ctx.current_wbgt_c}°C, eGFR {ctx.mean_egfr:.1f} mL/min, dehydration {ctx.dehydration_rate_pct:.1f}%)."
            )
        if self.intent == CopilotIntent.FIRST_AID:
            return (
                f"Frontline emergency first-aid protocols: immediate shade, active cooling (cold towels, ice packs to neck/armpits/groin), "
                f"oral rehydration salts (ORS) if conscious, elevation of feet 20-30 cm, and Dubai Ambulance DCAS 998 dispatch. "
                f"Active Site Monitored: {ctx.site_name} ({ctx.alert_tier.upper()} Tier, {ctx.workforce_size:,} workers)."
            )
        if self.intent == CopilotIntent.PLATFORM_GUIDANCE:
            return (
                f"Munzir Sovereign Health Early Warning Platform: Sentinel ESP32 IoT hardware twins, Medallion Lakehouse telemetry, "
                f"ISO 7933 PHS thermal strain, KDIGO renal biomarker surveillance, and UAE MOHRE statutory codex. "
                f"Active Site: {ctx.site_name} ({ctx.site_id})."
            )
        if self.intent == CopilotIntent.FOLLOW_UP_ELABORATION:
            return (
                f"Comprehensive thermal, clinical, and regulatory deep-dive for {ctx.site_name} ({ctx.site_id}) on {ctx.target_date}. "
                f"Peak WBGT: {ctx.current_wbgt_c}°C ({ctx.alert_tier.upper()} Tier, probability {round(ctx.calibrated_probability * 100, 1)}%). "
                f"Workforce: {ctx.workforce_size:,} workers. In-situ sensor delta: {ctx.microclimate_delta_c:+.1f}°C. "
                f"Logistics: {ctx.cooling_buses_needed} cooling buses, {ctx.misting_trailers_needed} misting trailers, {ctx.potable_water_tons:.1f}t water from {ctx.nearest_depot}. "
                f"Clinical: eGFR {ctx.mean_egfr:.1f} mL/min, dehydration {ctx.dehydration_rate_pct:.1f}%, KDIGO Stage 1: {ctx.kdigo_stage1_rate_per_1k:.1f}/1,000. "
                f"Statutory Mandate: {art_mandate}."
            )

        base = (
            f"Site: {ctx.site_name} ({ctx.site_id}) on {ctx.target_date}. "
            f"Peak WBGT: {ctx.current_wbgt_c}°C. Alert Tier: {ctx.alert_tier.upper()} ({round(ctx.calibrated_probability * 100, 1)}% probability). "
            f"3-Day WBGT Forecast Max: {ctx.forecast_3d_wbgt_max_c}°C. Workforce: {ctx.workforce_size:,} workers. "
            f"Primary Driver: {ctx.primary_signal_driver} (environmental SHAP={ctx.shap_attributions.get('environmental', 1.15)}, clinical SHAP={ctx.shap_attributions.get('clinical', 2.10)}). "
            f"Fleet: {ctx.cooling_buses_needed} cooling buses, {ctx.misting_trailers_needed} misting trailers, {ctx.potable_water_tons:.1f}t water from {ctx.nearest_depot} ({ctx.depot_transit_minutes} min transit). "
            f"Renal: {ctx.screened_workers} workers screened, mean eGFR {ctx.mean_egfr:.1f} mL/min, dehydration {ctx.dehydration_rate_pct:.1f}%, KDIGO Stage 1: {ctx.kdigo_stage1_rate_per_1k:.1f}/1,000 (+{ctx.renal_advance_lead_time_days:.1f} days lead window). "
            f"Statutory Mandate: {art_mandate}."
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
        greeting_words = ["hello", "hi", "hey", "salam", "salaam", "marhaba", "welcome", "greetings", "good morning", "good afternoon", "good evening", "ahlan", "good day", "morning", "evening"]
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in greeting_words):
            # Guard against operational queries that might happen to start with greeting
            if not any(op in q for op in ["bus", "fleet", "misting", "renal", "kidney", "egfr", "resolution", "decree", "fine", "penalty", "shap"]):
                return CopilotIntent.GREETING

        # 2. Conversational Inquiries, Gratitude, Slang & Humor
        joke_phrases = ["joke", "funny", "laugh", "humor", "tell me a joke", "make me laugh", "say a joke", "crack a joke", "نكتة", "مزحة"]
        if any(w in q for w in joke_phrases):
            return CopilotIntent.CONVERSATIONAL

        # Hallucination & Factuality Inquiries
        if re.search(r"hal+ucinat", q) or any(w in q for w in ["are you lying", "can i trust you", "is this real", "is this accurate", "are you accurate", "are you real", "are you fake"]):
            return CopilotIntent.CONVERSATIONAL

        # Slang & Casual Greetings
        slang_phrases = ["yo", "yo dude", "dude", "sup", "what's up", "whats up", "hey man", "hey dude", "howdy", "hiya", "peace"]
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in slang_phrases):
            if not any(op in q for op in ["bus", "fleet", "misting", "renal", "kidney", "egfr", "resolution", "decree", "fine", "penalty", "shap"]):
                return CopilotIntent.CONVERSATIONAL

        site_keywords = ["site", "jebel", "ali", "quoz", "warsan", "south", "qusais", "worker", "status", "situation", "heat", "port", "safe", "terminal"]
        if re.search(r"\b(how\s*(are\s*you|are\s*u|r\s*u|u|do\s*you\s*do|is\s*it\s*going|u\s*doing|you\s*doing))\b", q):
            if not any(k in q for k in site_keywords):
                return CopilotIntent.CONVERSATIONAL

        conv_phrases = [
            "who are you", "what are you", "what can you do", "what do you do", "what do u do",
            "what is your main work", "what is your work", "what is your job", "what is your role",
            "what is your purpose", "what are your tasks", "what are your main tasks",
            "what does this bot do", "what does the copilot do", "what does munzir do", "what is munzir",
            "tell me about munzir", "how are you", "how are you doing",
            "how do you do", "how u do", "how are u", "how r u", "hows it going", "how's it going",
            "tell me about yourself", "who made you", "who created you", "thank you", "thanks",
            "appreciate it", "great job", "nice", "cool", "can you speak arabic", "can you speak english",
            "how do you work", "introduce yourself", "help", "how can you help", "how can you assist",
            "what can i ask", "what can i ask you", "capabilities", "your capabilities",
            "poem", "poetry", "write a poem", "story", "tell me a story"
        ]
        conv_ar_phrases = [
            "من أنت", "ماذا تفعل", "ما هو عملك", "ما هو عملك الرئيسي", "ما هي مهامك", "ما هي وظيفتك",
            "كيف حالك", "شكر", "شكرا", "شكراً", "يعطيك العافية", "من صنعك", "ما هي منصة منذر",
            "ما هي مميزاتك", "مساعدة", "كيف تساعدني", "هل تهلوس", "هل أنت حقيقي", "قصيدة"
        ]
        if any(w in q for w in conv_ar_phrases):
            return CopilotIntent.CONVERSATIONAL

        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in conv_phrases):
            if not any(op in q for op in ["bus", "fleet", "misting", "renal", "kidney", "egfr", "resolution", "decree", "fine", "penalty", "shap", "site", "jebel", "ali", "quoz", "status"]):
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
            "command palette", "change region", "safe harbor shield", "what models", "how does munzir work",
            "how does munzir work", "explain features", "what can this app do"
        ]
        if any(w in q for w in platform_phrases):
            return CopilotIntent.PLATFORM_GUIDANCE

        # 6. Operational Planning & Master Heat Safety Plans
        plan_phrases = [
            "plan", "make a plan", "create a plan", "operational plan", "action plan",
            "contingency plan", "plan for tomorrow", "safety plan", "intervention plan",
            "how to plan", "heat action plan", "work plan", "shift plan", "planning",
            "master plan", "emergency plan", "risk plan", "give me a plan"
        ]
        if any(re.search(r"\b" + re.escape(w) + r"\b", q) for w in plan_phrases):
            return CopilotIntent.ACTION_PLAN

        # 7. Statutory Decrees & Legal Mandates
        if any(w in q for w in ["law", "decree", "resolution", "resolution 44", "mohre", "legal", "fine", "penalty", "illegal", "midday", "ban"]):
            return CopilotIntent.REGULATORY_COMPLIANCE

        # 8. Site Alert Drivers, Thermal Risk & SHAP Attributions
        if any(w in q for w in ["why", "cause", "driver", "explain jebel ali", "explain risk", "attribution", "reason", "shap", "risk", "thermal", "wbgt", "temperature", "heat stress", "hazard", "threat", "anomaly"]):
            return CopilotIntent.ALERT_EXPLANATION

        # 9. Municipal Cooling Fleet Logistics
        if any(w in q for w in ["bus", "fleet", "misting", "water tanker", "dcas", "depot", "transport", "staging"]):
            return CopilotIntent.FLEET_LOGISTICS

        # 10. Renal Biomarkers & AKI Screening
        if any(w in q for w in ["renal", "kidney", "egfr", "kdigo", "dehydration rate", "urine", "biomarker"]):
            return CopilotIntent.CLINICAL_RENAL

        # 11. Operational Action Checklist
        op_phrases = ["action", "checklist", "what should", "intervention", "protocol", "raci", "next step", "next steps", "directives", "what to do", "what must be done", "operational checklist"]
        if any(w in q for w in op_phrases) or re.search(r"\b(what\s+(should|must|can)\s+(i|we)\s+do|what\s+actions?|do\s+for\s+outdoor)\b", q):
            return CopilotIntent.OPERATIONAL_INTERVENTION

        # 12. Explicit Site Surveillance Overview & Status Requests
        overview_phrases = [
            "overview", "briefing", "site briefing", "surveillance overview",
            "site overview", "status briefing", "site status", "surveillance status",
            "status of site", "current status", "daily briefing", "situation report", "sitrep",
            "situation", "status", "update", "how is", "how are things", "how things look",
            "what is happening", "whats happening", "what is going on", "whats going on",
            "condition", "conditions", "tell me about", "whatsa status", "whats status",
            "what is status", "what is the status", "whats the status", "worker safety", "safe",
            "workers safe", "current state"
        ]
        if any(w in q for w in overview_phrases) or re.search(r"\b(what('?s|sa)?\s+(the\s+)?(status|situation|condition|state|sitrep))\b", q):
            return CopilotIntent.GENERAL_OVERVIEW

        # Check if query references any specific site directly for situational update
        site_names = ["jebel ali", "al quoz", "warsan", "dubai south", "al qusais", "site-ja-01", "site-aq-01", "site-ds-01", "port terminal"]
        if any(s in q for s in site_names):
            return CopilotIntent.GENERAL_OVERVIEW

        # 13. Default: Conversational Assistant for any open-ended normal chat
        return CopilotIntent.CONVERSATIONAL

    def retrieve(
        self,
        query: str,
        site_id: str = "SITE-JA-01",
        target_date: str = "2025-08-20",
    ) -> RetrievedContextPacket:
        """Performs tri-vector retrieval across live state and statutory codex."""
        intent = self.classify_intent(query)

        # Resolve target site from query if explicitly mentioned
        q_lower = query.lower()
        if "jebel ali" in q_lower or "ja-01" in q_lower or "port terminal" in q_lower:
            resolved_site_id = "SITE-JA-01"
        elif "al quoz" in q_lower or "aq-01" in q_lower or "aq-02" in q_lower or "quoz" in q_lower:
            resolved_site_id = "SITE-AQ-01"
        elif "dubai south" in q_lower or "ds-01" in q_lower or "ds-04" in q_lower:
            resolved_site_id = "SITE-DS-01"
        elif "warsan" in q_lower or "wn-03" in q_lower:
            resolved_site_id = "SITE-WN-03"
        elif "creek" in q_lower or "cr-03" in q_lower:
            resolved_site_id = "SITE-CR-03"
        elif "al qusais" in q_lower or "qs-05" in q_lower:
            resolved_site_id = "SITE-QS-05"
        else:
            resolved_site_id = site_id or "SITE-JA-01"

        live_ctx = self.context_builder.build_site_context(site_id=resolved_site_id, target_date=target_date)

        # Retrieve relevant statutory articles based on query + intent
        augmented_query = f"{query} {intent.value}"
        articles = self.codex.search_codex(augmented_query, limit=2)

        # Grounding citations only attached for operational / decree inquiries
        if intent in (CopilotIntent.GREETING, CopilotIntent.CONVERSATIONAL):
            citations = []
        else:
            citations = [art.citation for art in articles if art.citation]
            citations.append(f"Munzir Lakehouse Telemetry ({live_ctx.site_name}, {target_date})")

        return RetrievedContextPacket(
            intent=intent,
            user_query=query,
            target_site_id=resolved_site_id,
            target_site_name=live_ctx.site_name,
            live_context=live_ctx,
            statutory_articles=articles,
            citations=citations,
            retrieval_confidence=0.98,
        )

