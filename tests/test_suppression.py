"""Unit tests for small-cell suppression, complementary masking, and algebraic privacy."""

from prahari.models.canonical import SilverSignalObservation
from prahari.harmonisation.suppression import (
    apply_small_cell_suppression,
    apply_complementary_suppression,
    SuppressionEngine,
)


def test_primary_small_cell_suppression():
    observations = [
        SilverSignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=4.0,  # <= 10, must be suppressed
            raw_count=4.0,
        ),
        SilverSignalObservation(
            signal_type="clinical_resp",
            geo_level="district",
            geo_id="DXB-AQ",
            obs_date="2026-06-01",
            value=25.0,  # > 10, remains unsuppressed
            raw_count=25.0,
        ),
        SilverSignalObservation(
            signal_type="wbgt_max",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=34.5,  # Continuous physical metric, exempt from cell suppression
            raw_count=34.5,
        ),
    ]

    suppressed = apply_small_cell_suppression(observations, k=10)
    assert len(suppressed) == 3

    # Cell 1 (count = 4): primary suppressed
    assert suppressed[0].suppressed_flag is True
    assert suppressed[0].suppression_type == "primary"
    assert suppressed[0].value is None

    # Cell 2 (count = 25): not suppressed
    assert suppressed[1].suppressed_flag is False
    assert suppressed[1].value == 25.0

    # Cell 3 (WBGT): exempt
    assert suppressed[2].suppressed_flag is False
    assert suppressed[2].value == 34.5


def test_complementary_suppression_prevents_subtraction():
    """
    Scenario:
    District A: count = 5 (primarily suppressed)
    District B: count = 40 (unsuppressed)
    District C: count = 60 (unsuppressed)
    Total = 105.
    If only District A is suppressed, an attacker computes: 105 - (40 + 60) = 5.
    Complementary suppression MUST also suppress District B (lowest remaining)
    so attacker only knows: A + B = 45 (infinitely many integer solutions).
    """
    observations = [
        SilverSignalObservation(
            signal_type="clinical_gi",
            geo_level="district",
            geo_id="DXB-JA",
            obs_date="2026-06-01",
            value=5.0,
            raw_count=5.0,
        ),
        SilverSignalObservation(
            signal_type="clinical_gi",
            geo_level="district",
            geo_id="DXB-AQ",
            obs_date="2026-06-01",
            value=40.0,
            raw_count=40.0,
        ),
        SilverSignalObservation(
            signal_type="clinical_gi",
            geo_level="district",
            geo_id="DXB-DS",
            obs_date="2026-06-01",
            value=60.0,
            raw_count=60.0,
        ),
    ]

    engine = SuppressionEngine(k=10)
    harmonised = engine.process(observations)

    # District A is primary suppressed
    assert harmonised[0].suppressed_flag is True
    assert harmonised[0].suppression_type == "primary"

    # District B MUST be complementary suppressed
    assert harmonised[1].suppressed_flag is True
    assert harmonised[1].suppression_type == "complementary"

    # District C remains unsuppressed
    assert harmonised[2].suppressed_flag is False
    assert harmonised[2].value == 60.0

    # Verification: Audit must confirm algebraic privacy is secure!
    is_secure, vulns = engine.verify_algebraic_privacy(harmonised)
    assert is_secure is True
    assert len(vulns) == 0

