"""Tests for PII anonymizer and incident text classifier."""

import tempfile
from pathlib import Path
from prahari.nlp.anonymizer import sanitize_incident_narrative
from prahari.nlp.classifier import IncidentClassifier


def test_pii_anonymization():
    raw_text = (
        "Mr. Ahmed Al Mansoori (Badge EMP-9482, Emirates ID 784-1985-1234567-1) "
        "collapsed at Plot 45 Al Quoz Street. Call Dr. Sarah at +971 50 123 4567 "
        "or email ahmed.mansoori@construction.ae immediately."
    )
    sanitized = sanitize_incident_narrative(raw_text)

    # Ensure no PII survives
    assert "Ahmed" not in sanitized
    assert "EMP-9482" not in sanitized
    assert "784-1985-1234567-1" not in sanitized
    assert "+971" not in sanitized
    assert "ahmed.mansoori@construction.ae" not in sanitized

    # Redaction tokens present
    assert "[REDACTED_NAME]" in sanitized
    assert "[REDACTED_BADGE]" in sanitized
    assert "[REDACTED_ID]" in sanitized
    assert "[REDACTED_PHONE]" in sanitized
    assert "[REDACTED_EMAIL]" in sanitized


def test_incident_classifier_training_and_inference():
    with tempfile.TemporaryDirectory() as tmpdir:
        model_path = Path(tmpdir) / "test_model.joblib"
        classifier = IncidentClassifier(model_path=model_path)

        metrics = classifier.train()
        assert metrics["cv_macro_f1"] >= 0.80
        assert metrics["accuracy"] >= 0.80
        assert model_path.exists()

        # Test heat inference
        heat_text = "Worker John Doe collapsed on outdoor roof from heat exhaustion and dehydration."
        cat, conf = classifier.predict(heat_text)
        assert cat == "heat"
        assert conf > 0.50

        # Test respiratory/chemical inference
        chem_text = "Painter inhaled toxic solvent vapors and suffered severe coughing fit."
        cat, conf = classifier.predict(chem_text)
        assert cat == "respiratory_chemical"
        assert conf > 0.50

        # Test injury inference
        injury_text = "Scaffolder slipped on platform and sustained broken wrist fracture."
        cat, conf = classifier.predict(injury_text)
        assert cat == "injury"
        assert conf > 0.50
