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

