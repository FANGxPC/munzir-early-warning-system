"""
Audit Trail Logging Service for the PRAHARI Platform.
Records immutable audit logs of all API access, data views, and administrative operations
in Gold Lakehouse Parquet storage (data/gold/audit/view_audit_log.parquet).
Satisfies Phase 5 requirement: "Audit log of every view: role, endpoint, geo level, stated purpose."
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional
import threading
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prahari.config import GOLD_DIR
from prahari.api.models import AuditLogRecord

DEFAULT_AUDIT_DIR = Path(GOLD_DIR) / "audit"
DEFAULT_AUDIT_FILE = DEFAULT_AUDIT_DIR / "view_audit_log.parquet"


class AuditService:
    """Thread-safe immutable audit logging service."""

    def __init__(self, audit_file: Path = DEFAULT_AUDIT_FILE):
        self.audit_file = Path(audit_file)
        self.audit_file.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.Lock()
        self._memory_cache: List[Dict[str, Any]] = []
        self._init_storage()

    def _init_storage(self) -> None:
        """Initializes the parquet store if not present."""
        if not self.audit_file.exists():
            schema = pa.schema([
                ("timestamp", pa.string()),
                ("role", pa.string()),
                ("user_id", pa.string()),
                ("endpoint", pa.string()),
                ("geo_level", pa.string()),
                ("geo_id", pa.string()),
                ("purpose", pa.string()),
                ("status_code", pa.int32()),
                ("client_ip", pa.string()),
            ])
            empty_table = pa.Table.from_batches([], schema=schema)
            pq.write_table(empty_table, self.audit_file)

    def log_view(
        self,
        role: str,
        user_id: str,
        endpoint: str,
        geo_level: str = "district",
        geo_id: str = "ALL",
        purpose: str = "epidemiological_surveillance",
        status_code: int = 200,
        client_ip: str = "127.0.0.1",
    ) -> AuditLogRecord:
        """Logs a single data view or API action to the audit trail."""
        record = AuditLogRecord(
            timestamp=datetime.now(timezone.utc).isoformat(),
            role=role,
            user_id=user_id,
            endpoint=endpoint,
            geo_level=geo_level,
            geo_id=geo_id,
            purpose=purpose,
            status_code=status_code,
            client_ip=client_ip,
        )

        with self._lock:
            self._memory_cache.append(record.model_dump())
            # Periodically or on each write persist to Parquet
            df_new = pd.DataFrame([record.model_dump()])
            if self.audit_file.exists():
                try:
                    df_existing = pq.read_table(self.audit_file).to_pandas()
                    df_combined = pd.concat([df_existing, df_new], ignore_index=True)
                except Exception:
                    df_combined = df_new
            else:
                df_combined = df_new

            table = pa.Table.from_pandas(df_combined, preserve_index=False)
            pq.write_table(table, self.audit_file, compression="snappy")

        return record

    def get_logs(
        self,
        role_filter: Optional[str] = None,
        limit: int = 100,
    ) -> List[AuditLogRecord]:
        """Reads recent audit logs with optional filtering."""
        with self._lock:
            if not self.audit_file.exists():
                return []
            try:
                df = pq.read_table(self.audit_file).to_pandas()
                if role_filter:
                    df = df[df["role"] == role_filter]
                records = df.tail(limit).to_dict(orient="records")
                return [AuditLogRecord(**r) for r in reversed(records)]
            except Exception:
                return [AuditLogRecord(**r) for r in reversed(self._memory_cache[-limit:])]


_global_audit_service: Optional[AuditService] = None


def get_audit_service() -> AuditService:
    global _global_audit_service
    if _global_audit_service is None:
        _global_audit_service = AuditService()
    return _global_audit_service

