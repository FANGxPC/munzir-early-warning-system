"""
Comprehensive Unit & Integration Test Suite for Sovereign RAG Copilot & Executive Action Dossier (Phase 18).
Tests statutory codex integrity, real Lakehouse context aggregation, fenced zero-hallucination verification,
7-section dossier generation, bilingual chat agent, and REST API endpoints.
"""

import pytest
from fastapi.testclient import TestClient

from prahari.api.app import app
from prahari.copilot.chat_agent import SovereignCopilotAgent
from prahari.copilot.context_builder import LiveSiteSurveillanceContext, LiveSurveillanceContextBuilder
from prahari.copilot.dossier_generator import ExecutiveActionDossier, ExecutiveDossierGenerator
from prahari.copilot.fenced_rag_validator import FencedRAGValidator
from prahari.copilot.rag_retriever import CopilotIntent, SovereignRAGRetriever
from prahari.copilot.statutory_codex import StatutoryArticle, StatutoryCodex


class TestStatutoryCodex:
    """Tests official legal and clinical knowledge base."""

    def test_codex_articles_count_and_provenance(self):
        codex = StatutoryCodex()
        assert len(codex.articles) >= 6
        jurisdictions = {art.jurisdiction for art in codex.articles}
        assert any("United Arab Emirates" in j for j in jurisdictions)
        assert any("United States" in j for j in jurisdictions)

    def test_uae_resolution_44_2022_articles(self):
        codex = StatutoryCodex()
        res44_arts = [a for a in codex.articles if "Resolution No. 44 of 2022" in a.instrument]
        assert len(res44_arts) >= 3

        # Midday work ban article
        art1 = next(a for a in res44_arts if a.article_number == "Article 1")
        assert "12:30 PM to 3:00 PM" in art1.legal_text
        assert "15 June to 15 September" in art1.legal_text
        assert "5,000" in (art1.penalties or "")
        assert "50,000" in (art1.penalties or "")

    def test_codex_search_relevance(self):
        codex = StatutoryCodex()
        results = codex.search_codex("midday summer fine penalty", limit=2)
        assert len(results) > 0
        assert "Article 1" in results[0].article_number or "Article 3" in results[0].article_number

    def test_statutory_article_to_dict(self):
        art = StatutoryArticle(
            jurisdiction="UAE",
            authority="MOHRE",
            instrument="Resolution 44",
            article_number="Art 1",
            title="Ban",
            legal_text="No outdoor work",
            mandatory_actions=["Halt work"],
            applicability="All sites",
            penalties="AED 5,000",
            citation="UAE MOHRE 44/2022",
        )
        d = art.to_dict()
        assert d["article_number"] == "Art 1"
        assert d["penalties"] == "AED 5,000"


class TestContextBuilder:
    """Tests aggregation of real multi-layer Lakehouse ground truth."""

    def test_build_site_context_structure(self):
        builder = LiveSurveillanceContextBuilder(region_key="uae")
        ctx = builder.build_site_context(site_id="SITE-JA-01", target_date="2025-08-20")

        assert isinstance(ctx, LiveSiteSurveillanceContext)
        assert ctx.site_id == "SITE-JA-01"
        assert ctx.workforce_size > 0
        assert ctx.current_wbgt_c > 0.0
        assert ctx.current_pm25_ugm3 > 0.0
        assert ctx.alert_tier in ("Watch", "Warning", "Alert")
        assert 0.0 <= ctx.calibrated_probability <= 1.0

        # Hardware Sentinel sensor verification
        assert ctx.has_sensor is True
        assert ctx.sensor_node_id == "SENT-001"
        assert ctx.microclimate_delta_c is not None

        # Renal surveillance
        assert ctx.screened_workers > 0
        assert ctx.mean_egfr > 0.0
        assert ctx.renal_advance_lead_time_days > 0.0

        # Municipal dispatch
        assert ctx.cooling_buses_needed >= 0
        assert ctx.potable_water_tons >= 0.0
        assert len(ctx.nearest_depot) > 0

    def test_format_as_ground_truth_markdown(self):
        builder = LiveSurveillanceContextBuilder(region_key="uae")
        ctx = builder.build_site_context(site_id="SITE-JA-01", target_date="2025-08-20")
        md = ctx.format_as_ground_truth_markdown()

        assert "LIVE SURVEILLANCE GROUND TRUTH" in md
        assert "SITE-JA-01" in md
        assert f"{ctx.current_wbgt_c:.1f}°C" in md
        assert "Municipal Cooling Fleet" in md


