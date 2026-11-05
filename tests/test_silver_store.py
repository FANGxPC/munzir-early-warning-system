"""Unit tests for Silver Lakehouse Store and Workplace Governance."""

import tempfile
from pathlib import Path
import pytest
from prahari.models.canonical import SilverSignalObservation
from prahari.storage.silver_store import SilverStore
from prahari.harmonisation.workplace import WorkplaceGovernanceEngine, MANDATORY_WORKPLACE_BANNER


def test_silver_store_write_and_query():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = SilverStore(base_dir=Path(tmpdir))

        observations = [
            SilverSignalObservation(
                signal_type="clinical_resp",
                geo_level="district",
                geo_id="DXB-JA",
                obs_date="2026-06-01",
                value=None,  # Suppressed in external view
                raw_count=4.0,
                suppressed_flag=True,
                suppression_type="primary",
            ),
            SilverSignalObservation(
                signal_type="clinical_resp",
                geo_level="district",
                geo_id="DXB-AQ",
                obs_date="2026-06-01",
                value=28.0,
                raw_count=28.0,
                suppressed_flag=False,
                suppression_type="none",
            ),
        ]

        written = store.write_observations(observations)
        assert written == 2

        # Query internal view
        df_internal = store.read_observations(external_view=False)
        assert len(df_internal) == 2
        assert "raw_count" in df_internal.columns

        # Query external view
        df_external = store.read_observations(external_view=True)
        assert len(df_external) == 2
        # Suppressed cell must be masked as None/NaN in external view
        row_supp = df_external[df_external["geo_id"] == "DXB-JA"].iloc[0]
        assert pytest.approx(row_supp["suppressed_flag"]) == True
        assert row_supp["value"] is None or str(row_supp["value"]) == "nan"
        assert "raw_count" not in df_external.columns  # Dropped from external view


def test_silver_privacy_schema_forbids_identifiers():
    """Requirement: unit test proves no column can hold a personal identifier."""
    with pytest.raises(ValueError, match="Privacy violation"):
        SilverSignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            patient_name="John Doe",  # Forbidden personal identifier
        )


def test_workplace_minimum_group_rule():
    engine = WorkplaceGovernanceEngine(min_group_size=50)

    # Site A: 120 workers (eligible)
    view_large = engine.enforce_rate_view(
        site_id="SITE-JA-01",
        district_id="DXB-JA",
        obs_date="2026-06-01",
        signal_type="absence_heat",
        raw_count=3.0,
        workforce_size=120,
    )
    assert view_large.is_eligible is True
    # Rate per 1000: (3 / 120) * 1000 = 25.0
    assert view_large.rate_per_1000 == 25.0
    assert view_large.disclaimer == MANDATORY_WORKPLACE_BANNER

    # Site B: 30 workers (< 50, ineligible)
    view_small = engine.enforce_rate_view(
        site_id="SITE-JA-02",
        district_id="DXB-JA",
        obs_date="2026-06-01",
        signal_type="absence_heat",
        raw_count=2.0,
        workforce_size=30,
    )
    assert view_small.is_eligible is False
    assert view_small.rate_per_1000 is None  # Rate withheld to prevent individual tracking


def test_workplace_prohibited_subsite_breakdowns():
    engine = WorkplaceGovernanceEngine()

    # Attempting to slice by team or shift must raise PermissionError
    with pytest.raises(PermissionError, match="Prohibited Query"):
        engine.validate_query_filters({"shift": "night_shift", "site_id": "SITE-JA-01"})

    with pytest.raises(PermissionError, match="Prohibited Query"):
        engine.validate_query_filters({"worker_id": "EMP-102"})

