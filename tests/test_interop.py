"""
Unit & Integration Tests for Munzir (منذر) Interoperability Module (Phase 9).
Tests HL7 FHIR R4 Surveillance Adapter, SFTP/CSV batch drop with PII rejection,
and Population Stability Index (PSI) model drift monitoring.
"""

import json
import pytest
import numpy as np
from fastapi.testclient import TestClient

from prahari.detection.l5_policy import PrahariAlert, AlertSeverity
from prahari.models.canonical import SignalObservation
from prahari.interop.fhir_adapter import FHIRSurveillanceAdapter
from prahari.interop.sftp_csv import SFTPCSVAdapter
from prahari.interop.drift_monitor import ModelDriftMonitor, DriftReport
from prahari.api.app import app


@pytest.fixture
def sample_alert() -> PrahariAlert:
    return PrahariAlert(
        alert_id="ALT-TST001",
        alert_type="heat_cluster",
        severity=AlertSeverity.WARNING,
        probability=0.78,
        ci_low=0.68,
        ci_high=0.88,
        geo_ids=["SITE-JA-01"],
        obs_date="2026-06-15",
        signal_contributions={"wbgt_max": 0.45, "absence_heat": 0.35},
        dq_status="healthy",
        owner_role="Site Safety Officer",
        recommended_action="Mandate 15m rest per hour and hydration replenishment."
    )


@pytest.fixture
def sample_observations() -> list[SignalObservation]:
    return [
        SignalObservation(
            signal_type="absence_heat",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-15",
            value=25.0,
            denominator=5000.0,
        ),
        SignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-15",
            value=8.0,  # under small cell threshold k=10
            denominator=5000.0,
        ),
    ]


# --- 1. HL7 FHIR Adapter Tests ---

def test_fhir_alert_to_risk_assessment(sample_alert):
    ra = FHIRSurveillanceAdapter.alert_to_risk_assessment(sample_alert)
    assert ra["resourceType"] == "RiskAssessment"
    assert ra["status"] == "final"
    assert "Location/SITE-JA-01" in ra["subject"]["reference"]
    assert len(ra["prediction"]) == 1
    pred = ra["prediction"][0]
    assert pred["probabilityDecimal"] == 0.78
    assert pred["qualitativeRisk"]["text"] == "WARNING"
    assert "78.0%" in pred["rationale"]


def test_fhir_observations_to_measure_report(sample_observations):
    mr = FHIRSurveillanceAdapter.observations_to_measure_report(
        observations=sample_observations,
        district_id="DXB-JA",
        period_start="2026-06-01",
        period_end="2026-06-15"
    )
    assert mr["resourceType"] == "MeasureReport"
    assert mr["status"] == "complete"
    assert mr["type"] == "summary"
    assert len(mr["group"]) == 2
    # Check that codes and populations are mapped
    absence_group = next(g for g in mr["group"] if g["code"]["coding"][0]["code"] == "absence_heat")
    assert absence_group["population"][1]["count"] == 25


def test_fhir_bundle_generation(sample_alert, sample_observations):
    bundle = FHIRSurveillanceAdapter.create_surveillance_bundle(
        alerts=[sample_alert],
        observations=sample_observations,
        district_id="UAE-DXB",
        period_start="2026-06-01",
        period_end="2026-06-15"
    )
    assert bundle["resourceType"] == "Bundle"
    assert bundle["type"] == "collection"
    assert bundle["total"] == 2
    res_types = [e["resource"]["resourceType"] for e in bundle["entry"]]
    assert "RiskAssessment" in res_types
    assert "MeasureReport" in res_types


# --- 2. SFTP / CSV Adapter Tests ---

def test_sftp_csv_valid_ingest():
    csv_data = """site_id,obs_date,workforce_size,absence_heat_count,heat_illness_count,first_aid_count
SITE-01,2026-06-15,1200,12,3,5
SITE-02,2026-06-15,850,4,1,2
"""
    obs, warnings = SFTPCSVAdapter.ingest_workplace_batch(csv_data)
    assert len(obs) == 6  # 3 signals * 2 sites
    assert len(warnings) == 0
    assert all(o.geo_id in ["SITE-01", "SITE-02"] for o in obs)


