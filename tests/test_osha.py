"""
Unit tests for OSHA Severe Injury Reports Real-World Data Ingestor.
Verifies loading, PII scrubbing, NLP classification, and Bronze Parquet storage.
"""

from pathlib import Path
import pytest
import pandas as pd

from prahari.ingestion.osha import OSHAIncidentIngestor, DEFAULT_OSHA_DATA_PATH
from prahari.storage.bronze_store import BronzeStore
from prahari.nlp.anonymizer import sanitize_incident_narrative


def test_osha_data_file_exists():
    """Verify that the authentic OSHA dataset file exists and contains valid JSON."""
    assert DEFAULT_OSHA_DATA_PATH.exists(), "OSHA data file not found!"
    ingestor = OSHAIncidentIngestor()
    records = ingestor.load_raw_records()
    assert len(records) >= 50, f"Expected at least 50 OSHA records, got {len(records)}"
    
    # Check required fields in each record
    first = records[0]
    for key in ["osha_id", "event_date", "naics_code", "nature_title", "narrative", "category"]:
        assert key in first, f"Missing required field '{key}' in OSHA record"


def test_osha_training_corpus_extraction():
    """Verify extracting sanitized training corpus for NLP classifier."""
    ingestor = OSHAIncidentIngestor()
    corpus = ingestor.get_training_corpus()
    assert len(corpus) >= 50
    for text, cat in corpus:
        assert isinstance(text, str) and len(text) > 20
        assert cat in {"heat", "respiratory_chemical", "injury", "other"}


def test_osha_pii_sanitization():
    """Verify that inspector narratives are thoroughly scrubbed of personal identifiers."""
    sample_text = (
        "Foreman John Smith (BADGE-99412) reported that worker Ahmed Al-Falasi "
        "at Building #14 Sheikh Zayed Road collapsed from extreme heat. Call +971-50-1234567 or email safety@contractor.ae."
    )
    scrubbed = sanitize_incident_narrative(sample_text)
    assert "John Smith" not in scrubbed
    assert "Ahmed Al-Falasi" not in scrubbed
    assert "99412" not in scrubbed
    assert "safety@contractor.ae" not in scrubbed
    assert "+971" not in scrubbed
    assert "[REDACTED" in scrubbed


def test_osha_ingest_and_bronze_storage(tmp_path):
    """
    Test end-to-end ingestion of OSHA severe injuries into Bronze Parquet storage.
    Verifies creation of both IncidentReports and aggregate SignalObservations.
    """
    store = BronzeStore(base_dir=tmp_path / "bronze")
    ingestor = OSHAIncidentIngestor(bronze_store=store)

    incidents, observations = ingestor.ingest(
        start_date="2024-06-01",
        end_date="2024-08-31",
        write_to_store=True,
    )

    assert len(incidents) > 0, "No incidents ingested in date range"
    assert len(observations) > 0, "No observations generated from incidents"

    # Verify IncidentReports in Bronze store
    df_inc = store.read_incidents(start_date="2024-06-01", end_date="2024-08-31")
    assert not df_inc.empty
    assert len(df_inc) == len(incidents)
    assert "narrative_sanitized" in df_inc.columns
    assert "predicted_category" in df_inc.columns

    # Verify workplace_incident SignalObservations in Bronze store
    df_obs = store.read_observations(
        signal_types=["workplace_incident"],
        start_date="2024-06-01",
        end_date="2024-08-31",
    )
    assert not df_obs.empty
    assert (df_obs["signal_type"] == "workplace_incident").all()
    assert (df_obs["value"] >= 1.0).all()

