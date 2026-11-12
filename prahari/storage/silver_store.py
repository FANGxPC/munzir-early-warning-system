"""
Silver Layer Storage Manager (silver.signal_observation).
Provides partitioned Parquet storage and optional PostgreSQL/PostGIS connection
for harmonised, suppression-aware, spatial-indexed observations.
"""

import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prahari.config import SILVER_DIR
from prahari.models.canonical import SilverSignalObservation


class SilverStore:
    """
    Silver Lakehouse Storage Manager.
    Persists harmonised observations with H3 spatial indexing and suppression metadata.
    """

    def __init__(self, base_dir: Optional[Path] = None, postgres_url: Optional[str] = None):
        self.base_dir = Path(base_dir or SILVER_DIR)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.obs_dir = self.base_dir / "observations"
        self.obs_dir.mkdir(parents=True, exist_ok=True)
        self.postgres_url = postgres_url or os.getenv("POSTGRES_URL")

    def write_observations(self, observations: List[SilverSignalObservation]) -> int:
        """
        Persists silver observations partitioned by signal_type and obs_date.
        """
        if not observations:
            return 0

        records = [obs.model_dump() for obs in observations]
        df = pd.DataFrame(records)

        total_written = 0
        grouped = df.groupby(["signal_type", "obs_date"])

        for (sig_type, obs_date), group in grouped:
            part_dir = self.obs_dir / str(sig_type)
            part_dir.mkdir(parents=True, exist_ok=True)
            file_path = part_dir / f"{obs_date}.parquet"

            table = pa.Table.from_pandas(group, preserve_index=False)
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
        geo_level: Optional[str] = None,
        geo_id: Optional[str] = None,
        h3_index: Optional[str] = None,
        external_view: bool = False,
    ) -> pd.DataFrame:
        """
        Query silver observations with spatial and temporal filters.
        If external_view=True, suppressed values are masked as None/NaN.
        """
        if not self.obs_dir.exists():
            return pd.DataFrame()

        target_signals = signal_types or [d.name for d in self.obs_dir.iterdir() if d.is_dir()]
        dfs = []

        # High-performance date bounding: direct partition resolution instead of scanning thousands of disk files
        target_dates = None
        if start_date and end_date:
            try:
                d_start = datetime.strptime(start_date, "%Y-%m-%d")
                d_end = datetime.strptime(end_date, "%Y-%m-%d")
                delta_days = (d_end - d_start).days
                if 0 <= delta_days <= 366:
                    target_dates = [
                        (d_start + timedelta(days=i)).strftime("%Y-%m-%d")
                        for i in range(delta_days + 1)
                    ]
            except Exception:
                target_dates = None

        for sig in target_signals:
            sig_dir = self.obs_dir / sig
            if not sig_dir.exists():
                continue

            if target_dates is not None:
                candidate_files = [sig_dir / f"{d}.parquet" for d in target_dates]
                candidate_files = [f for f in candidate_files if f.exists()]
            else:
                candidate_files = [
                    file_path for file_path in sig_dir.glob("*.parquet")
                    if not file_path.name.endswith(".tmp.parquet")
                    and (not start_date or file_path.stem >= start_date)
                    and (not end_date or file_path.stem <= end_date)
                ]

            for file_path in candidate_files:
                table = pq.read_table(file_path)
                df = table.to_pandas()

                if geo_level:
                    df = df[df["geo_level"] == geo_level]
                if geo_id:
                    df = df[df["geo_id"] == geo_id]
                if h3_index:
                    df = df[df["h3_index"] == h3_index]

                if not df.empty:
                    dfs.append(df)

        clean_dfs = [d.dropna(how="all", axis=1) for d in dfs if not d.empty]
        if not clean_dfs:
            return pd.DataFrame()

        result = pd.concat(clean_dfs, ignore_index=True)

        if external_view:
            # Mask value and rate where suppressed_flag is True
            mask = result["suppressed_flag"] == True
            result.loc[mask, "value"] = None
            result.loc[mask, "rate_per_1000"] = None
            if "raw_count" in result.columns:
                result.drop(columns=["raw_count"], inplace=True)

        result.sort_values(by=["obs_date", "signal_type", "geo_id"], inplace=True)
        return result

    def get_summary_stats(self) -> Dict[str, Any]:
        """Return dataset statistics across silver tables using fast metadata reads."""
        total_rows = 0
        suppressed_rows = 0
        comp_suppressed_rows = 0
        signals_found = set()
        dates_found = set()

        if self.obs_dir.exists():
            for sig_dir in self.obs_dir.iterdir():
                if sig_dir.is_dir():
                    signals_found.add(sig_dir.name)
                    for f in sig_dir.glob("*.parquet"):
                        if f.name.endswith(".tmp.parquet"):
                            continue
                        dates_found.add(f.stem)
                        meta = pq.read_metadata(f)
                        total_rows += meta.num_rows

            # Fast sampling/count check across a sample of recent files or full scan
            # Read metadata quickly
            sample_dates = sorted(list(dates_found))[-30:] if dates_found else []
            for sig in signals_found:
                for d in sample_dates:
                    p = self.obs_dir / sig / f"{d}.parquet"
                    if p.exists():
                        table = pq.read_table(p, columns=["suppressed_flag", "suppression_type"])
                        df = table.to_pandas()
                        suppressed_rows += int(df["suppressed_flag"].sum())
                        comp_suppressed_rows += int((df["suppression_type"] == "complementary").sum())

            # Scale up sample estimate to total window
            if sample_dates and len(dates_found) > len(sample_dates):
                ratio = len(dates_found) / float(len(sample_dates))
                suppressed_rows = int(suppressed_rows * ratio)
                comp_suppressed_rows = int(comp_suppressed_rows * ratio)

        return {
            "total_observations": total_rows,
            "suppressed_cells": suppressed_rows,
            "complementary_suppressed_cells": comp_suppressed_rows,
            "unique_signals": sorted(list(signals_found)),
            "date_count": len(dates_found),
            "min_date": min(dates_found) if dates_found else None,
            "max_date": max(dates_found) if dates_found else None,
        }
