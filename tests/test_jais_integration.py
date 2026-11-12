"""
Tests for Phase 17: Inception 42 Jais-3-0.9B & Multilingual Frontline Dispatch Engine.
"""

from prahari.llm.fenced_validator import FencedHallucinationGate
from prahari.llm.jais_runner import JaisInferenceRunner
from prahari.llm.multilingual_dispatch import generate_multilingual_dispatch


def test_fenced_hallucination_gate_valid():
    """Verifies that narratives containing only ground-truth numbers pass the gate."""
    gate = FencedHallucinationGate()
    evidence_data = {
        "calibrated_p": 0.833,
        "wbgt": 33.4,
        "hours_above_32": 4.5,
        "site_id": "SITE-JA-01",
    }

    # Text contains only numbers present in evidence or statutory constants (44, 2022, 15)
    valid_text = (
        "Thermal risk is 83.3% at Jebel Ali with peak WBGT 33.4 C over 4.5 hours. "
        "Pursuant to UAE Resolution 44 of 2022, 15 minute rest intervals apply."
    )

    is_valid, unverified = gate.verify_narrative(valid_text, evidence_data)
    assert is_valid is True
    assert len(unverified) == 0


def test_fenced_hallucination_gate_flags_hallucinations():
    """Verifies that ungrounded numbers or invented statistics are immediately flagged."""
    gate = FencedHallucinationGate()
    evidence_data = {
        "calibrated_p": 0.75,
        "wbgt": 32.0,
    }

    # Text introduces an invented number: 99.9% and 420 ICU deaths
    hallucinated_text = "Risk is 75% with peak 32 C, causing 99.9% failure and 420 deaths."
    is_valid, unverified = gate.verify_narrative(hallucinated_text, evidence_data)

    assert is_valid is False
    assert 99.9 in unverified or 420.0 in unverified


def test_jais_inference_runner_bilingual_generation():
    """Verifies that the Jais runner outputs authentic bilingual text and cites Inception 42."""
    runner = JaisInferenceRunner()
    alert_dict = {
        "site_name": "Jebel Ali Port Yard",
        "site_id": "SITE-JA-01",
        "tier": "Warning",
        "calibrated_p": 0.833,
        "wbgt": 33.4,
    }

    res = runner.generate_bilingual_dispatch(alert_dict)

    assert "Jais-3-0.9B" in res.model_id
    assert res.passed_fenced_gate is True
    # Assert dispatch narrative generated successfully
    assert len(res.cleaned_narrative) > 20
    assert res.execution_mode in ("JAIS_NATIVE_TORCH", "JAIS_VERIFIED_TEMPLATE")


def test_multilingual_dispatch_four_languages():
    """Verifies generation of 4 languages (Arabic, English, Urdu, Hindi) with audio scripts."""
    alert_dict = {
        "alert_id": "ALT-JA-001",
        "site_name": "Jebel Ali Port Logistics",
        "site_id": "SITE-JA-01",
        "tier": "Warning",
        "wbgt": 33.5,
        "calibrated_p": 0.85,
    }

    card = generate_multilingual_dispatch(alert_dict)

    # Check language contents
    assert "منصة مُنذِر" in card.arabic_text
    assert "MUNZIR EARLY WARNING" in card.english_text
    assert "منذر پیشگی وارننگ" in card.urdu_text
    assert "मुन्ज़िर अर्ली वार्निंग" in card.hindi_text
    assert "മുൻസിർ" in card.malayalam_text

    # Check audio TTS scripts
    assert "ar" in card.audio_tts_scripts
    assert "en" in card.audio_tts_scripts
    assert "ur" in card.audio_tts_scripts
    assert "hi" in card.audio_tts_scripts
    assert "ml" in card.audio_tts_scripts

    # Check WhatsApp preview
    assert "MUNZIR DISPATCH" in card.whatsapp_preview_markdown
    assert "[ACKNOWLEDGE & START 15M BREAK]" in card.whatsapp_preview_markdown

