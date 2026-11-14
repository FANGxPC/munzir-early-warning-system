"""
Tests for ISO 7933:2004 Predicted Heat Strain & Nocturnal Thermal Debt Engine (Phase 22).
"""

import math
from prahari.physiology.iso7933_phs import (
    ISO7933PredictedHeatStrainEngine,
    METABOLIC_PROFILES,
    WorkerPhysicalProfile,
)
from prahari.physiology.thermal_debt import ThermalDebtAccumulator


def test_saturation_vapor_pressure_magnus():
    """Verifies Magnus-Tetens formula against standard psychrometric tables."""
    # At 0°C, P_sat ≈ 0.611 kPa
    p0 = ISO7933PredictedHeatStrainEngine.saturation_vapor_pressure_kpa(0.0)
    assert 0.60 <= p0 <= 0.62

    # At 35.5°C (skin temp), P_sat ≈ 5.77 kPa
    p35 = ISO7933PredictedHeatStrainEngine.saturation_vapor_pressure_kpa(35.5)
    assert 5.70 <= p35 <= 5.85


def test_phs_metabolic_work_rate_scaling():
    """Verifies that heavy rigging yields higher thermal strain than forklift driving."""
    engine = ISO7933PredictedHeatStrainEngine()

    res_heavy = engine.evaluate_phs(
        ambient_temp_c=38.0,
        relative_humidity_pct=60.0,
        globe_temp_c=42.0,
        activity_type="heavy_rigging",
    )

    res_light = engine.evaluate_phs(
        ambient_temp_c=38.0,
        relative_humidity_pct=60.0,
        globe_temp_c=42.0,
        activity_type="logistics_forklift",
    )

    # Heavy work generates more internal metabolic heat
    assert res_heavy.metabolic_rate_w_m2 > res_light.metabolic_rate_w_m2
    # Heavy work requires more sweat evaporation
    assert res_heavy.evaporation_required_w_m2 > res_light.evaporation_required_w_m2
    # Heavy work has shorter safe duration limit D_lim
    assert res_heavy.max_allowable_exposure_mins < res_light.max_allowable_exposure_mins
    # Sweat rate is higher
    assert res_heavy.sweat_rate_liters_per_hr > res_light.sweat_rate_liters_per_hr


def test_phs_uncompensable_heat_storage():
    """Verifies that extreme Dubai summer conditions produce uncompensable heat storage (S > 0)."""
    engine = ISO7933PredictedHeatStrainEngine()

    # Extreme asphalt heat trap: 44°C ambient, 75% RH, 48°C globe
    res = engine.evaluate_phs(
        ambient_temp_c=44.0,
        relative_humidity_pct=75.0,
        globe_temp_c=48.0,
        activity_type="heavy_rigging",
    )

    assert res.strain_status == "UNCOMPENSABLE_CRITICAL"
    assert res.heat_storage_rate_w_m2 > 50.0  # Significant heat storage
    assert res.core_temp_rise_rate_c_per_hr > 1.0  # Rapid core temperature drift
    assert res.max_allowable_exposure_mins < 90.0  # Acute time limit


def test_phs_compensable_mild_conditions():
    """Verifies that mild indoor/shaded conditions remain compensable (S == 0)."""
    engine = ISO7933PredictedHeatStrainEngine()

    res = engine.evaluate_phs(
        ambient_temp_c=26.0,
        relative_humidity_pct=45.0,
        globe_temp_c=27.0,
        activity_type="logistics_forklift",
    )

    assert res.strain_status == "COMPENSABLE"
    assert res.heat_storage_rate_w_m2 == 0.0
    assert res.core_temp_rise_rate_c_per_hr == 0.0
    assert res.max_allowable_exposure_mins >= 400.0


def test_thermal_debt_accumulator_lakehouse_progression():
    """Verifies 72-hour thermal debt progression using authentic Lakehouse telemetry."""
    accumulator = ThermalDebtAccumulator()

    debt = accumulator.evaluate_site_thermal_debt(
        site_id="SITE-JA-01",
        target_date="2024-08-18",
        activity_type="heavy_rigging",
    )

    assert debt.site_id == "SITE-JA-01"
    assert len(debt.daily_profiles) == 3
    # Check that cumulative debt is positive under August extreme heat
    assert debt.cumulative_thermal_debt_kj_m2 > 0.0
    # Day 3 starting core temperature should show elevation due to nocturnal deficit
    assert debt.projected_day3_start_core_temp_c > 36.85
    # Collapse risk tier should be assigned
    assert debt.collapse_risk_tier in ("Moderate", "High", "Critical Collapse Risk")
    assert len(debt.mandatory_countermeasures) >= 2

    # Verify serialization
    data = debt.to_dict()
    assert "cumulative_debt_kj_m2" in data
    assert "daily_profiles" in data
    assert len(data["daily_profiles"]) == 3

