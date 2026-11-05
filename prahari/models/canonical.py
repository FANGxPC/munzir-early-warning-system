"""
Canonical Data Models for PRAHARI.
Defines schemas for signal observations, incident reports, injected ground truth, and DQ metrics.
"""

from datetime import datetime, timezone
from typing import Optional, Dict, Any, List
from uuid import uuid4
from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


# List of forbidden personal identifier attributes to guarantee privacy-by-architecture
FORBIDDEN_IDENTIFIER_FIELDS = {
    "patient_name", "worker_name", "employee_id", "national_id", "ssn",
    "emirates_id", "aadhaar", "phone", "email", "passport_no", "dob",
    "exact_home_address", "residential_address", "name"
}


class SignalObservation(BaseModel):
    """
    Standardized aggregate observation row landing in Bronze / Silver storage.
    Strictly aggregates by location × day × signal type.
    """
    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_type: str = Field(
        ...,
        description="Category: wbgt_max, wbgt_hours_danger, pm25, clinical_resp, clinical_gi, clinical_fever, lab_pos, absence_heat, incident"
    )
    geo_level: str = Field(
        ...,
        description="Spatial aggregation tier: site, h3_res7, district, state"
    )
    geo_id: str = Field(..., description="Unique spatial identifier (e.g. DXB-JA, SITE-JA-01)")
    location_confidence: str = Field(
        default="exact",
        description="Confidence tier: exact, inferred, district_only"
    )
    obs_date: str = Field(..., description="Observation date in YYYY-MM-DD")
    value: float = Field(..., description="Count of occurrences or physical measurement")
    denominator: Optional[float] = Field(
        default=None,
        description="Population or workforce size at risk"
    )
    ingested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    source_latency_hrs: float = Field(
        default=0.0,
        description="Lag in hours between event occurrence and system ingestion"
    )
    completeness_score: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data quality completeness ratio (0.0 to 1.0)"
    )
    suppressed_flag: bool = Field(
        default=False,
        description="True if non-zero count is below small-cell threshold (k <= 10)"
    )

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_IDENTIFIER_FIELDS:
                    raise ValueError(f"Privacy violation: Forbidden identifier field '{k}' detected!")
        return data

    @field_validator("geo_level")
    def validate_geo_level(cls, v: str) -> str:
        valid_levels = {"site", "h3_res7", "district", "state"}
        if v not in valid_levels:
            raise ValueError(f"Invalid geo_level '{v}'. Must be one of {valid_levels}")
        return v

    @field_validator("location_confidence")
    def validate_confidence(cls, v: str) -> str:
        valid = {"exact", "inferred", "district_only"}
        if v not in valid:
            raise ValueError(f"Invalid location_confidence '{v}'. Must be one of {valid}")
        return v


class IncidentReport(BaseModel):
    """
    Workplace safety incident report stripped of person-level identifiers.
    """
    incident_id: str = Field(default_factory=lambda: str(uuid4()))
    site_id: str = Field(..., description="Worksite identifier")
    district_id: str = Field(..., description="District identifier")
    obs_date: str = Field(..., description="Incident date in YYYY-MM-DD")
    narrative_sanitized: str = Field(
        ...,
        description="Free-text incident log scrubbed of all employee names and contact details"
    )
    predicted_category: str = Field(
        ...,
        description="Classification: heat, respiratory_chemical, injury, other"
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Classification confidence score"
    )
    ingested_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class InjectedEventTruth(BaseModel):
    """
    Ground truth for synthetic validation experiments and back-testing.
    """
    event_id: str = Field(default_factory=lambda: str(uuid4()))
    scenario_type: str = Field(
        ...,
        description="Scenario: heat_cluster, respiratory_surge, infectious_cluster, decoy_backlog, decoy_holiday, decoy_clinic"
    )
    target_geo_id: str = Field(..., description="Target site or district ID")
    start_date: str = Field(..., description="Start date YYYY-MM-DD")
    peak_date: str = Field(..., description="Expected peak impact date YYYY-MM-DD")
    end_date: str = Field(..., description="End date YYYY-MM-DD")
    multiplier: float = Field(default=1.5, description="Aberration multiplier over baseline")
    is_decoy: bool = Field(default=False, description="True if event is a benign artefact / decoy")
    description: Optional[str] = None


class DataQualityMetric(BaseModel):
    """
    Data quality scoring per signal × location × day.
    """
    signal_type: str
    geo_id: str
    obs_date: str
    expected_reporters: int
    observed_reporters: int
    completeness_score: float
    source_latency_hrs: float
    staleness_score: float
    computed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class SilverSignalObservation(BaseModel):
    """
    Harmonised, suppression-aware observation in Silver layer.
    Enforces privacy by architecture: no person identifiers,
    supports H3 spatial resolution, small-cell & complementary suppression,
    and rate calculations.
    """
    model_config = ConfigDict(extra="forbid")

    signal_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_type: str
    geo_level: str  # site | h3_res7 | h3_res6 | district | state
    geo_id: str     # district code, site code, h3 hex index, or state name
    h3_index: Optional[str] = None
    district_id: Optional[str] = None
    location_confidence: str = "exact"  # exact | inferred | district_only
    obs_date: str
    value: Optional[float] = None  # None/null when suppressed in external view
    raw_count: Optional[float] = None  # retained only for internal calculation, not exported
    rate_per_1000: Optional[float] = None
    denominator: Optional[float] = None  # population or workforce at risk
    suppressed_flag: bool = False
    suppression_type: str = "none"  # none | primary | complementary | min_group_size
    completeness_score: float = 1.0
    source_latency_hrs: float = 0.0
    ingested_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_IDENTIFIER_FIELDS:
                    raise ValueError(f"Privacy violation: Forbidden identifier field '{k}' detected in Silver observation!")
        return data


class DifferentialPrivacyRelease(BaseModel):
    """
    Differential Privacy release record generated with calibrated noise (OpenDP).
    """
    release_id: str = Field(default_factory=lambda: str(uuid4()))
    signal_type: str
    geo_level: str
    geo_id: str
    obs_date: str
    true_count: float
    noisy_count: float
    epsilon: float
    mechanism: str = "laplace"
    released_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


class WorkplaceRateView(BaseModel):
    """
    Workplace safety and health aggregate rate view.
    Enforces minimum cohort size (N >= 50) and rate-only presentation.
    """
    model_config = ConfigDict(extra="forbid")

    site_id: str
    district_id: str
    obs_date: str
    signal_type: str
    workforce_size: int
    rate_per_1000: Optional[float] = None
    is_eligible: bool = True
    disclaimer: str = "Aggregate data — not for individual employment or disciplinary decisions."

    @model_validator(mode="before")
    @classmethod
    def check_forbidden_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            for k in data.keys():
                if k.lower() in FORBIDDEN_IDENTIFIER_FIELDS:
                    raise ValueError(f"Privacy violation: Forbidden identifier field '{k}' in workplace rate view!")
        return data
