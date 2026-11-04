"""Tests for Data Quality scoring and backlog artefact detection."""

from prahari.models.canonical import SignalObservation
from prahari.ingestion.data_quality import DataQualityScorer


def test_data_quality_scoring():
    scorer = DataQualityScorer(expected_reporters_per_district=5)

    observations = [
        SignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=25.0,
            source_latency_hrs=18.5,
            completeness_score=0.85,
        ),
        SignalObservation(
            signal_type="wbgt_max",
            geo_level="site",
            geo_id="SITE-JA-01",
            obs_date="2026-06-01",
            value=31.2,
            source_latency_hrs=1.2,
            completeness_score=1.0,
        ),
    ]

    metrics = scorer.compute_daily_quality(observations, as_of_date="2026-06-02")
    assert len(metrics) == 2

    metric_map = {m.signal_type: m for m in metrics}
    assert "clinical_resp" in metric_map
    assert metric_map["clinical_resp"].source_latency_hrs == 18.5
    assert metric_map["clinical_resp"].completeness_score == 0.85
    assert metric_map["clinical_resp"].staleness_score == 24.0  # 1 day lag * 24h

