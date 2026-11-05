"""
Automated SFTP / CSV Batch Drop Adapter for Munzir (منذر).
Handles inbound ingestion of employer occupational safety reports and lab drops,
and outbound syndromic export for enterprise EHS platforms (Enablon, Cority, SAP EHS).
Enforces zero-PII validation and privacy-preserving aggregation rules.
"""

import csv
import io
from datetime import datetime, timezone
from typing import List, Dict, Any, Tuple, Optional
from uuid import uuid4

from prahari.models.canonical import SignalObservation, FORBIDDEN_IDENTIFIER_FIELDS


class SFTPCSVAdapter:
    """
    Ingests and exports privacy-safe tabular feeds over simulated SFTP batch drops.
    Enforces privacy-by-architecture by aggressively stripping/rejecting individual identifiers.
    """

    REQUIRED_WORKPLACE_COLS = {"site_id", "obs_date", "workforce_size"}
    OPTIONAL_WORKPLACE_COLS = {"heat_illness_count", "first_aid_count", "absence_heat_count", "indoor_temp"}

    @classmethod
    def ingest_workplace_batch(
        cls,
        csv_content: str,
        source_name: str = "sftp_drop"
    ) -> Tuple[List[SignalObservation], List[str]]:
        """
        Parses inbound workplace CSV batch drop.
        Returns (list_of_observations, list_of_validation_errors_or_warnings).
        """
        reader = csv.DictReader(io.StringIO(csv_content.strip()))
        headers = set(reader.fieldnames or [])

        warnings = []

        # Check for forbidden PII headers
        violating_headers = headers.intersection(FORBIDDEN_IDENTIFIER_FIELDS)
        if violating_headers:
            raise ValueError(
                f"Privacy Violation: Inbound batch contains prohibited personal identifier columns: {violating_headers}. "
                f"Batch rejected under UAE PDPL & Munzir Privacy-by-Architecture policy."
            )

        missing_required = cls.REQUIRED_WORKPLACE_COLS - headers
        if missing_required:
            raise ValueError(f"Batch format error: Missing required columns: {missing_required}")

        observations: List[SignalObservation] = []
        row_idx = 0

        for row in reader:
            row_idx += 1
            site_id = row.get("site_id", "").strip()
            obs_date = row.get("obs_date", "").strip()

            try:
                workforce = float(row.get("workforce_size", 0.0))
            except (ValueError, TypeError):
                workforce = 100.0

            if not site_id or not obs_date:
                warnings.append(f"Row {row_idx}: Skipped due to missing site_id or obs_date")
                continue

            # Absence heat signal
            if "absence_heat_count" in row and row["absence_heat_count"] != "":
                try:
                    val = float(row["absence_heat_count"])
                    observations.append(SignalObservation(
                        signal_type="absence_heat",
                        geo_level="site",
                        geo_id=site_id,
                        location_confidence="exact",
                        obs_date=obs_date,
                        value=val,
                        denominator=workforce,
                        source_latency_hrs=4.0,
                        completeness_score=1.0
                    ))
                except ValueError:
                    warnings.append(f"Row {row_idx}: Invalid absence_heat_count")

            # First aid / Heat illness incident signals
            for col_name, sig_name in [("first_aid_count", "incident"), ("heat_illness_count", "clinical_resp")]:
                if col_name in row and row[col_name] != "":
                    try:
                        val = float(row[col_name])
                        observations.append(SignalObservation(
                            signal_type=sig_name,
                            geo_level="site",
                            geo_id=site_id,
                            location_confidence="exact",
                            obs_date=obs_date,
                            value=val,
                            denominator=workforce,
                            source_latency_hrs=4.0,
                            completeness_score=1.0
                        ))
                    except ValueError:
                        warnings.append(f"Row {row_idx}: Invalid {col_name}")

        return observations, warnings

    @classmethod
    def export_ehs_summary(
        cls,
        observations: List[SignalObservation],
        min_cell_size: int = 10
    ) -> str:
        """
        Exports a rate-only aggregate CSV suitable for enterprise EHS integration.
        Applies small-cell suppression: cells with count < min_cell_size are masked as '<10'.
        """
        output = io.StringIO()
        writer = csv.writer(output)

        writer.writerow([
            "geo_id",
            "geo_level",
            "obs_date",
            "signal_type",
            "count_display",
            "rate_per_1000",
            "data_quality_score"
        ])

        for obs in observations:
            if obs.value < min_cell_size and obs.value > 0:
                count_str = f"<{min_cell_size}"
            elif obs.value == 0:
                count_str = "0"
            else:
                count_str = str(int(obs.value))

            denom = obs.denominator or 1000.0
            rate = (obs.value / denom * 1000.0) if denom > 0 else 0.0

            writer.writerow([
                obs.geo_id,
                obs.geo_level,
                obs.obs_date,
                obs.signal_type,
                count_str,
                f"{rate:.2f}",
                f"{obs.completeness_score:.2f}"
            ])

        return output.getvalue()

