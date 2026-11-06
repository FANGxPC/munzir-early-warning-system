"""
Comprehensive Unit & Integration Test Suite for Munzir Sentinel Hardware (Phase 11).
Tests telemetry ingestion, sanity bound gating, server-side WBGT physics re-derivation,
node commissioning, H3 spatial resolution, offline heartbeat detection, stuck sensor
filtering, and REST API endpoints.
"""

from datetime import datetime, timezone, timedelta
import pytest
from fastapi.testclient import TestClient

from prahari.config import (
    SENTINEL_LOCATION_EXACT_THRESHOLD_M,
    SENTINEL_LOCATION_INFERRED_THRESHOLD_M,
)
from prahari.models.canonical import (
    SentinelUpload,
    SentinelUploadResponse,
    SentinelCommission,
    SentinelNodeStatus,
)
from prahari.ingestion.sentinel_ingest import SentinelIngestionEngine
from prahari.ingestion.data_quality import DataQualityScorer
from prahari.api.app import app


@pytest.fixture
def fresh_engine(tmp_path):
    """Instantiates a clean SentinelIngestionEngine with temporary persistence."""
    node_file = tmp_path / "sentinel_nodes.json"
    return SentinelIngestionEngine(persistence_file=node_file)


@pytest.fixture
def commissioned_node(fresh_engine):
    """Provides a fresh engine with a commissioned SENT-001 node."""
    comm = SentinelCommission(
        node_id="SENT-001",
        site_id="SITE-JA-01",
        latitude=24.9920,
        longitude=55.0410,
        accuracy_m=14.0,
        method="browser_geolocation",
        indoor_mode=False,
    )
    fresh_engine.commission_node(comm)
    return fresh_engine


# --- 1. Ingestion & Bound Verification Tests ---

def test_sentinel_upload_valid_payload(commissioned_node):
    upload = SentinelUpload(
        node_id="SENT-001",
        seq=1,
        ts="2026-11-06T10:00:00Z",
        air_temp_c=34.0,
        rh_pct=60.0,
        globe_temp_c=42.0,
        wbgt_est_c=31.2,
        ok={"dht": True, "globe": True, "rssi": -65}
    )
    resp = commissioned_node.process_upload(upload)
    assert isinstance(resp, SentinelUploadResponse)
    assert resp.node_id == "SENT-001"
    assert resp.level in ["Watch", "Warning", "Alert"]
    assert resp.rederived_wbgt is not None
    assert 25.0 < resp.rederived_wbgt < 40.0

    status = commissioned_node.get_node_status("SENT-001")
    assert status.is_online is True
    assert status.readings_today == 1
    assert status.last_air_temp == 34.0


def test_sentinel_upload_rejects_out_of_bounds(commissioned_node):
    # Air temp 120°C and RH 150% are physically impossible
    upload = SentinelUpload(
        node_id="SENT-001",
        seq=2,
        ts="2026-11-06T10:01:00Z",
        air_temp_c=120.0,
        rh_pct=150.0,
        globe_temp_c=42.0,
        wbgt_est_c=45.0,
        ok={"dht": True, "globe": True, "rssi": -65}
    )
    resp = commissioned_node.process_upload(upload)
    # Since air temp was nulled out, rederived WBGT is None and level is None
    assert resp.rederived_wbgt is None
    assert resp.level == "None"

    status = commissioned_node.get_node_status("SENT-001")
    assert status.sensor_health["dht"] is False


def test_sentinel_upload_null_globe_falls_back(commissioned_node):
    # Missing globe sensor falls back to no-radiant formula without crash
    upload = SentinelUpload(
        node_id="SENT-001",
        seq=3,
        ts="2026-11-06T10:02:00Z",
        air_temp_c=32.0,
        rh_pct=50.0,
        globe_temp_c=None,
        wbgt_est_c=28.0,
        ok={"dht": True, "globe": False, "rssi": -65}
    )
    resp = commissioned_node.process_upload(upload)
    assert resp.rederived_wbgt is not None
    status = commissioned_node.get_node_status("SENT-001")
    assert status.sensor_health["globe"] is False


def test_sentinel_upload_uncommissioned_node(fresh_engine):
    upload = SentinelUpload(
        node_id="SENT-GHOST-99",
        seq=1,
        ts="2026-11-06T10:00:00Z",
        air_temp_c=30.0,
        rh_pct=50.0,
        globe_temp_c=35.0,
    )
    with pytest.raises(KeyError) as excinfo:
        fresh_engine.process_upload(upload)
    assert "not commissioned" in str(excinfo.value)


# --- 2. Commissioning & Geolocation Fallback Hierarchy Tests ---

def test_sentinel_commission_location_exact(fresh_engine):
    comm = SentinelCommission(
        node_id="SENT-EXACT",
        site_id="SITE-JA-01",
        latitude=24.9920,
        longitude=55.0410,
        accuracy_m=15.0,  # <= 50m
        method="browser_geolocation"
    )
    status = fresh_engine.commission_node(comm)
    assert status.location_confidence == "exact"
    assert status.h3_index is not None
    assert len(status.h3_index) == 15


def test_sentinel_commission_location_inferred(fresh_engine):
    comm = SentinelCommission(
        node_id="SENT-INFERRED",
        site_id="SITE-AQ-01",
        latitude=25.1380,
        longitude=55.2390,
        accuracy_m=250.0,  # 50m < accuracy <= 1000m
        method="browser_geolocation"
    )
    status = fresh_engine.commission_node(comm)
    assert status.location_confidence == "inferred"


