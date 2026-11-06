"""
Unit tests for openFDA Clinical Pharmacological Vulnerability Engine.
Verifies loading of FDA Drug Label warnings, PVI index calculation,
and Evidence Card integration.
"""

import pytest
from fastapi.testclient import TestClient

from prahari.ingestion.openfda import OpenFDAClient, ClinicalVulnerabilityEngine
from prahari.detection.l5_policy import PrahariAlert, AlertSeverity
from prahari.decision.evidence_card import EvidenceCardGenerator
from prahari.api.app import app


def test_openfda_curated_dataset():
    """Verify loading curated openFDA drug label vulnerability dataset."""
    client = OpenFDAClient()
    vulns = client.load_curated_vulnerabilities()
    assert len(vulns) >= 6, f"Expected at least 6 vulnerability classes, got {len(vulns)}"

    # Ensure required fields in each vulnerability profile
    first = vulns[0]
    for key in [
        "drug_class_id",
        "class_name",
        "representative_drugs",
        "adverse_reaction_terms",
        "physiological_mechanism",
        "environmental_driver",
        "clinical_mitigation_action",
    ]:
        assert key in first, f"Missing required field '{key}' in openFDA record"


def test_clinical_vulnerability_engine_heat():
    """Verify pharmacological vulnerability index calculation for thermal heatwaves."""
    engine = ClinicalVulnerabilityEngine()
    profile = engine.evaluate_vulnerability_profile(
        alert_type="heat_cluster",
        severity="alert",
        environmental_metrics={"wbgt_max": 34.5},
    )

    assert profile["vulnerability_tier"] == "CRITICAL"
    assert profile["pharmacological_vulnerability_index"] >= 2.0
    assert profile["evaluated_drug_classes_count"] >= 5
    assert len(profile["clinical_directives"]) >= 3

    class_names = [d["class_name"] for d in profile["high_risk_drug_classes"]]
    assert any("Diuretics" in name for name in class_names)
    assert any("Anticholinergic" in name for name in class_names)
    assert any("Beta-Adrenergic" in name for name in class_names)


def test_clinical_vulnerability_engine_respiratory():
    """Verify pharmacological vulnerability index calculation for particulate air hazards."""
    engine = ClinicalVulnerabilityEngine()
    profile = engine.evaluate_vulnerability_profile(
        alert_type="respiratory_surge",
        severity="warning",
        environmental_metrics={"pm25": 140.0},
    )

    assert profile["vulnerability_tier"] in ("HIGH", "CRITICAL")
    assert profile["pharmacological_vulnerability_index"] >= 1.5
    class_names = [d["class_name"] for d in profile["high_risk_drug_classes"]]
    assert any("Respiratory" in name for name in class_names)


def test_evidence_card_includes_clinical_vulnerability():
    """Verify that generated Evidence Cards contain the openFDA pharmacological profile."""
    generator = EvidenceCardGenerator()
    alert = PrahariAlert(
        alert_id="ALT-TEST-CLINICAL",
        alert_type="heat_cluster",
        severity=AlertSeverity.WARNING,
        probability=0.88,
        geo_ids=["SITE-JA-01"],
        obs_date="2025-08-15",
        signal_contributions={"wbgt_max": 0.45, "clinical_heat": 0.35, "absence_heat": 0.20},
    )

    card = generator.generate(alert)
    assert card.alert_id == "ALT-TEST-CLINICAL"
    assert hasattr(card, "clinical_vulnerability")
    assert card.clinical_vulnerability is not None
    assert "pharmacological_vulnerability_index" in card.clinical_vulnerability
    assert card.clinical_vulnerability["vulnerability_tier"] in ("HIGH", "CRITICAL")
    assert len(card.clinical_vulnerability["high_risk_drug_classes"]) >= 4


def test_clinical_vulnerability_api_endpoint():
    """Verify REST API endpoint GET /api/v1/clinical/vulnerability-profile."""
    client = TestClient(app)
    response = client.get("/api/v1/clinical/vulnerability-profile?hazard=heat&severity=alert&wbgt=35.0")
    assert response.status_code == 200
    data = response.json()
    assert "pharmacological_vulnerability_index" in data
    assert data["vulnerability_tier"] == "CRITICAL"
    assert len(data["high_risk_drug_classes"]) >= 5
    assert len(data["clinical_directives"]) >= 3
