"""
Pydantic Request and Response Schemas for the PRAHARI API.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from prahari.api.rbac import EntraRole


class RoleInfo(BaseModel):
    role: str
    display_name: str
    description: str
    permitted_geo_levels: List[str]
    permitted_signals: List[str]
    can_view_audit_logs: bool
    can_acknowledge_alerts: bool


class RolesListResponse(BaseModel):
    current_role: str
    user_id: str
    organization: str
    available_roles: List[RoleInfo]


class GeoFeature(BaseModel):
    geo_id: str
    geo_name: str
    geo_level: str  # district, site, h3_res7
    lat: float
    lon: float
    risk_tier: str  # normal, watch, warning, alert
    calibrated_prob: float
    location_confidence: str  # exact, district_only
    hatch_pattern: bool = False  # True if district_only requires diagonal hatching
    primary_syndrome: Optional[str] = None
    h3_index: Optional[str] = None
    population: Optional[int] = None


class ClusterBoundary(BaseModel):
    cluster_id: str
    centroid_lat: float
    centroid_lon: float
    radius_km: float
    relative_risk: float
    p_value: float
    syndrome: str
    coordinates: List[List[float]] = []  # polygon vertices for map rendering


class MapLayersResponse(BaseModel):
    date: str
    role_view: str
    total_locations: int
    features: List[GeoFeature]
    clusters: List[ClusterBoundary]
    privacy_notice: Optional[str] = None


class AlertInboxItem(BaseModel):
    alert_id: str
    alert_tier: str  # watch, warning, alert
    syndrome: str
    geo_id: str
    geo_name: str
    timestamp: str
    calibrated_probability: float
    conformal_interval: List[float]  # [lower, upper]
    dq_score: float
    dq_badge: str  # NORMAL, EXCELLENT, DEGRADED, LOW_COMPLETENESS
    primary_owner: str
    status: str  # PENDING, ACKNOWLEDGED, ACTED, DISMISSED
    can_acknowledge: bool = True
    dismissal_reason: Optional[str] = None


class AlertInboxResponse(BaseModel):
    date: str
    total_alerts: int
    alerts: List[AlertInboxItem]
    role: str
    operational_ppv: Optional[float] = None


class AcknowledgeRequest(BaseModel):
    action: str = Field(..., description="ACKNOWLEDGED, ACTED, or DISMISSED")
    comment: Optional[str] = Field(default="")
    dismissal_reason: Optional[str] = Field(
        default=None,
        description="Mandatory if action is DISMISSED: benign_local_event, data_artefact_backlog, already_managed_duplicate, false_positive_noise, other"
    )


class AcknowledgeResponse(BaseModel):
    alert_id: str
    status: str
    updated_at: str
    user_id: str
    message: str


class WorkplaceRateView(BaseModel):
    site_id: str
    site_name: str
    district_id: str
    date: str
    workforce_size: int
    absence_rate_per_1000: Optional[float] = None
    heat_incident_rate_per_1000: Optional[float] = None
    is_suppressed: bool = False
    suppression_reason: Optional[str] = None
    wbgt_max: float
    wbgt_hours_caution: float
    wbgt_hours_danger: float
    work_rest_recommendation: str
    statutory_banner: str = "Aggregate data — not for individual employment or disciplinary decisions."


class FeedHealthStatus(BaseModel):
    source_name: str
    feed_key: str
    freshness_minutes: float
    completeness_pct: float
    latency_hours: float
    status: str  # HEALTHY, DEGRADED, OFFLINE


class DataHealthResponse(BaseModel):
    composite_dq_score: float
    overall_status: str
    dq_gating_triggered: bool
    evaluated_at: str
    feeds: List[FeedHealthStatus]


class DemoToggleRequest(BaseModel):
    feed: str = Field(..., description="clinical, weather, air_quality, workplace, or pharmacy")
    enabled: bool = Field(..., description="Toggle status: true for online, false for disabled/outage")


class DemoToggleResponse(BaseModel):
    toggled_feed: str
    is_enabled: bool
    before_composite_dq: float
    after_composite_dq: float
    before_conformal_interval: List[float]
    after_conformal_interval: List[float]
    alert_impact: str
    message: str


class AuditLogRecord(BaseModel):
    timestamp: str
    role: str
    user_id: str
    endpoint: str
    geo_level: str
    geo_id: str
    purpose: str
    status_code: int
    client_ip: str


class AuditLogsResponse(BaseModel):
    total_records: int
    records: List[AuditLogRecord]


class CopilotChatRequest(BaseModel):
    query: str
    site_id: str = "SITE-JA-01"
    target_date: str = "2025-08-20"
    history: Optional[List[Dict[str, str]]] = None


class VoiceIntercomRequest(BaseModel):
    spoken_transcript: Optional[str] = None
    transcript: Optional[str] = None
    audio_transcript: Optional[str] = None
    speech_transcript: Optional[str] = None
    worker_id: Optional[str] = None
    site_id: str = "SITE-JA-01"
    audio_channel: str = "radio_handset_ch4"
    language_hint: Optional[str] = None

    def get_transcript(self) -> str:
        text = self.spoken_transcript or self.transcript or self.audio_transcript or self.speech_transcript
        return text or ""


class PolicyStudioRequest(BaseModel):
    scenario_name: str = "MOHRE Summer Emergency Directive"
    cohort_size: int = 50000
    midday_ban_start_hour: float = 12.0
    midday_ban_end_hour: float = 15.0
    wbgt_threshold_mandatory_ors: float = 31.0
    max_distance_to_cooling_shelter_m: float = 75.0
    mandatory_bedside_usg_screening: bool = True
    monte_carlo_draws: int = 1000


class ActionConfirmRequest(BaseModel):
    action_type: str = "shade_break"
    site_id: str = "SITE-JA-01"
    foreman_name: str = "Tariq Mansoor"
    notes: Optional[str] = None
    affected_workers: int = 15
    timestamp: Optional[str] = None




