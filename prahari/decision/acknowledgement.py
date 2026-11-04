"""
Human-in-the-Loop Acknowledgement and Operational Audit Trail Engine.
Tracks alert transitions (Acknowledge / Act / Dismiss with mandatory reason),
maintains non-repudiation audit logs, and computes real-world Positive Predictive Value (PPV).
"""

from dataclasses import asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prahari.config import GOLD_DIR

DEFAULT_ACK_DIR = Path(GOLD_DIR) / "acknowledgements"


class AlertStatus(str, Enum):
    PENDING = "pending"
    ACKNOWLEDGED = "acknowledged"
    ACTED = "acted"
    DISMISSED = "dismissed"


DISMISS_REASONS = [
    "benign_local_event",
    "data_artefact_backlog",
    "already_managed_duplicate",
    "false_positive_noise",
    "other",
]


class AcknowledgementRecord:
    """Audit log entry capturing state transitions by authorized users."""

    def __init__(
        self,
        alert_id: str,
        incident_id: str,
        user_role: str,
        status: AlertStatus,
        user_name: str = "Surveillance Officer",
        action_taken: Optional[str] = None,
        dismiss_reason: Optional[str] = None,
        comment: str = "",
        created_at: Optional[str] = None,
        latency_minutes: float = 0.0,
        record_id: Optional[str] = None,
    ):
        self.record_id = record_id or f"ACK-{str(uuid4())[:8].upper()}"
        self.alert_id = alert_id
        self.incident_id = incident_id
        self.user_role = user_role
        self.user_name = user_name
        self.status = status if isinstance(status, AlertStatus) else AlertStatus(status)
        self.action_taken = action_taken
        self.dismiss_reason = dismiss_reason
        self.comment = comment
        self.created_at = created_at or datetime.now().isoformat()
        self.latency_minutes = latency_minutes

    def to_dict(self) -> Dict[str, Any]:
        return {
            "record_id": self.record_id,
            "alert_id": self.alert_id,
            "incident_id": self.incident_id,
            "user_role": self.user_role,
            "user_name": self.user_name,
            "status": self.status.value,
            "action_taken": self.action_taken or "",
            "dismiss_reason": self.dismiss_reason or "",
            "comment": self.comment,
            "created_at": self.created_at,
            "latency_minutes": self.latency_minutes,
        }


