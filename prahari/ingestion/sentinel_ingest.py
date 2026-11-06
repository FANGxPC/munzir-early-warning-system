"""
Munzir Sentinel On-Site Hardware Ingestion Engine (Phase 11).
Processes telemetry uploads from ESP32 nodes, re-derives WBGT using Stull
micrometeorology physics, evaluates sensor sanity bounds, detects stuck sensors,
maintains node commission records, and resolves real-time alert levels for on-board LED feedback.
"""

from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import json

from prahari.config import (
    GOLD_DIR,
    REGIONAL_PROFILES,
    SENTINEL_BOUNDS,
    SENTINEL_OFFLINE_THRESHOLD_SECS,
    SENTINEL_VALID_UNTIL_BUFFER_SECS,
    SENTINEL_LOCATION_EXACT_THRESHOLD_M,
    SENTINEL_LOCATION_INFERRED_THRESHOLD_M,
    WBGT_CAUTION,
    WBGT_EXTREME_CAUTION,
    WBGT_DANGER,
)
from prahari.models.canonical import (
    SentinelUpload,
    SentinelUploadResponse,
    SentinelCommission,
    SentinelNodeStatus,
    SignalObservation,
)
from prahari.ingestion.wbgt import compute_stull_wet_bulb
from prahari.harmonisation.spatial import get_h3_index
from prahari.storage.bronze_store import BronzeStore


