"""
Data Health and Feed Freshness Service for PRAHARI.
Monitors feed ingestion freshness, completeness ratios, and source latency.
Powers the Data Health Panel view specified in Phase 5.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
from prahari.api.models import FeedHealthStatus, DataHealthResponse


class DataHealthService:
    """Monitors ingestion streams and platform data quality health."""

    def __init__(self):
        # Default baseline states for feeds
        self.feed_states: Dict[str, Dict[str, Any]] = {
            "weather": {
                "name": "Open-Meteo Weather & Thermal API",
                "freshness_minutes": 14.5,
                "completeness_pct": 99.1,
                "latency_hours": 0.25,
                "status": "HEALTHY",
                "is_active": True,
            },
            "air_quality": {
                "name": "OpenAQ Ambient Air Monitoring",
                "freshness_minutes": 22.0,
                "completeness_pct": 97.4,
                "latency_hours": 0.40,
                "status": "HEALTHY",
                "is_active": True,
            },
            "clinical": {
                "name": "MoHAP Syndromic EHR Stream",
                "freshness_minutes": 35.0,
                "completeness_pct": 95.8,
                "latency_hours": 1.20,
                "status": "HEALTHY",
                "is_active": True,
            },
            "workplace": {
                "name": "MOHRE / Employer EHS Incident Logs",
                "freshness_minutes": 48.0,
                "completeness_pct": 93.5,
                "latency_hours": 2.10,
                "status": "HEALTHY",
                "is_active": True,
            },
            "pharmacy": {
                "name": "OTC Pharmaceutical Sales Surveillance",
                "freshness_minutes": 65.0,
                "completeness_pct": 92.0,
                "latency_hours": 2.80,
                "status": "HEALTHY",
                "is_active": True,
            },
        }

    def set_feed_active(self, feed_key: str, active: bool) -> None:
        """Toggles feed state (used by interactive missing-data demo control)."""
        if feed_key in self.feed_states:
            self.feed_states[feed_key]["is_active"] = active
            if active:
                self.feed_states[feed_key]["status"] = "HEALTHY"
                self.feed_states[feed_key]["completeness_pct"] = 95.0
            else:
                self.feed_states[feed_key]["status"] = "OFFLINE"
                self.feed_states[feed_key]["completeness_pct"] = 0.0
                self.feed_states[feed_key]["freshness_minutes"] = 1440.0  # 24 hours stale

    def get_health_status(self) -> DataHealthResponse:
        """Computes live composite data quality and feed status."""
        feeds: List[FeedHealthStatus] = []
        completeness_sum = 0.0

        for key, s in self.feed_states.items():
            feeds.append(FeedHealthStatus(
                source_name=s["name"],
                feed_key=key,
                freshness_minutes=s["freshness_minutes"],
                completeness_pct=s["completeness_pct"],
                latency_hours=s["latency_hours"],
                status=s["status"],
            ))
            completeness_sum += (s["completeness_pct"] / 100.0)

        composite_dq = round(completeness_sum / len(self.feed_states), 3)
        dq_gating_triggered = composite_dq < 0.60

        overall_status = "HEALTHY"
        if dq_gating_triggered:
            overall_status = "CRITICAL_GATING_ACTIVE"
        elif composite_dq < 0.85:
            overall_status = "DEGRADED"

        return DataHealthResponse(
            composite_dq_score=composite_dq,
            overall_status=overall_status,
            dq_gating_triggered=dq_gating_triggered,
            evaluated_at=datetime.now(timezone.utc).isoformat(),
            feeds=feeds,
        )


_global_health_service: Optional[DataHealthService] = None


def get_health_service() -> DataHealthService:
    global _global_health_service
    if _global_health_service is None:
        _global_health_service = DataHealthService()
    return _global_health_service
