"""
Munzir 'Exposure-to-Seeking' Spatio-Temporal Deconvolution Engine (Phase 15).
Solves the fundamental geolocation ambiguity in workforce epidemiology by
mathematically back-projecting delayed residential clinic visits onto their
true upstream industrial exposure locus.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class SpatialLocation:
    """Geographic point with identifier and district metadata."""
    location_id: str
    name: str
    latitude: float
    longitude: float
    district: str
    h3_res7: str
    location_type: str  # "industrial_worksite", "residential_camp", "clinical_facility"


@dataclass
class ClinicalSeekingCluster:
    """Observed cluster of clinical presentations at a clinic."""
    clinic_id: str
    clinic_name: str
    district: str
    latitude: float
    longitude: float
    seeking_timestamp: str  # ISO format
    case_count: int
    primary_symptom: str = "heat_exhaustion"


@dataclass
class DeconvolvedSourceCandidate:
    """Candidate upstream exposure site with attributed posterior probability."""
    site_id: str
    site_name: str
    district: str
    latitude: float
    longitude: float
    posterior_probability: float  # 0.0 to 1.0
    attributed_cases: float
    mean_exposure_wbgt: float
    estimated_exposure_window_utc: str
    transit_flow_weight: float
    incubation_lag_hours: float


@dataclass
class SpatialUncertaintyEllipse:
    """Geometric parameters for rendering spatial uncertainty bounds on maps."""
    center_latitude: float
    center_longitude: float
    semi_major_axis_km: float
    semi_minor_axis_km: float
    angle_degrees: float
    confidence_level: float = 0.95


@dataclass
class DeconvolutionResult:
    """Comprehensive result of spatio-temporal back-projection."""
    seeking_cluster: ClinicalSeekingCluster
    candidates: List[DeconvolvedSourceCandidate]
    primary_source_site_id: str
    spatial_resolution: str
    confidence_ellipse: SpatialUncertaintyEllipse
    explanation: str


# Dubai Known Reference Locations
DUBAI_INDUSTRIAL_SITES = {
    "SITE-JA-01": SpatialLocation(
        location_id="SITE-JA-01",
        name="Jebel Ali Deepwater Port Terminal",
        latitude=24.9857,
        longitude=55.0872,
        district="Jebel Ali",
        h3_res7="87439404effffff",
        location_type="industrial_worksite",
    ),
    "SITE-AQ-01": SpatialLocation(
        location_id="SITE-AQ-01",
        name="Al Quoz Structural Steel Yard",
        latitude=25.1324,
        longitude=55.2341,
        district="Al Quoz",
        h3_res7="87439400affffff",
        location_type="industrial_worksite",
    ),
    "SITE-DS-01": SpatialLocation(
        location_id="SITE-DS-01",
        name="Dubai South Mega-Logistics Park",
        latitude=24.8962,
        longitude=55.1583,
        district="Dubai South",
        h3_res7="87439412bffffff",
        location_type="industrial_worksite",
    ),
    "SITE-RAK-01": SpatialLocation(
        location_id="SITE-RAK-01",
        name="Ras Al Khor Heavy Concrete Hub",
        latitude=25.1820,
        longitude=55.3390,
        district="Ras Al Khor",
        h3_res7="874394025ffffff",
        location_type="industrial_worksite",
    ),
}

# Empirical Labor Commute & Accommodation Connectivity Matrix
# Maps Industrial Worksite -> Clinic District Seeking Probability
TRANSIT_CONNECTIVITY_MATRIX: Dict[str, Dict[str, float]] = {
    "SITE-JA-01": {
        "Jebel Ali": 0.40,
        "Muhaisnah": 0.35,
        "Deira": 0.15,
        "Bur Dubai": 0.10,
    },
    "SITE-AQ-01": {
        "Al Quoz": 0.45,
        "Muhaisnah": 0.30,
        "Deira": 0.15,
        "Bur Dubai": 0.10,
    },
    "SITE-DS-01": {
        "Dubai South": 0.50,
        "Jebel Ali": 0.30,
        "Muhaisnah": 0.20,
    },
    "SITE-RAK-01": {
        "Ras Al Khor": 0.35,
        "Deira": 0.35,
        "Muhaisnah": 0.30,
    },
}


def weibull_incubation_density(lag_hours: float, shape: float = 3.0, scale: float = 7.0) -> float:
    """
    Evaluates probability density of incubation lag between occupational thermal/particulate
    exposure and emergency healthcare seeking using a 2-parameter Weibull distribution.
    Mean lag ~ 6.2 hours (typical shift-end commute + delayed symptomatic onset).
    """
    if lag_hours <= 0:
        return 0.0
    x_over_scale = lag_hours / scale
    density = (shape / scale) * (x_over_scale ** (shape - 1.0)) * math.exp(-(x_over_scale ** shape))
    return density


def compute_haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Computes great-circle distance between two GPS coordinates in kilometers."""
    r = 6371.0  # Earth radius in km
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def deconvolve_seeking_cluster(
    cluster: ClinicalSeekingCluster,
    site_wbgt_series: Dict[str, float],  # site_id -> exposure window mean WBGT
    candidate_sites: Optional[Dict[str, SpatialLocation]] = None,
    mean_lag_hours: float = 6.0,
) -> DeconvolutionResult:
    """
    Deconvolves a clinical seeking cluster at a healthcare facility into likely upstream exposure sites.
    Combines transit connectivity prior, Weibull lag likelihood, and microclimate WBGT intensity.
    """
    if candidate_sites is None:
        candidate_sites = DUBAI_INDUSTRIAL_SITES

    unnormalized_scores: Dict[str, float] = {}
    candidate_details: Dict[str, Dict[str, Any]] = {}

    lag_likelihood = weibull_incubation_density(mean_lag_hours)

    for site_id, site in candidate_sites.items():
        # 1. Transit connectivity prior: how likely workers at this site seek care in cluster.district
        transit_priors = TRANSIT_CONNECTIVITY_MATRIX.get(site_id, {})
        transit_weight = transit_priors.get(cluster.district, 0.05)  # default small epsilon

        # 2. Environmental exposure intensity: WBGT excess above 30°C threshold
        mean_wbgt = site_wbgt_series.get(site_id, 30.0)
        # Exposure multiplier: exponential hazard for WBGT > 30°C
        thermal_hazard = math.exp(max(0.0, mean_wbgt - 30.0) * 0.4)

        # 3. Spatial friction penalty (distance from site to clinic)
        dist_km = compute_haversine_distance_km(site.latitude, site.longitude, cluster.latitude, cluster.longitude)
        spatial_friction = math.exp(-dist_km / 35.0)  # 35km typical urban commute scale

        # Combined unnormalized posterior density
        score = transit_weight * lag_likelihood * thermal_hazard * spatial_friction
        unnormalized_scores[site_id] = score
        candidate_details[site_id] = {
            "site": site,
            "mean_wbgt": mean_wbgt,
            "transit_weight": transit_weight,
            "distance_km": dist_km,
        }

    total_score = sum(unnormalized_scores.values()) or 1.0

    candidates_list: List[DeconvolvedSourceCandidate] = []
    # Calculate estimated exposure window (seeking_time minus lag_hours)
    seeking_dt = datetime.fromisoformat(cluster.seeking_timestamp.replace("Z", "+00:00"))
    exp_start = (seeking_dt - timedelta(hours=mean_lag_hours + 2.0)).strftime("%H:%M")
    exp_end = (seeking_dt - timedelta(hours=mean_lag_hours - 2.0)).strftime("%H:%M UTC")
    exp_window_str = f"{exp_start} - {exp_end}"

    for site_id, score in unnormalized_scores.items():
        post_p = score / total_score
        details = candidate_details[site_id]
        site = details["site"]
        attributed_cases = round(cluster.case_count * post_p, 1)

        candidates_list.append(
            DeconvolvedSourceCandidate(
                site_id=site_id,
                site_name=site.name,
                district=site.district,
                latitude=site.latitude,
                longitude=site.longitude,
                posterior_probability=round(post_p, 3),
                attributed_cases=attributed_cases,
                mean_exposure_wbgt=round(details["mean_wbgt"], 1),
                estimated_exposure_window_utc=exp_window_str,
                transit_flow_weight=round(details["transit_weight"], 2),
                incubation_lag_hours=mean_lag_hours,
            )
        )

    # Sort candidates by posterior probability descending
    candidates_list.sort(key=lambda c: c.posterior_probability, reverse=True)
    primary = candidates_list[0] if candidates_list else None
    primary_id = primary.site_id if primary else "UNKNOWN"

    # Compute 95% spatial uncertainty ellipse around the weighted centroid
    weighted_lat = sum(c.latitude * c.posterior_probability for c in candidates_list)
    weighted_lon = sum(c.longitude * c.posterior_probability for c in candidates_list)
    variance_lat = sum(c.posterior_probability * (c.latitude - weighted_lat) ** 2 for c in candidates_list)
    variance_lon = sum(c.posterior_probability * (c.longitude - weighted_lon) ** 2 for c in candidates_list)

    semi_major = max(2.5, math.sqrt(variance_lat) * 111.0 * 2.0)  # km (approx 2 sigma)
    semi_minor = max(1.5, math.sqrt(variance_lon) * 100.0 * 2.0)

    ellipse = SpatialUncertaintyEllipse(
        center_latitude=round(weighted_lat, 4),
        center_longitude=round(weighted_lon, 4),
        semi_major_axis_km=round(semi_major, 2),
        semi_minor_axis_km=round(semi_minor, 2),
        angle_degrees=35.0,  # Alignment with primary Dubai coastal/industrial corridor
        confidence_level=0.95,
    )

    explanation = (
        f"Deconvolved {cluster.case_count} presentations at {cluster.clinic_name} ({cluster.district}). "
        f"Upstream Bayesian back-projection identifies {primary.site_name} ({primary.district}) as the primary "
        f"exposure origin (Posterior Probability: {primary.posterior_probability * 100:.1f}%) with estimated "
        f"exposure {mean_lag_hours:.1f} hours prior during peak WBGT {primary.mean_exposure_wbgt}°C."
    )

    return DeconvolutionResult(
        seeking_cluster=cluster,
        candidates=candidates_list,
        primary_source_site_id=primary_id,
        spatial_resolution="H3 Resolution 7 (~5.16 km²)",
        confidence_ellipse=ellipse,
        explanation=explanation,
    )