class SentinelIngestionEngine:
    """
    Validates, re-derives, and persists telemetry from shade-mounted ESP32 Sentinel nodes.
    Integrates directly with Bronze storage and the Munzir alert policy pipeline.
    """

    def __init__(self, persistence_file: Optional[Path] = None):
        self.persistence_file = persistence_file or (GOLD_DIR / "sentinel" / "nodes.json")
        self.persistence_file.parent.mkdir(parents=True, exist_ok=True)
        self.bronze_store = BronzeStore()

        self._node_registry: Dict[str, SentinelCommission] = {}
        self._node_state: Dict[str, SentinelNodeStatus] = {}
        self._reading_history: Dict[str, List[Dict[str, Any]]] = {}
        self._last_seq: Dict[str, int] = {}
        self._site_lookup: Dict[str, Dict[str, Any]] = {}

        self._build_site_lookup()
        self._load_persisted_nodes()

    def _build_site_lookup(self) -> None:
        """Indexes known physical sites across regional configurations."""
        for reg_key, reg_cfg in REGIONAL_PROFILES.items():
            for site in reg_cfg.get("sites", []):
                self._site_lookup[site["id"]] = {
                    **site,
                    "region": reg_key,
                }

    def _load_persisted_nodes(self) -> None:
        """Restores registered nodes from Gold storage if file exists."""
        if self.persistence_file.exists():
            try:
                data = json.loads(self.persistence_file.read_text(encoding="utf-8"))
                for item in data:
                    comm = SentinelCommission(**item)
                    self._register_commission_internal(comm, persist=False)
            except Exception:
                pass

    def _persist_nodes(self) -> None:
        """Serializes commissioned nodes to Gold storage."""
        data = [c.model_dump() for c in self._node_registry.values()]
        self.persistence_file.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _register_commission_internal(
        self,
        commission: SentinelCommission,
        persist: bool = True
    ) -> SentinelNodeStatus:
        """Internal helper to configure node registry and spatial hierarchy."""
        site_info = self._site_lookup.get(commission.site_id)
        if not site_info:
            raise ValueError(f"Unknown worksite ID '{commission.site_id}'. Must be a registered site in regional config.")

        district_id = site_info.get("district_id", "DXB-JA")
        h3_cell = get_h3_index(commission.latitude, commission.longitude)

        # Geolocation confidence assignment based on browser accuracy
        if commission.accuracy_m <= SENTINEL_LOCATION_EXACT_THRESHOLD_M:
            loc_conf = "exact"
        elif commission.accuracy_m <= SENTINEL_LOCATION_INFERRED_THRESHOLD_M:
            loc_conf = "inferred"
        else:
            loc_conf = "district_only"

        self._node_registry[commission.node_id] = commission

        # Initialize or preserve state
        existing = self._node_state.get(commission.node_id)
        status = SentinelNodeStatus(
            node_id=commission.node_id,
            site_id=commission.site_id,
            district_id=district_id,
            is_online=True if existing is None else existing.is_online,
            last_seen_utc=existing.last_seen_utc if existing else None,
            last_wbgt=existing.last_wbgt if existing else None,
            last_air_temp=existing.last_air_temp if existing else None,
            last_rh=existing.last_rh if existing else None,
            last_globe_temp=existing.last_globe_temp if existing else None,
            sensor_health=existing.sensor_health if existing else {"dht": True, "globe": True},
            location_confidence=loc_conf,
            h3_index=h3_cell,
            current_level=existing.current_level if existing else "None",
            readings_today=existing.readings_today if existing else 0,
            gaps_today=existing.gaps_today if existing else 0,
            indoor_mode=commission.indoor_mode,
        )
        self._node_state[commission.node_id] = status

        if persist:
            self._persist_nodes()

        return status

    def commission_node(self, commission: SentinelCommission) -> SentinelNodeStatus:
        """Public API to commission a new ESP32 Sentinel node with verified location."""
        return self._register_commission_internal(commission, persist=True)

    def _validate_bounds(self, upload: SentinelUpload) -> Tuple[Optional[float], Optional[float], Optional[float]]:
        """
        Validates telemetry against physical sensor bounds.
        Returns (valid_air_temp, valid_rh, valid_globe_temp). Nulls out invalid readings.
        """
        air_t = upload.air_temp_c
        if air_t is not None:
            low, high = SENTINEL_BOUNDS["air_temp_c"]
            if not (low <= air_t <= high):
                air_t = None

        rh = upload.rh_pct
        if rh is not None:
            low, high = SENTINEL_BOUNDS["rh_pct"]
            if not (low <= rh <= high):
                rh = None

        globe_t = upload.globe_temp_c
        if globe_t is not None:
            low, high = SENTINEL_BOUNDS["globe_temp_c"]
            if not (low <= globe_t <= high):
                globe_t = None

        return air_t, rh, globe_t

    def _check_stuck_sensor(self, node_id: str, field_name: str, current_val: Optional[float]) -> bool:
        """
        Detects if a sensor reading has remained identical for 10+ consecutive minutes.
        Returns True if sensor appears stuck (unhealthy).
        """
        if current_val is None:
            return False

        hist = self._reading_history.get(node_id, [])
        if len(hist) < 10:
            return False

        recent_vals = [h.get(field_name) for h in hist[-10:] if h.get(field_name) is not None]
        if len(recent_vals) >= 10 and all(abs(v - current_val) < 1e-4 for v in recent_vals):
            return True
        return False

    def _rederive_wbgt(
        self,
        air_temp: Optional[float],
        rh: Optional[float],
        globe_temp: Optional[float],
        indoor_mode: bool = False
    ) -> Optional[float]:
        """
        Re-derives WBGT using Stull's natural wet-bulb approximation.
        Formula:
          - Outdoor: 0.7 * Tnw + 0.2 * Tg + 0.1 * Ta
          - Indoor / No-globe: 0.7 * Tnw + 0.3 * (Tg if available else Ta)
        """
        if air_temp is None or rh is None:
            return None

        tnw = compute_stull_wet_bulb(temp_c=air_temp, rel_humidity_pct=rh)

        if indoor_mode or globe_temp is None:
            tg_effective = globe_temp if globe_temp is not None else air_temp
            wbgt = 0.7 * tnw + 0.3 * tg_effective
        else:
            wbgt = 0.7 * tnw + 0.2 * globe_temp + 0.1 * air_temp

        # Bound check
        low, high = SENTINEL_BOUNDS["wbgt_est_c"]
        wbgt = max(low, min(high, wbgt))
        return float(round(wbgt, 2))

    def _resolve_alert_level(self, wbgt: Optional[float], site_id: str) -> str:
        """
        Determines the alert level to return to the node to light the on-board LED.
        Grounded in UAE MOHRE / OSHA heat stress thresholds.
        """
        if wbgt is None:
            return "None"

        if wbgt >= WBGT_DANGER:
            return "Alert"
        elif wbgt >= WBGT_EXTREME_CAUTION:
            return "Warning"
        elif wbgt >= WBGT_CAUTION:
            return "Watch"
        return "None"

    def process_upload(self, upload: SentinelUpload) -> SentinelUploadResponse:
        """
        Processes inbound telemetry from an ESP32 Sentinel node:
        1. Verifies node commissioning
        2. Validates sensor bounds & stuck status
        3. Re-derives on-site WBGT
        4. Writes SignalObservations into Bronze storage
        5. Computes alert level & valid_until timestamp
        """
        if upload.node_id not in self._node_registry:
            raise KeyError(f"Node '{upload.node_id}' is not commissioned. Must commission node before uploading telemetry.")

        commission = self._node_registry[upload.node_id]
        status = self._node_state[upload.node_id]

        # 1. Sequence gap detection
        last_s = self._last_seq.get(upload.node_id)
        if last_s is not None and upload.seq > (last_s + 1):
            status.gaps_today += (upload.seq - last_s - 1)
        self._last_seq[upload.node_id] = upload.seq

        # 2. Sanity bound checks
        air_t, rh, globe_t = self._validate_bounds(upload)

        # 3. Stuck sensor detection
        dht_stuck = self._check_stuck_sensor(upload.node_id, "air_temp_c", air_t)
        globe_stuck = self._check_stuck_sensor(upload.node_id, "globe_temp_c", globe_t)

        sensor_health = {
            "dht": (air_t is not None and rh is not None and not dht_stuck),
            "globe": (globe_t is not None and not globe_stuck),
        }

        # 4. Re-derive WBGT
        wbgt = self._rederive_wbgt(
            air_temp=air_t,
            rh=rh,
            globe_temp=globe_t,
            indoor_mode=commission.indoor_mode
        )

        # 5. Determine Alert Level & valid_until window
        level = self._resolve_alert_level(wbgt=wbgt, site_id=commission.site_id)
        now_dt = datetime.now(timezone.utc)
        valid_until_dt = now_dt + timedelta(seconds=SENTINEL_VALID_UNTIL_BUFFER_SECS)
        valid_until_iso = valid_until_dt.isoformat()

        # 6. Emit canonical SignalObservation rows into Bronze lakehouse
        obs_date = upload.ts[:10] if len(upload.ts) >= 10 else now_dt.strftime("%Y-%m-%d")
        observations_to_write: List[SignalObservation] = []

        if wbgt is not None:
            observations_to_write.append(SignalObservation(
                signal_type="wbgt_onsite",
                geo_level="site",
                geo_id=commission.site_id,
                location_confidence=status.location_confidence,
                obs_date=obs_date,
                value=wbgt,
                source_latency_hrs=0.02,
                completeness_score=1.0,
            ))

        if air_t is not None:
            observations_to_write.append(SignalObservation(
                signal_type="air_temp_onsite",
                geo_level="site",
                geo_id=commission.site_id,
                location_confidence=status.location_confidence,
                obs_date=obs_date,
                value=air_t,
                source_latency_hrs=0.02,
                completeness_score=1.0,
            ))

        if rh is not None:
            observations_to_write.append(SignalObservation(
                signal_type="rh_onsite",
                geo_level="site",
                geo_id=commission.site_id,
                location_confidence=status.location_confidence,
                obs_date=obs_date,
                value=rh,
                source_latency_hrs=0.02,
                completeness_score=1.0,
            ))

        if globe_t is not None:
            observations_to_write.append(SignalObservation(
                signal_type="globe_temp_onsite",
                geo_level="site",
                geo_id=commission.site_id,
                location_confidence=status.location_confidence,
                obs_date=obs_date,
                value=globe_t,
                source_latency_hrs=0.02,
                completeness_score=1.0,
            ))

        if observations_to_write:
            self.bronze_store.write_observations(observations_to_write)

        # 7. Update node state & reading history
        status.is_online = True

        # Determine last seen timestamp:
        # Microcontrollers without an RTC or NTP clock often send pseudo timestamps (e.g. uptime starting at 00:00:xx).
        # If upload.ts is wildly out of sync with current server time (> 3600s difference),
        # use current server UTC reception time so the device is not falsely marked offline.
        now_dt = datetime.now(timezone.utc)
        try:
            ts_str = upload.ts.replace("Z", "+00:00")
            upload_dt = datetime.fromisoformat(ts_str)
            if abs((now_dt - upload_dt).total_seconds()) > 3600:
                status.last_seen_utc = now_dt.isoformat()
            else:
                status.last_seen_utc = upload.ts
        except Exception:
            status.last_seen_utc = now_dt.isoformat()

        status.last_wbgt = wbgt
        status.last_air_temp = air_t
        status.last_rh = rh
        status.last_globe_temp = globe_t
        status.sensor_health = sensor_health
        status.current_level = level
        status.readings_today += 1

        if upload.node_id not in self._reading_history:
            self._reading_history[upload.node_id] = []
        self._reading_history[upload.node_id].append({
            "ts": upload.ts,
            "air_temp_c": air_t,
            "rh_pct": rh,
            "globe_temp_c": globe_t,
            "wbgt": wbgt,
        })
        # Keep sliding 1-hour window (60 readings)
        if len(self._reading_history[upload.node_id]) > 60:
            self._reading_history[upload.node_id].pop(0)

        return SentinelUploadResponse(
            node_id=upload.node_id,
            level=level,
            valid_until=valid_until_iso,
            rederived_wbgt=wbgt,
        )

    def get_node_status(self, node_id: str) -> Optional[SentinelNodeStatus]:
        """Returns node health, verifying heartbeat threshold."""
        status = self._node_state.get(node_id)
        if not status:
            return None

        # Check offline heartbeat timeout
        if status.last_seen_utc:
            try:
                # Handle ISO timestamps with or without Z
                ts_str = status.last_seen_utc.replace("Z", "+00:00")
                last_dt = datetime.fromisoformat(ts_str)
                now_dt = datetime.now(timezone.utc)
                diff_sec = (now_dt - last_dt).total_seconds()
                if diff_sec > SENTINEL_OFFLINE_THRESHOLD_SECS:
                    status.is_online = False
            except Exception:
                pass

        return status

    def get_all_nodes(self) -> List[SentinelNodeStatus]:
        """Returns fleet list with up-to-date online/offline heartbeat status."""
        for nid in list(self._node_state.keys()):
            self.get_node_status(nid)
        return list(self._node_state.values())

    def log_node_ack(self, node_id: str, ts: Optional[str] = None) -> Dict[str, Any]:
        """
        Logs an on-site hardware button acknowledgement (BOOT button).
        Distinguished from formal clinical officer triage.
        """
        if node_id not in self._node_registry:
            raise KeyError(f"Node '{node_id}' is not commissioned.")

        commission = self._node_registry[node_id]
        now_iso = ts or datetime.now(timezone.utc).isoformat()

        ack_record = {
            "source": "sentinel_button",
            "node_id": node_id,
            "site_id": commission.site_id,
            "timestamp": now_iso,
            "user_role": "on_site_operator",
            "action": "site_acknowledged",
            "message": "Physical on-site Sentinel button pressed. Node operator confirmed hazard awareness."
        }

        # Append to sentinel ack log
        ack_file = GOLD_DIR / "sentinel" / "button_acks.jsonl"
        with open(ack_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(ack_record) + "\n")

        return ack_record

