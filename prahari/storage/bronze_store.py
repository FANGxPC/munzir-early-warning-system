"""
Bronze Lakehouse Parquet Storage Layer.
Provides fast partitioned writes and reads for PRAHARI signal observations,
incident reports, and ground truth records. Supports local file system and
pluggable Azure Blob Storage sync.
"""

from pathlib import Path
from typing import List, Optional, Union, Dict, Any
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prahari.config import BRONZE_DIR
from prahari.models.canonical import (
    SignalObservation,
    IncidentReport,
    InjectedEventTruth,
    DataQualityMetric,
)


class BronzeStore:
    """
    Bronze layer parquet storage manager.
    Partitions observations by signal_type and date.
    """

    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir or BRONZE_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.obs_dir = self.base_dir / "observations"
        self.incidents_dir = self.base_dir / "incidents"
        self.truth_dir = self.base_dir / "ground_truth"
        self.dq_dir = self.base_dir / "data_quality"

        for d in [self.obs_dir, self.incidents_dir, self.truth_dir, self.dq_dir]:
            d.mkdir(parents=True, exist_ok=True)

    def write_observations(self, observations: List[SignalObservation]) -> int:
        """
        Write signal observations partitioned by signal_type and obs_date.
        Returns count of records written.
        """
        if not observations:
            return 0

        # Convert to dicts
        records = [obs.model_dump() for obs in observations]
        df = pd.DataFrame(records)

        # Ensure consistent dtypes
        df["value"] = df["value"].astype(float)
        df["source_latency_hrs"] = df["source_latency_hrs"].astype(float)
        df["completeness_score"] = df["completeness_score"].astype(float)
        df["suppressed_flag"] = df["suppressed_flag"].astype(bool)

        # Partition by signal_type and obs_date
        total_written = 0
        grouped = df.groupby(["signal_type", "obs_date"])

        for (sig_type, obs_date), group in grouped:
            part_dir = self.obs_dir / str(sig_type)
            part_dir.mkdir(parents=True, exist_ok=True)
            file_path = part_dir / f"{obs_date}.parquet"

            table = pa.Table.from_pandas(group, preserve_index=False)

            # Atomic write via temporary file
            temp_path = file_path.with_suffix(".tmp.parquet")
            pq.write_table(table, temp_path, compression="snappy")
            temp_path.replace(file_path)
            total_written += len(group)

        return total_written

    def read_observations(
        self,
        signal_types: Optional[List[str]] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        geo_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """
        Query observations across partitions with optional filters.
        """
        if not self.obs_dir.exists():
            return pd.DataFrame()

        target_signals = signal_types or [d.name for d in self.obs_dir.iterdir() if d.is_dir()]
        dfs = []

        for sig in target_signals:
            sig_dir = self.obs_dir / sig
            if not sig_dir.exists():
                continue

            for file_path in sig_dir.glob("*.parquet"):
                # Fast date filtering from filename (format: YYYY-MM-DD.parquet)
                date_str = file_path.stem
                if start_date and date_str < start_date:
                    continue
                if end_date and date_str > end_date:
                    continue

                table = pq.read_table(file_path)
                df = table.to_pandas()
                if geo_id:
                    df = df[df["geo_id"] == geo_id]
                if not df.empty:
                    dfs.append(df)

        if not dfs:
            return pd.DataFrame()

        result = pd.concat(dfs, ignore_index=True)
        result.sort_values(by=["obs_date", "signal_type", "geo_id"], inplace=True)
        return result

    def write_incidents(self, incidents: List[IncidentReport]) -> int:
        """Store incident reports in bronze storage partitioned by date."""
        if not incidents:
            return 0
        df = pd.DataFrame([inc.model_dump() for inc in incidents])
        grouped = df.groupby("obs_date")
        total = 0
        for obs_date, group in grouped:
            file_path = self.incidents_dir / f"incidents_{obs_date}.parquet"
            table = pa.Table.from_pandas(group, preserve_index=False)
            pq.write_table(table, file_path, compression="snappy")
            total += len(group)
        return total

    def read_incidents(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        site_id: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read incident reports with optional filters."""
        dfs = []
        for file_path in self.incidents_dir.glob("incidents_*.parquet"):
            date_str = file_path.stem.replace("incidents_", "")
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            table = pq.read_table(file_path)
            df = table.to_pandas()
            if site_id:
                df = df[df["site_id"] == site_id]
            if not df.empty:
                dfs.append(df)
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    def write_ground_truth(self, events: List[InjectedEventTruth]) -> int:
        """Store injected event ground truth for validation and scoring."""
        if not events:
            return 0
        df = pd.DataFrame([e.model_dump() for e in events])
        file_path = self.truth_dir / "injected_events.parquet"
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, file_path, compression="snappy")
        return len(events)

    def read_ground_truth(self) -> pd.DataFrame:
        """Read ground truth injected event catalog."""
        file_path = self.truth_dir / "injected_events.parquet"
        if not file_path.exists():
            return pd.DataFrame()
        return pq.read_table(file_path).to_pandas()

    def write_data_quality(self, metrics: List[DataQualityMetric]) -> int:
        """Store data quality metrics."""
        if not metrics:
            return 0
        df = pd.DataFrame([m.model_dump() for m in metrics])
        grouped = df.groupby("obs_date")
        total = 0
        for obs_date, group in grouped:
            file_path = self.dq_dir / f"dq_{obs_date}.parquet"
            table = pa.Table.from_pandas(group, preserve_index=False)
            pq.write_table(table, file_path, compression="snappy")
            total += len(group)
        return total

    def read_data_quality(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> pd.DataFrame:
        """Read data quality metrics."""
        dfs = []
        for file_path in self.dq_dir.glob("dq_*.parquet"):
            date_str = file_path.stem.replace("dq_", "")
            if start_date and date_str < start_date:
                continue
            if end_date and date_str > end_date:
                continue
            table = pq.read_table(file_path)
            dfs.append(table.to_pandas())
        if not dfs:
            return pd.DataFrame()
        return pd.concat(dfs, ignore_index=True)

    def get_summary_stats(self) -> Dict[str, Any]:
        """Return dataset row counts and date spans across bronze tables."""
        total_obs = 0
        signals_found = set()
        dates_found = set()

        if self.obs_dir.exists():
            for sig_dir in self.obs_dir.iterdir():
                if sig_dir.is_dir():
                    signals_found.add(sig_dir.name)
                    for f in sig_dir.glob("*.parquet"):
                        dates_found.add(f.stem)
                        # Read metadata without loading whole file
                        meta = pq.read_metadata(f)
                        total_obs += meta.num_rows

        incidents_count = 0
        if self.incidents_dir.exists():
            for f in self.incidents_dir.glob("*.parquet"):
                meta = pq.read_metadata(f)
                incidents_count += meta.num_rows

        truth_count = 0
        truth_file = self.truth_dir / "injected_events.parquet"
        if truth_file.exists():
            truth_count = pq.read_metadata(truth_file).num_rows

        return {
            "total_observations": total_obs,
            "unique_signals": sorted(list(signals_found)),
            "date_count": len(dates_found),
            "min_date": min(dates_found) if dates_found else None,
            "max_date": max(dates_found) if dates_found else None,
            "total_incidents": incidents_count,
            "total_ground_truth_events": truth_count,
        }