class AcknowledgementManager:
    """
    Manages human-in-the-loop workflows, state storage, and audit logs.
    """

    def __init__(self, ack_dir: Optional[Path] = None):
        self.ack_dir = Path(ack_dir or DEFAULT_ACK_DIR)
        self.ack_dir.mkdir(parents=True, exist_ok=True)
        self.audit_log_path = self.ack_dir / "audit_log.parquet"
        self.records: List[AcknowledgementRecord] = []
        self._load_records()

    def _load_records(self) -> None:
        """Loads historical audit trail from disk if exists."""
        if self.audit_log_path.exists():
            try:
                df = pq.read_table(self.audit_log_path).to_pandas()
                self.records = [
                    AcknowledgementRecord(
                        record_id=r["record_id"],
                        alert_id=r["alert_id"],
                        incident_id=r["incident_id"],
                        user_role=r["user_role"],
                        user_name=r["user_name"],
                        status=AlertStatus(r["status"]),
                        action_taken=r.get("action_taken"),
                        dismiss_reason=r.get("dismiss_reason"),
                        comment=r.get("comment", ""),
                        created_at=r["created_at"],
                        latency_minutes=float(r.get("latency_minutes", 0.0)),
                    )
                    for r in df.to_dict(orient="records")
                ]
            except Exception:
                self.records = []

    def _persist(self) -> None:
        """Persists audit trail to parquet."""
        if not self.records:
            return
        df = pd.DataFrame([r.to_dict() for r in self.records])
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, self.audit_log_path, compression="snappy")

    def acknowledge(
        self,
        alert_id: str,
        user_role: str,
        user_name: str = "Officer",
        incident_id: str = "",
        comment: str = "",
        latency_minutes: float = 5.0,
    ) -> AcknowledgementRecord:
        """Transitions alert to ACKNOWLEDGED."""
        rec = AcknowledgementRecord(
            alert_id=alert_id,
            incident_id=incident_id,
            user_role=user_role,
            user_name=user_name,
            status=AlertStatus.ACKNOWLEDGED,
            comment=comment or "Alert receipt confirmed for active monitoring",
            latency_minutes=latency_minutes,
        )
        self.records.append(rec)
        self._persist()
        return rec

    def act(
        self,
        alert_id: str,
        user_role: str,
        action_taken: str,
        user_name: str = "Officer",
        incident_id: str = "",
        comment: str = "",
        latency_minutes: float = 15.0,
    ) -> AcknowledgementRecord:
        """Transitions alert to ACTED with recorded operational response."""
        if not action_taken:
            raise ValueError("Action taken description is required when transitioning to ACTED")

        rec = AcknowledgementRecord(
            alert_id=alert_id,
            incident_id=incident_id,
            user_role=user_role,
            user_name=user_name,
            status=AlertStatus.ACTED,
            action_taken=action_taken,
            comment=comment,
            latency_minutes=latency_minutes,
        )
        self.records.append(rec)
        self._persist()
        return rec

    def dismiss(
        self,
        alert_id: str,
        user_role: str,
        dismiss_reason: str,
        user_name: str = "Officer",
        incident_id: str = "",
        comment: str = "",
        latency_minutes: float = 10.0,
    ) -> AcknowledgementRecord:
        """Transitions alert to DISMISSED with mandatory structured justification."""
        if not dismiss_reason or dismiss_reason not in DISMISS_REASONS:
            valid_str = ", ".join(DISMISS_REASONS)
            raise ValueError(f"Valid dismiss_reason is required. Must be one of: [{valid_str}]")

        rec = AcknowledgementRecord(
            alert_id=alert_id,
            incident_id=incident_id,
            user_role=user_role,
            user_name=user_name,
            status=AlertStatus.DISMISSED,
            dismiss_reason=dismiss_reason,
            comment=comment or f"Alert dismissed: {dismiss_reason}",
            latency_minutes=latency_minutes,
        )
        self.records.append(rec)
        self._persist()
        return rec

    def get_status(self, alert_id: str) -> AlertStatus:
        """Returns current operational status of an alert."""
        matching = [r for r in self.records if r.alert_id == alert_id]
        if not matching:
            return AlertStatus.PENDING
        # Return latest status recorded
        return matching[-1].status

    def get_audit_history(self, alert_id: Optional[str] = None) -> List[AcknowledgementRecord]:
        """Returns chronological audit records."""
        if alert_id:
            return [r for r in self.records if r.alert_id == alert_id]
        return list(self.records)

    def calculate_operational_metrics(self) -> Dict[str, Any]:
        """
        Calculates real-world performance metrics:
        Acknowledgement rate, mean latency, and practical PPV.
        """
        if not self.records:
            return {
                "total_transitions": 0,
                "acted_count": 0,
                "dismissed_count": 0,
                "mean_latency_minutes": 0.0,
                "practical_ppv": 1.0,
            }

        acted = sum(1 for r in self.records if r.status == AlertStatus.ACTED)
        dismissed = sum(1 for r in self.records if r.status == AlertStatus.DISMISSED)
        latencies = [r.latency_minutes for r in self.records if r.latency_minutes > 0]
        mean_lat = round(float(sum(latencies) / len(latencies)), 1) if latencies else 0.0

        total_decisive = acted + dismissed
        ppv = round(acted / total_decisive, 3) if total_decisive > 0 else 1.0

        return {
            "total_transitions": len(self.records),
            "acted_count": acted,
            "dismissed_count": dismissed,
            "mean_latency_minutes": mean_lat,
            "practical_ppv": ppv,
        }

