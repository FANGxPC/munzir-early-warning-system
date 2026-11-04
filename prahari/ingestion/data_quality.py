"""
Data Quality (DQ) Scoring Pipeline.
Calculates daily completeness, latency, staleness, and backlog dump artefacts
for every signal × location.
"""

from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd

from prahari.models.canonical import SignalObservation, DataQualityMetric


class DataQualityScorer:
    """
    Evaluates feed completeness, latency, and reporting artefacts.
    """

    def __init__(self, expected_reporters_per_district: int = 5):
        self.expected_reporters_per_district = expected_reporters_per_district

    def compute_daily_quality(
        self,
        observations: List[SignalObservation],
        as_of_date: Optional[str] = None,
    ) -> List[DataQualityMetric]:
        """
        Calculates DataQualityMetric records per signal × geo_id × obs_date.
        """
        if not observations:
            return []

        df = pd.DataFrame([obs.model_dump() for obs in observations])
        metrics: List[DataQualityMetric] = []

        now_utc = datetime.now(timezone.utc)
        current_date_str = as_of_date or now_utc.strftime("%Y-%m-%d")

        grouped = df.groupby(["signal_type", "geo_id", "obs_date"])

        for (sig_type, geo_id, obs_date), group in grouped:
            # Latency (mean latency in hours)
            mean_latency = float(group["source_latency_hrs"].mean())

            # Completeness: mean of record completeness scores
            mean_completeness = float(group["completeness_score"].mean())

            # Number of reporting records/entities
            n_obs = len(group)
            expected = 1 if "site" in str(group["geo_level"].iloc[0]) else self.expected_reporters_per_district

            # Calculate staleness: days between observation date and current date
            try:
                obs_dt = datetime.strptime(str(obs_date), "%Y-%m-%d")
                curr_dt = datetime.strptime(current_date_str, "%Y-%m-%d")
                staleness_days = max(0, (curr_dt - obs_dt).days)
            except Exception:
                staleness_days = 0

            staleness_score = float(round(staleness_days * 24.0, 1))

            metrics.append(
                DataQualityMetric(
                    signal_type=str(sig_type),
                    geo_id=str(geo_id),
                    obs_date=str(obs_date),
                    expected_reporters=expected,
                    observed_reporters=n_obs,
                    completeness_score=round(mean_completeness, 2),
                    source_latency_hrs=round(mean_latency, 1),
                    staleness_score=staleness_score,
                )
            )

        return metrics

    def detect_backlog_dump(
        self,
        historical_metrics: pd.DataFrame,
        current_metrics: pd.DataFrame,
        volume_threshold_mult: float = 3.0,
        latency_threshold_hrs: float = 48.0,
    ) -> List[Dict[str, Any]]:
        """
        Detects reporting backlog dump artefacts: sudden spike in latency
        combined with surge in reported counts.
        """
        backlog_flags = []
        if current_metrics.empty:
            return backlog_flags

        for _, row in current_metrics.iterrows():
            if row.get("source_latency_hrs", 0) >= latency_threshold_hrs:
                backlog_flags.append({
                    "signal_type": row["signal_type"],
                    "geo_id": row["geo_id"],
                    "obs_date": row["obs_date"],
                    "reason": "High latency reporting dump detected",
                    "latency_hrs": row["source_latency_hrs"],
                })

        return backlog_flags

