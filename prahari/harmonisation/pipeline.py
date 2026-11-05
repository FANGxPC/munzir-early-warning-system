"""
Harmonisation ETL Pipeline: Bronze -> Silver.
Ingests Bronze Parquet observations, applies spatial H3 mapping, resolves
geolocation fallbacks, aggregates with denominators, and enforces small-cell
and complementary suppression.
"""

from typing import List, Dict, Any, Optional
import pandas as pd

from prahari.storage.bronze_store import BronzeStore
from prahari.storage.silver_store import SilverStore
from prahari.harmonisation.spatial import SpatialHierarchyMapper
from prahari.harmonisation.suppression import SuppressionEngine
from prahari.models.canonical import SilverSignalObservation


class HarmonisationPipeline:
    """
    Transforms Bronze raw partitioned observations into Silver harmonised,
    privacy-preserving, suppression-aware observations.
    """

    def __init__(
        self,
        region_key: str = "uae",
        bronze_store: Optional[BronzeStore] = None,
        silver_store: Optional[SilverStore] = None,
    ):
        self.region_key = region_key
        self.bronze_store = bronze_store or BronzeStore()
        self.silver_store = silver_store or SilverStore()
        self.spatial_mapper = SpatialHierarchyMapper(region_key=region_key)
        self.suppression_engine = SuppressionEngine()

    def run_harmonisation(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        signal_types: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Executes the Bronze-to-Silver pipeline.
        Returns a summary report of records processed, suppressed, and persisted.
        """
        # 1. Read raw Bronze observations
        bronze_df = self.bronze_store.read_observations(
            signal_types=signal_types,
            start_date=start_date,
            end_date=end_date,
        )

        if bronze_df.empty:
            return {"status": "no_data", "records_processed": 0}

        # 2. Map spatial hierarchy and enrich records
        silver_candidates: List[SilverSignalObservation] = []

        for _, row in bronze_df.iterrows():
            geo_id = str(row["geo_id"])
            geo_level = str(row["geo_level"])
            sig_type = str(row["signal_type"])
            obs_date = str(row["obs_date"])
            val = float(row["value"])
            denom = float(row["denominator"]) if pd.notna(row.get("denominator")) else None
            completeness = float(row.get("completeness_score", 1.0))
            latency = float(row.get("source_latency_hrs", 0.0))

            # Resolve spatial hierarchy
            if geo_level == "site":
                spatial_info = self.spatial_mapper.resolve_hierarchy(site_id=geo_id)
            elif geo_level == "district":
                spatial_info = self.spatial_mapper.resolve_hierarchy(district_id=geo_id)
            else:
                spatial_info = self.spatial_mapper.resolve_hierarchy()

            # Calculate rate per 1000 if denominator exists
            rate_per_1000 = None
            if denom and denom > 0:
                rate_per_1000 = round((val / denom) * 1000.0, 3)

            silver_candidates.append(
                SilverSignalObservation(
                    signal_type=sig_type,
                    geo_level=spatial_info["geo_level"],
                    geo_id=spatial_info["geo_id"],
                    h3_index=spatial_info["h3_index"],
                    district_id=spatial_info["district_id"],
                    location_confidence=spatial_info["location_confidence"],
                    obs_date=obs_date,
                    value=val,
                    raw_count=val,
                    rate_per_1000=rate_per_1000,
                    denominator=denom,
                    completeness_score=completeness,
                    source_latency_hrs=latency,
                )
            )

        # 3. Apply Primary and Complementary Suppression
        harmonised_observations = self.suppression_engine.process(silver_candidates)

        # 4. Write to Silver Store
        total_written = self.silver_store.write_observations(harmonised_observations)

        # 5. Security audit check
        is_secure, vuln_list = self.suppression_engine.verify_algebraic_privacy(harmonised_observations)

        primary_suppressed = sum(1 for o in harmonised_observations if o.suppression_type == "primary")
        comp_suppressed = sum(1 for o in harmonised_observations if o.suppression_type == "complementary")

        return {
            "status": "success",
            "records_processed": len(silver_candidates),
            "records_written": total_written,
            "primary_suppressed_cells": primary_suppressed,
            "complementary_suppressed_cells": comp_suppressed,
            "algebraic_privacy_verified": is_secure,
            "vulnerabilities": vuln_list,
        }