class TestFencedRAGValidator:
    """Tests zero-hallucination validation gate."""

    def test_reject_invented_numbers(self):
        builder = LiveSurveillanceContextBuilder(region_key="uae")
        ctx = builder.build_site_context(site_id="SITE-JA-01", target_date="2025-08-20")
        codex = StatutoryCodex()
        validator = FencedRAGValidator()

        # Text containing hallucinated numbers not present anywhere in context or legal codex
        hallucinated_text = (
            "We detected an unprecedented risk of 99.78% at the site. "
            "Ambient thermal index breached 58.74°C. "
            "The employer was issued a fine of AED 948,221 under Article 99."
        )
        is_valid, unverified = validator.verify_text(hallucinated_text, ctx, codex.articles)
        assert is_valid is False
        assert len(unverified) > 0

    def test_accept_grounded_text(self):
        builder = LiveSurveillanceContextBuilder(region_key="uae")
        ctx = builder.build_site_context(site_id="SITE-JA-01", target_date="2025-08-20")
        codex = StatutoryCodex()
        validator = FencedRAGValidator()

        # Text using only verified numbers from context and Resolution 44
        grounded_text = (
            f"Under Ministerial Resolution No. 44 of 2022 Article 1, "
            f"peak WBGT reached {ctx.current_wbgt_c:.1f}°C. "
            f"Mandatory 15-minute rest periods apply, with potential fines of AED 5,000 per worker."
        )
        is_valid, unverified = validator.verify_text(grounded_text, ctx, codex.articles)
        assert is_valid is True
        assert len(unverified) == 0


class TestSovereignRAGRetriever:
    """Tests tri-vector query classification and context retrieval."""

    def test_query_intent_classification(self):
        retriever = SovereignRAGRetriever(region_key="uae")
        assert retriever.classify_intent("What is the legal fine under Resolution 44?") == CopilotIntent.REGULATORY_COMPLIANCE
        assert retriever.classify_intent("Why did this alert trigger? Explain SHAP drivers") == CopilotIntent.ALERT_EXPLANATION
        assert retriever.classify_intent("How many cooling buses and misting trailers are needed?") == CopilotIntent.FLEET_LOGISTICS
        assert retriever.classify_intent("What are the eGFR and KDIGO renal biomarker rates?") == CopilotIntent.CLINICAL_RENAL
        assert retriever.classify_intent("What 30-minute operational actions should I take?") == CopilotIntent.OPERATIONAL_INTERVENTION
        assert retriever.classify_intent("hello") == CopilotIntent.GREETING
        assert retriever.classify_intent("who are you?") == CopilotIntent.CONVERSATIONAL
        assert retriever.classify_intent("what is heat stroke vs heat exhaustion?") == CopilotIntent.CLINICAL_EDUCATION
        assert retriever.classify_intent("worker fainted, need first aid") == CopilotIntent.FIRST_AID
        assert retriever.classify_intent("how do I use the sentinel hardware twin?") == CopilotIntent.PLATFORM_GUIDANCE

    def test_retrieval_packet_assembly(self):
        retriever = SovereignRAGRetriever(region_key="uae")
        packet = retriever.retrieve("What should I do right now?", site_id="SITE-JA-01")

        assert packet.intent == CopilotIntent.OPERATIONAL_INTERVENTION
        assert packet.live_context.site_id == "SITE-JA-01"
        assert len(packet.statutory_articles) > 0
        assert len(packet.citations) > 0
        prompt_ctx = packet.format_prompt_context()
        assert "RETRIEVED GROUND TRUTH" in prompt_ctx


class TestExecutiveDossierGenerator:
    """Tests comprehensive 7-section Action Dossier generation."""

    def test_generate_dossier_all_sections(self):
        generator = ExecutiveDossierGenerator(region_key="uae")
        dossier = generator.generate_dossier(site_id="SITE-JA-01", target_date="2025-08-20")

        assert isinstance(dossier, ExecutiveActionDossier)
        assert dossier.dossier_id.startswith("DOSSIER-SITE-JA-01")
        assert dossier.site_id == "SITE-JA-01"

        # Section 1: Threat Trajectory
        assert "current_wbgt_c" in dossier.threat_trajectory
        assert "microclimate_delta_c" in dossier.threat_trajectory

        # Section 2: Multi-Signal Diagnostic Attribution
        assert "primary_driver" in dossier.diagnostic_attribution
        assert "shap_attributions" in dossier.diagnostic_attribution
        assert "renal_surveillance" in dossier.diagnostic_attribution

        # Section 3: Statutory Trigger
        assert "Resolution No. 44 of 2022" in dossier.statutory_trigger["decree"]
        assert "legal_mandate" in dossier.statutory_trigger

        # Section 4: Immediate 30-Minute Operational Checklist
        assert len(dossier.operational_checklist) >= 3
        first_step = dossier.operational_checklist[0]
        assert first_step["step_number"] == 1
        assert "responsible_lead" in first_step

        # Section 5: Municipal Fleet Directive
        assert "cooling_buses_allocated" in dossier.municipal_fleet_directive
        assert "potable_water_metric_tons" in dossier.municipal_fleet_directive

        # Section 6: RACI Matrix
        assert "responsible" in dossier.raci_matrix
        assert "accountable" in dossier.raci_matrix

        # Section 7: Frontline WhatsApp Preview
        assert "arabic_text" in dossier.dispatch_preview
        assert "english_text" in dossier.dispatch_preview
        assert "urdu_text" in dossier.dispatch_preview
        assert "hindi_text" in dossier.dispatch_preview

        # Markdown Report
        assert len(dossier.markdown_report) > 1000
        assert "# MUNZIR (منذر) — EXECUTIVE ACTION DOSSIER" in dossier.markdown_report


