"""
Tests for Hands-Free Multilingual Two-Way Voice Intercom (Phase 23).
"""

from prahari.llm.voice_intercom import (
    TwoWayVoiceIntercomEngine,
    VoiceIntercomRequest,
    VoiceIntercomResponse,
)


def test_voice_intercom_entity_extraction_emergency():
    """Verifies that urgent medical symptoms trigger emergency triage classification."""
    engine = TwoWayVoiceIntercomEngine()

    req = VoiceIntercomRequest(
        speech_transcript="Report from Tariq: 4 workers in Zone C are dizzy and vomiting from extreme heat",
        site_id="SITE-JA-01",
    )

    res = engine.process_voice_turn(req)

    assert res.zone_identified == "Zone C"
    assert res.workers_affected == 4
    assert res.clinical_severity == "Emergency"
    assert "AC shelter" in res.spoken_response_en or "shelter" in res.spoken_response_en
    assert len(res.spoken_response_ar) > 10
    assert len(res.spoken_response_ur) > 10
    assert res.fhir_task_id.startswith("task_")
    assert len(res.immediate_directives) >= 3


def test_voice_intercom_routine_break_confirmation():
    """Verifies that routine rest break confirmations are handled gracefully."""
    engine = TwoWayVoiceIntercomEngine()

    req = VoiceIntercomRequest(
        speech_transcript="Confirming 15 minute water and shade rest break for Zone A gang",
        site_id="SITE-JA-01",
    )

    res = engine.process_voice_turn(req)

    assert res.zone_identified == "Zone A"
    assert res.clinical_severity == "Routine"
    assert "break" in res.spoken_response_en.lower() or "timer" in res.spoken_response_en.lower()
    assert "استراحة" in res.spoken_response_ar or "الراحة" in res.spoken_response_ar


def test_voice_intercom_language_detection():
    """Verifies automatic detection of Arabic, Urdu, and English speech scripts."""
    engine = TwoWayVoiceIntercomEngine()

    # English
    lang_en = engine._detect_language("Report: 2 workers exhausted in Zone B")
    assert lang_en == "en"

    # Arabic
    lang_ar = engine._detect_language("تقرير: هناك ثلاثة عمال يشعرون بالإعياء الشديد في الموقع")
    assert lang_ar == "ar"

    # Urdu (distinctive Urdu letters like ے, ں, ٹ)
    lang_ur = engine._detect_language("رپورٹ: زون بی میں دو مزدوروں کی طبیعت خراب ہے")
    assert lang_ur == "ur"


def test_voice_intercom_to_dict_serialization():
    """Verifies JSON serializability for the REST API."""
    engine = TwoWayVoiceIntercomEngine()

    req = VoiceIntercomRequest(
        speech_transcript="Emergency in Zone 1: worker collapsed on dock",
        site_id="SITE-JA-01",
    )
    res = engine.process_voice_turn(req)
    d = res.to_dict()

    assert "incident_id" in d
    assert "triage" in d
    assert d["triage"]["clinical_severity"] == "Emergency"
    assert "audio_dispatches" in d
    assert "en" in d["audio_dispatches"]
    assert "ar" in d["audio_dispatches"]
    assert "ur" in d["audio_dispatches"]
    assert "interop" in d
    assert "fhir_task_id" in d["interop"]


def test_voice_intercom_api_endpoint_aliases():
    """Verifies that the FastAPI voice-intercom endpoint supports transcript aliases."""
    from fastapi.testclient import TestClient
    from prahari.api.app import app

    client = TestClient(app)

    # 1. Using spoken_transcript
    res1 = client.post(
        "/api/v1/llm/voice-intercom",
        json={"spoken_transcript": "Emergency: 2 workers feeling heat exhaustion in Zone B", "site_id": "SITE-JA-01"},
        headers={"X-Role": "surveillance_officer"},
    )
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["clinical_severity"] in ["Emergency", "Urgent"]
    assert "directives" in data1
    assert "spoken_audio" in data1

    # 2. Using transcript alias
    res2 = client.post(
        "/api/v1/llm/voice-intercom",
        json={"transcript": "Zone A gang starting mandatory 15 min shade break", "site_id": "SITE-JA-01"},
        headers={"X-Role": "surveillance_officer"},
    )
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["zone_identified"] == "Zone A"
    assert data2["clinical_severity"] == "Routine"

    # 3. Using speech_transcript alias
    res3 = client.post(
        "/api/v1/llm/voice-intercom",
        json={"speech_transcript": "Worker collapsed near crane in Zone C", "site_id": "SITE-JA-01"},
        headers={"X-Role": "surveillance_officer"},
    )
    assert res3.status_code == 200
    data3 = res3.json()
    assert data3["zone_identified"] == "Zone C"
    assert data3["clinical_severity"] == "Emergency"