def test_sftp_csv_rejects_pii_violation():
    # Attempt to upload batch containing prohibited employee_id and worker_name
    malicious_csv = """site_id,obs_date,workforce_size,absence_heat_count,worker_name,emirates_id
SITE-01,2026-06-15,1200,12,John Doe,784-1980-1234567-1
"""
    with pytest.raises(ValueError) as excinfo:
        SFTPCSVAdapter.ingest_workplace_batch(malicious_csv)
    assert "Privacy Violation" in str(excinfo.value)
    assert "worker_name" in str(excinfo.value) or "emirates_id" in str(excinfo.value)


def test_sftp_csv_export_small_cell_suppression(sample_observations):
    ehs_csv = SFTPCSVAdapter.export_ehs_summary(sample_observations, min_cell_size=10)
    lines = ehs_csv.strip().split("\n")
    assert len(lines) == 3  # Header + 2 data rows
    # The clinical_resp observation had value=8, which must be suppressed to '<10'
    assert "<10" in lines[2]
    # The absence_heat observation had value=25, which remains '25'
    assert "25" in lines[1]


# --- 3. Model Drift & PSI Tests ---

def test_psi_identical_distributions():
    rng = np.random.default_rng(42)
    expected = rng.normal(30, 5, 2000)
    actual = rng.normal(30, 5, 2000)
    psi = ModelDriftMonitor.calculate_psi(expected, actual)
    assert psi < 0.05  # Should be close to 0


def test_psi_shifted_distribution():
    rng = np.random.default_rng(42)
    expected = rng.normal(30, 5, 2000)
    actual = rng.normal(42, 6, 2000)  # Significant shift
    psi = ModelDriftMonitor.calculate_psi(expected, actual)
    assert psi > 0.25  # Critical shift


def test_drift_monitor_evaluation():
    rng = np.random.default_rng(42)
    base = {"feat_a": rng.normal(10, 2, 500)}
    curr = {"feat_a": rng.normal(10.2, 2.1, 500)}
    report = ModelDriftMonitor.evaluate_model_drift(
        baseline_features=base,
        current_features=curr,
        recent_probabilities=[0.2, 0.3, 0.7],
        recent_ground_truth=[0, 0, 1]
    )
    assert isinstance(report, DriftReport)
    assert report.overall_status in ["healthy", "warning", "critical"]
    assert "feat_a" in report.psi_scores


# --- 4. FastAPI Endpoints Integration ---

client = TestClient(app)


def test_api_fhir_export_endpoint():
    # Call with surveillance_officer role header
    headers = {"X-Role": "surveillance_officer"}
    response = client.get("/api/v1/interop/fhir/export?district_id=UAE-DXB", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["resourceType"] == "Bundle"
    assert data["type"] == "collection"
    assert data["total"] > 0


def test_api_drift_report_endpoint():
    response = client.get("/api/v1/interop/drift/report")
    assert response.status_code == 200
    data = response.json()
    assert "overall_status" in data
    assert "max_psi" in data
    assert "psi_scores" in data
    assert "data_freshness_hrs" in data


def test_api_sftp_ingest_endpoint_valid_and_pii_block():
    headers = {"X-Role": "employer_safety", "X-Employer-ID": "SITE-01"}
    
    # Valid CSV
    valid_csv = "site_id,obs_date,workforce_size,absence_heat_count\nSITE-01,2026-06-15,500,6\n"
    res_valid = client.post("/api/v1/interop/sftp/ingest", content=valid_csv, headers=headers)
    assert res_valid.status_code == 200
    assert res_valid.json()["status"] == "success"
    assert res_valid.json()["ingested_observations"] == 1

    # PII CSV
    pii_csv = "site_id,obs_date,workforce_size,absence_heat_count,worker_name\nSITE-01,2026-06-15,500,6,John\n"
    res_pii = client.post("/api/v1/interop/sftp/ingest", content=pii_csv, headers=headers)
    assert res_pii.status_code == 400
    assert "Privacy Violation" in res_pii.json()["detail"]