def test_sentinel_commission_location_district(fresh_engine):
    comm = SentinelCommission(
        node_id="SENT-COARSE",
        site_id="SITE-DS-01",
        latitude=24.8910,
        longitude=55.1620,
        accuracy_m=2500.0,  # > 1000m
        method="ip_geolocation"
    )
    status = fresh_engine.commission_node(comm)
    assert status.location_confidence == "district_only"


def test_sentinel_commission_rejects_unknown_site(fresh_engine):
    comm = SentinelCommission(
        node_id="SENT-BAD",
        site_id="SITE-NONEXISTENT-999",
        latitude=24.9920,
        longitude=55.0410,
        accuracy_m=10.0,
    )
    with pytest.raises(ValueError) as excinfo:
        fresh_engine.commission_node(comm)
    assert "Unknown worksite ID" in str(excinfo.value)


# --- 3. Operational Resilience: Heartbeat Timeout & Stuck Sensor ---

def test_sentinel_offline_detection(commissioned_node):
    # Simulate reading from 10 minutes ago
    ten_mins_ago = (datetime.now(timezone.utc) - timedelta(minutes=10)).isoformat()
    upload = SentinelUpload(
        node_id="SENT-001",
        seq=1,
        ts=ten_mins_ago,
        air_temp_c=30.0,
        rh_pct=50.0,
        globe_temp_c=35.0,
    )
    commissioned_node.process_upload(upload)
    
    # Heartbeat check should evaluate to offline (since > 180s)
    status = commissioned_node.get_node_status("SENT-001")
    assert status.is_online is False


def test_sentinel_stuck_sensor_detection(commissioned_node):
    # Send 11 readings with identical air temp (sensor stuck)
    for i in range(11):
        upload = SentinelUpload(
            node_id="SENT-001",
            seq=i + 1,
            ts=f"2026-11-06T10:{i:02d}:00Z",
            air_temp_c=32.456,  # exactly unchanged
            rh_pct=50.0 + (i * 0.1),
            globe_temp_c=38.0 + (i * 0.2),
        )
        commissioned_node.process_upload(upload)

    status = commissioned_node.get_node_status("SENT-001")
    assert status.sensor_health["dht"] is False  # Stuck sensor flagged


def test_sentinel_button_ack_logging(commissioned_node):
    ack = commissioned_node.log_node_ack("SENT-001")
    assert ack["source"] == "sentinel_button"
    assert ack["node_id"] == "SENT-001"
    assert ack["user_role"] == "on_site_operator"
    assert ack["action"] == "site_acknowledged"


# --- 4. Data Quality Scoring for Hardware Feed ---

def test_sentinel_dq_completeness_scoring():
    scorer = DataQualityScorer()
    # 720 readings out of 1440 expected in 24h = 50% completeness
    comp_score = scorer.compute_sentinel_completeness("SENT-001", readings_received=720, expected_readings=1440)
    assert comp_score == 0.5

    # Full 1440 readings = 1.0 completeness
    assert scorer.compute_sentinel_completeness("SENT-001", readings_received=1440) == 1.0


# --- 5. REST API Integration Endpoints ---

client = TestClient(app)


def test_api_sentinel_full_lifecycle():
    # 1. Commission node via API
    comm_payload = {
        "node_id": "SENT-E2E-01",
        "site_id": "SITE-JA-01",
        "latitude": 24.9920,
        "longitude": 55.0410,
        "accuracy_m": 12.0,
        "method": "browser_geolocation",
        "indoor_mode": False
    }
    res_comm = client.post(
        "/api/v1/sentinel/commission",
        json=comm_payload,
        headers={"X-Role": "employer_safety"}
    )
    assert res_comm.status_code == 200
    data_comm = res_comm.json()
    assert data_comm["node_id"] == "SENT-E2E-01"
    assert data_comm["location_confidence"] == "exact"

    # 2. Upload telemetry via API
    up_payload = {
        "node_id": "SENT-E2E-01",
        "seq": 1,
        "ts": "2026-11-06T10:15:00Z",
        "air_temp_c": 36.2,
        "rh_pct": 58.0,
        "globe_temp_c": 44.0,
        "wbgt_est_c": 32.5,
        "ok": {"dht": True, "globe": True, "rssi": -60}
    }
    res_up = client.post(
        "/api/v1/sentinel/upload",
        json=up_payload,
        headers={"X-Sentinel-Key": "munzir_sentinel_secret_2026"}
    )
    assert res_up.status_code == 200
    data_up = res_up.json()
    assert data_up["node_id"] == "SENT-E2E-01"
    assert data_up["level"] in ["Warning", "Alert"]
    assert "valid_until" in data_up

    # 3. Retrieve fleet status
    res_fleet = client.get("/api/v1/sentinel/nodes")
    assert res_fleet.status_code == 200
    nodes = res_fleet.json()
    e2e_node = next((n for n in nodes if n["node_id"] == "SENT-E2E-01"), None)
    assert e2e_node is not None
    assert e2e_node["is_online"] is True
    assert e2e_node["last_wbgt"] is not None

    # 4. Button acknowledgement via API
    res_ack = client.post("/api/v1/sentinel/ack", json={"node_id": "SENT-E2E-01"})
    assert res_ack.status_code == 200
    assert res_ack.json()["status"] == "acknowledged"


def test_api_sentinel_upload_uncommissioned_returns_404():
    up_payload = {
        "node_id": "SENT-UNKNOWN-99",
        "seq": 1,
        "ts": "2026-11-06T10:15:00Z",
        "air_temp_c": 30.0,
        "rh_pct": 50.0,
    }
    res = client.post("/api/v1/sentinel/upload", json=up_payload)
    assert res.status_code == 404
    assert "not commissioned" in res.json()["detail"]