class TestSovereignCopilotAgent:
    """Tests bilingual conversational chat agent and truth grounding."""

    def test_agent_chat_operational_query(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("What should I do right now for outdoor workers?", site_id="SITE-JA-01")

        assert res.query == "What should I do right now for outdoor workers?"
        assert res.intent == "operational_intervention"
        assert len(res.response_text) > 40
        assert len(res.arabic_translation) > 20
        assert res.passed_fenced_gate is True
        assert "100% Grounded" in res.grounding_badge
        assert len(res.citations) > 0

    def test_agent_chat_regulatory_query(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("What are the legal fines under Resolution 44?", site_id="SITE-JA-01")

        assert res.intent == "regulatory_compliance"
        assert any(term in res.response_text for term in ["Resolution", "44", "القرار", "MOHRE"])
        assert res.passed_fenced_gate is True

    def test_agent_chat_conversational_greeting(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("hello", site_id="SITE-JA-01")

        assert res.intent == "greeting"
        assert len(res.response_text) >= 10
        assert res.passed_fenced_gate is True
        # Must not inject a false emergency site shutdown for a simple greeting
        assert "Emergency Tier" not in res.response_text

    def test_agent_chat_action_plan(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("make a plan for tomorrow", site_id="SITE-JA-01")

        assert res.intent == "action_plan"
        assert res.passed_fenced_gate is True
        assert len(res.response_text) > 30
        assert any(term in res.response_text.lower() for term in ["plan", "protocol", "hour", "break", "rest", "water", "shift", "resolution", "44", "worker", "heat", "phase"])

    def test_agent_chat_conversational_questions(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res_who = agent.chat("who are you", site_id="SITE-JA-01")
        assert res_who.intent == "conversational"
        assert any(term in res_who.response_text.lower() for term in ["munzir", "ai", "assistant", "help", "support"])
        assert res_who.passed_fenced_gate is True

        res_thanks = agent.chat("thank you so much", site_id="SITE-JA-01")
        assert res_thanks.intent == "conversational"
        assert any(term in res_thanks.response_text.lower() for term in ["welcome", "help", "thank", "pleasure", "assist"])
        assert res_thanks.passed_fenced_gate is True

    def test_agent_chat_casual_inquiry_and_humor(self):
        agent = SovereignCopilotAgent(region_key="uae")

        # 1. Casual 'how u do' should NOT trigger 30-min operational emergency directive
        res_how = agent.chat("how u do", site_id="SITE-JA-01")
        assert res_how.intent == "conversational"
        assert len(res_how.response_text) > 10
        assert "13 mobile cooling buses" not in res_how.response_text
        assert res_how.passed_fenced_gate is True

        # 2. Slang 'yo dude' should respond naturally as a friendly chatbot
        res_yo = agent.chat("yo dude", site_id="SITE-JA-01")
        assert res_yo.intent == "conversational"
        assert len(res_yo.response_text) > 5
        assert "Munzir Surveillance Briefing" not in res_yo.response_text
        assert res_yo.citations == []
        assert res_yo.passed_fenced_gate is True

        # 3. Hallucination query 'are you halllucinating ?' should respond naturally
        res_hal = agent.chat("are you halllucinating ?", site_id="SITE-JA-01")
        assert res_hal.intent == "conversational"
        assert len(res_hal.response_text) > 10
        assert "Munzir Surveillance Briefing" not in res_hal.response_text
        assert res_hal.citations == []
        assert res_hal.passed_fenced_gate is True

        # 4. 'tell me a joke' should NOT fall back to raw surveillance statistics
        res_joke = agent.chat("tell me a joke", site_id="SITE-JA-01")
        assert res_joke.intent == "conversational"
        assert len(res_joke.response_text) > 10
        assert "Munzir Surveillance Briefing" not in res_joke.response_text
        # Enforce zero emojis in responses
        assert not any(ord(ch) > 0x1F000 for ch in res_joke.response_text)
        assert res_joke.passed_fenced_gate is True

        # 5. Explicit site briefing query should route to general_overview with surveillance stats
        res_brief = agent.chat("give me the site briefing", site_id="SITE-JA-01")
        assert res_brief.intent == "general_overview"
        assert any(t in res_brief.response_text.lower() for t in ["briefing", "surveillance", "jebel ali", "wbgt", "alert", "port"])
        assert len(res_brief.citations) > 0

    def test_agent_chat_main_work_and_capabilities(self):
        agent = SovereignCopilotAgent(region_key="uae")

        # 'what is your main work' explains agent's core responsibilities
        res_work = agent.chat("what is your main work", site_id="SITE-JA-01")
        assert res_work.intent == "conversational"
        assert any(t in res_work.response_text.lower() for t in ["munzir", "health", "decision support", "public", "data", "guidance", "assist", "ai"])
        assert res_work.passed_fenced_gate is True

        res_do = agent.chat("what do you do", site_id="SITE-JA-01")
        assert res_do.intent == "conversational"
        assert any(t in res_do.response_text.lower() for t in ["munzir", "health", "decision support", "assist", "help", "ai"])

    def test_agent_chat_shap_attribution_normalized(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res_risk = agent.chat("Explain Jebel Ali risk", site_id="SITE-JA-01")

        assert res_risk.intent == "alert_explanation"
        assert res_risk.passed_fenced_gate is True
        # Must not contain impossible unnormalized percentages > 100%
        assert "115.0%" not in res_risk.response_text
        assert "210.0%" not in res_risk.response_text
        assert any(t in res_risk.response_text.lower() for t in ["jebel ali", "telemetry", "thermal", "risk", "wbgt", "protocol", "dcas", "attribution", "signal"])

    def test_agent_chat_renal_cohort_percentage(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res_renal = agent.chat("what are renal biomarker rates ?", site_id="SITE-JA-01")

        assert res_renal.intent == "clinical_renal"
        assert res_renal.passed_fenced_gate is True
        assert any(t in res_renal.response_text.lower() for t in ["renal", "kidney", "dehydration", "biomarker", "stage 1", "kdigo", "egfr", "rate"])

    def test_agent_chat_clinical_first_aid(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("worker fainted, need first aid", site_id="SITE-JA-01")

        assert res.intent == "first_aid"
        assert any(term in res.response_text for term in ["Shade", "Cooling", "Hydration", "998"])
        assert res.passed_fenced_gate is True

    def test_agent_chat_follow_up_elaboration(self):
        agent = SovereignCopilotAgent(region_key="uae")
        res = agent.chat("tell me more abou it", site_id="SITE-JA-01")

        assert res.intent == "follow_up_elaboration"
        assert any(term in res.response_text for term in ["Microclimate", "Thermal", "WBGT", "Resolution", "44"])
        assert res.passed_fenced_gate is True

    def test_agent_chat_multi_turn_history(self):
        agent = SovereignCopilotAgent(region_key="uae")
        history = [
            {"role": "user", "content": "What is the status of Jebel Ali?"},
            {"role": "assistant", "content": "Jebel Ali is at Alert Tier with 41.3C WBGT."}
        ]
        res = agent.chat("tell me more about this site", site_id="SITE-JA-01", history=history)

        assert res.intent == "follow_up_elaboration"
        assert res.passed_fenced_gate is True


class TestCopilotAPIEndpoints:
    """Tests FastAPI REST endpoints for Copilot and Dossier."""

    def test_api_statutory_codex(self):
        client = TestClient(app)
        res = client.get("/api/v1/copilot/statutory-codex")
        assert res.status_code == 200
        data = res.json()
        assert data["total_articles"] >= 6
        assert len(data["articles"]) >= 6

    def test_api_dossier_endpoint(self):
        client = TestClient(app)
        res = client.get("/api/v1/copilot/dossier?site_id=SITE-JA-01&date=2025-08-20")
        assert res.status_code == 200
        data = res.json()
        assert data["site_id"] == "SITE-JA-01"
        assert "threat_trajectory" in data
        assert "operational_checklist" in data
        assert "raci_matrix" in data

    def test_api_chat_endpoint(self):
        client = TestClient(app)
        payload = {
            "query": "What is the midday work ban schedule under Resolution 44?",
            "site_id": "SITE-JA-01",
            "target_date": "2025-08-20",
        }
        res = client.post("/api/v1/copilot/chat", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "regulatory_compliance"
        assert data["passed_fenced_gate"] is True
        assert len(data["citations"]) > 0

