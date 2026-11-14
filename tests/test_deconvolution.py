"""
Tests for Phase 15: 'Exposure-to-Seeking' Spatio-Temporal Deconvolution Engine.
"""

import math
from prahari.spatial.deconvolution import (
    ClinicalSeekingCluster,
    compute_haversine_distance_km,
    deconvolve_seeking_cluster,
    weibull_incubation_density,
)


def test_weibull_incubation_density():
    """Verifies that the Weibull lag density exhibits realistic physiological kinetics."""
    # At lag <= 0, density should be 0.0
    assert weibull_incubation_density(0.0) == 0.0
    assert weibull_incubation_density(-2.0) == 0.0

    # Peak should occur around 5-7 hours (typical acute occupational thermal exhaustion)
    d2 = weibull_incubation_density(2.0)
    d6 = weibull_incubation_density(6.0)
    d18 = weibull_incubation_density(18.0)

    assert d6 > d2
    assert d6 > d18


def test_haversine_distance():
    """Verifies GPS distance calculation between known landmarks."""
    # Jebel Ali Port (24.9857, 55.0872) to Al Quoz (25.1324, 55.2341) is ~22-25 km
    dist = compute_haversine_distance_km(24.9857, 55.0872, 25.1324, 55.2341)
    assert 20.0 <= dist <= 26.0


def test_deconvolution_normalization_and_attribution():
    """Verifies that posterior probabilities sum to 1.0 and case attribution is conserved."""
    cluster = ClinicalSeekingCluster(
        clinic_id="CLN-MUH-01",
        clinic_name="Muhaisnah Primary Health Centre",
        district="Muhaisnah",
        latitude=25.2680,
        longitude=55.3920,
        seeking_timestamp="2025-08-18T19:30:00Z",
        case_count=45,
        primary_symptom="heat_exhaustion",
    )

    # Elevated WBGT at Jebel Ali Port (34.5°C) vs normal elsewhere (29.5°C)
    wbgt_series = {
        "SITE-JA-01": 34.5,
        "SITE-AQ-01": 30.0,
        "SITE-DS-01": 29.5,
        "SITE-RAK-01": 29.0,
    }

    result = deconvolve_seeking_cluster(cluster, wbgt_series, mean_lag_hours=6.5)

    # Posterior probabilities sum to 1.0
    total_p = sum(c.posterior_probability for c in result.candidates)
    assert 0.99 <= total_p <= 1.01

    # Primary source correctly identifies Jebel Ali Port due to extreme heat excess + commute link
    assert result.primary_source_site_id == "SITE-JA-01"
    primary_candidate = result.candidates[0]
    assert primary_candidate.site_id == "SITE-JA-01"
    assert primary_candidate.posterior_probability > 0.50

    # Attributed cases conserve total (allowing for rounding)
    total_attributed = sum(c.attributed_cases for c in result.candidates)
    assert abs(total_attributed - cluster.case_count) <= 1.0


def test_deconvolution_uncertainty_ellipse():
    """Verifies the geometric integrity of the 95% spatial confidence ellipse."""
    cluster = ClinicalSeekingCluster(
        clinic_id="CLN-DEI-01",
        clinic_name="Deira Specialty Clinic",
        district="Deira",
        latitude=25.2711,
        longitude=55.3075,
        seeking_timestamp="2025-08-18T20:00:00Z",
        case_count=30,
        primary_symptom="heat_exhaustion",
    )

    wbgt_series = {
        "SITE-JA-01": 33.0,
        "SITE-AQ-01": 33.8,  # Al Quoz higher
        "SITE-DS-01": 29.0,
        "SITE-RAK-01": 31.0,
    }

    result = deconvolve_seeking_cluster(cluster, wbgt_series, mean_lag_hours=5.5)
    ellipse = result.confidence_ellipse

    assert ellipse.semi_major_axis_km > 0.0
    assert ellipse.semi_minor_axis_km > 0.0
    assert ellipse.confidence_level == 0.95
    assert 24.0 <= ellipse.center_latitude <= 26.0
    assert 54.0 <= ellipse.center_longitude <= 56.0


def test_deconvolution_explanation_integrity():
    """Ensures human-readable narrative contains specific names, percentages, and timestamps."""
    cluster = ClinicalSeekingCluster(
        clinic_id="CLN-JA-01",
        clinic_name="Jebel Ali Port Clinic",
        district="Jebel Ali",
        latitude=24.9900,
        longitude=55.0900,
        seeking_timestamp="2025-08-18T18:00:00Z",
        case_count=20,
    )

    wbgt_series = {"SITE-JA-01": 34.0, "SITE-AQ-01": 30.0}
    result = deconvolve_seeking_cluster(cluster, wbgt_series)

    assert "Jebel Ali" in result.explanation
    assert "%" in result.explanation
    assert "WBGT" in result.explanation

