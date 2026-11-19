"""
ISO 7933:2004 Predicted Heat Strain (PHS) Model (Phase 22).
Implements the international standard rational heat balance equation:
  M - W = C + R + E_req + S
Computes core body temperature drift, required sweat rates, and maximum
allowable exposure duration (D_lim) for frontline industrial workers.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class WorkerPhysicalProfile:
    """Standard physiological parameters of a frontline industrial worker."""
    mass_kg: float = 75.0
    height_m: float = 1.75
    body_surface_area_m2: float = 1.90  # DuBois formula default for 75kg, 1.75m
    clothing_insulation_clo: float = 0.6  # Standard summer cotton coveralls
    specific_heat_tissue_kj_kg_k: float = 3.49


# Standard metabolic work rates (ISO 8996 & ISO 7933)
METABOLIC_PROFILES: Dict[str, Dict[str, Any]] = {
    "heavy_rigging": {
        "name": "Heavy Structural Steel Rigger / Scaffolder",
        "metabolic_rate_w_m2": 415.0,
        "description": "Intense manual climbing, steel positioning, heavy lifting (>25kg)",
    },
    "masonry_concreting": {
        "name": "Concrete Pouring & Masonry Gang",
        "metabolic_rate_w_m2": 330.0,
        "description": "Continuous shovel work, concrete vibration, brisk walking",
    },
    "logistics_forklift": {
        "name": "Forklift Driver / Depot Logistics",
        "metabolic_rate_w_m2": 180.0,
        "description": "Vehicle driving, light material packaging, inspection",
    },
    "routine_maintenance": {
        "name": "Routine Plant Maintenance / Foreman Patrol",
        "metabolic_rate_w_m2": 240.0,
        "description": "Intermittent walking, equipment inspection, hand tools",
    },
}


@dataclass
class PHSAssessmentResult:
    """Calculated Predicted Heat Strain outputs for an individual or cohort."""
    activity_type: str
    activity_name: str
    metabolic_rate_w_m2: float
    ambient_temp_c: float
    relative_humidity_pct: float
    globe_temp_c: float
    air_velocity_m_s: float
    
    # Heat Balance Fluxes (W/m^2)
    convection_w_m2: float
    radiation_w_m2: float
    evaporation_required_w_m2: float
    evaporation_max_capacity_w_m2: float
    heat_storage_rate_w_m2: float
    
    # Physiological Strain Metrics
    core_temp_rise_rate_c_per_hr: float
    projected_core_temp_1hr_c: float
    max_allowable_exposure_mins: float  # D_lim
    sweat_rate_liters_per_hr: float
    strain_status: str  # "COMPENSABLE", "BORDERLINE", "UNCOMPENSABLE_CRITICAL"
    clinical_mechanism: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "activity_type": self.activity_type,
            "activity_name": self.activity_name,
            "metabolic_rate_w_m2": self.metabolic_rate_w_m2,
            "environmental": {
                "ambient_temp_c": self.ambient_temp_c,
                "relative_humidity_pct": self.relative_humidity_pct,
                "globe_temp_c": self.globe_temp_c,
                "air_velocity_m_s": self.air_velocity_m_s,
            },
            "heat_fluxes_w_m2": {
                "convection": round(self.convection_w_m2, 1),
                "radiation": round(self.radiation_w_m2, 1),
                "evaporation_required": round(self.evaporation_required_w_m2, 1),
                "evaporation_max_capacity": round(self.evaporation_max_capacity_w_m2, 1),
                "heat_storage_rate": round(self.heat_storage_rate_w_m2, 1),
            },
            "physiological_strain": {
                "core_temp_rise_rate_c_per_hr": round(self.core_temp_rise_rate_c_per_hr, 2),
                "projected_core_temp_1hr_c": round(self.projected_core_temp_1hr_c, 2),
                "max_allowable_exposure_mins": round(self.max_allowable_exposure_mins, 1),
                "sweat_rate_liters_per_hr": round(self.sweat_rate_liters_per_hr, 2),
                "strain_status": self.strain_status,
                "clinical_mechanism": self.clinical_mechanism,
            },
        }


class ISO7933PredictedHeatStrainEngine:
    """
    Rational heat balance engine implementing ISO 7933:2004 (PHS Model).
    Calculates metabolic internal heat, convective/radiative loads, evaporative
    limits, body heat storage S, core body temperature rise dT_re/dt, and D_lim.
    """

    def __init__(self, profile: Optional[WorkerPhysicalProfile] = None):
        self.profile = profile or WorkerPhysicalProfile()

    @staticmethod
    def saturation_vapor_pressure_kpa(temp_c: float) -> float:
        """Computes saturation vapor pressure using Magnus-Tetens formula (kPa)."""
        return 0.61078 * math.exp((17.27 * temp_c) / (temp_c + 237.3))

    def evaluate_phs(
        self,
        ambient_temp_c: float,
        relative_humidity_pct: float,
        globe_temp_c: Optional[float] = None,
        air_velocity_m_s: float = 1.0,
        activity_type: str = "heavy_rigging",
        initial_core_temp_c: float = 37.0,
    ) -> PHSAssessmentResult:
        """
        Evaluates ISO 7933 Predicted Heat Strain for given environmental and occupational profile.
        """
        # Guard inputs
        if globe_temp_c is None or math.isnan(globe_temp_c):
            globe_temp_c = ambient_temp_c + 4.5  # Realistic sunny asphalt offset
        air_velocity_m_s = max(0.2, min(10.0, air_velocity_m_s))
        relative_humidity_pct = max(5.0, min(100.0, relative_humidity_pct))

        meta = METABOLIC_PROFILES.get(activity_type, METABOLIC_PROFILES["heavy_rigging"])
        M = meta["metabolic_rate_w_m2"]
        W = 0.1 * M  # Mechanical efficiency ~10%
        H = M - W    # Internal metabolic heat generation

        # Mean skin temperature in hot climates: T_sk ≈ 35.5°C
        T_sk = 35.5
        P_sk = self.saturation_vapor_pressure_kpa(T_sk)  # ~5.77 kPa

        # Ambient vapor pressure P_a
        P_a_sat = self.saturation_vapor_pressure_kpa(ambient_temp_c)
        P_a = (relative_humidity_pct / 100.0) * P_a_sat

        # Convective heat transfer coefficient h_c (forced convection)
        h_c = max(3.5, 8.3 * (air_velocity_m_s ** 0.6))
        # Convective exchange C: positive = body loses heat, negative = body gains heat
        # C = h_c * (T_sk - T_a)
        C = h_c * (T_sk - ambient_temp_c)

        # Radiative heat transfer coefficient h_r ≈ 4.7 W/(m^2 K)
        # R = h_r * (T_sk - T_g)
        h_r = 4.7
        R = h_r * (T_sk - globe_temp_c)

        # Required evaporative heat loss E_req to maintain thermal equilibrium:
        # H - C - R - E_req = 0 => E_req = H - C - R
        # Note: if C and R are negative (ambient > skin), heat flows into body, increasing E_req
        E_req = H - C - R

        # Maximum evaporative capacity of ambient environment E_max:
        # Lewis relation: h_e = 16.5 * h_c
        h_e = 16.5 * h_c
        delta_p = max(0.05, P_sk - P_a)
        E_max = h_e * delta_p

        # Evaporative efficiency and heat storage rate S
        if E_req <= E_max:
            # Compensable environment: body can sweat enough to stay in balance
            E_actual = max(0.0, E_req)
            S = 0.0
            strain_status = "COMPENSABLE"
        else:
            # Uncompensable heat strain: required evaporation exceeds physical capacity!
            E_actual = E_max
            S = E_req - E_max  # Positive S = heat accumulates in tissue!
            strain_status = "UNCOMPENSABLE_CRITICAL" if S >= 50.0 else "BORDERLINE"

        # Rate of core body temperature rise dT_re / dt (°C/hr)
        # S (W/m^2) * Area (m^2) * 3600s / (mass_kg * c_tissue * 1000 J/kJ)
        heat_accumulation_factor = (self.profile.body_surface_area_m2 * 3600.0) / (
            self.profile.mass_kg * self.profile.specific_heat_tissue_kj_kg_k * 1000.0
        )
        dT_re_dt = max(0.0, S * heat_accumulation_factor)

        # Projected core temp after 1 continuous hour of work
        projected_T_re_1hr = initial_core_temp_c + dT_re_dt

        # Maximum Allowable Exposure Duration D_lim before reaching 38.5°C threshold
        safe_delta_T = max(0.0, 38.5 - initial_core_temp_c)
        if dT_re_dt > 0.01:
            D_lim = (safe_delta_T / dT_re_dt) * 60.0
            D_lim = min(480.0, max(10.0, D_lim))
        else:
            D_lim = 480.0  # Full 8-hour shift is physiologically sustainable

        # Required sweat rate (Liters / hour)
        # Latent heat of vaporization of water: 2430 J/g = 2.43 kJ/g = 2430 kJ/kg
        # Sweat efficiency η_sw
        eta_sw = max(0.4, min(1.0, 0.5 + 0.5 * (E_max / max(1.0, E_req))))
        sweat_rate_kg_hr = (E_req * self.profile.body_surface_area_m2 * 3600.0) / (2430000.0 * eta_sw)
        sweat_rate_liters = max(0.2, min(3.5, sweat_rate_kg_hr))

        if strain_status == "UNCOMPENSABLE_CRITICAL":
            mechanism = (
                f"Uncompensable Thermal Storage: Required sweat evaporation ({E_req:.0f} W/m²) exceeds atmospheric "
                f"evaporative limit ({E_max:.0f} W/m²). Heat accumulates in body tissue at {S:.0f} W/m², driving core "
                f"rectal temperature upward at +{dT_re_dt:.2f}°C/hr. Safe duration limited to {D_lim:.0f} minutes."
            )
        elif strain_status == "BORDERLINE":
            mechanism = (
                f"Borderline Compensable: Evaporation near threshold. Core body temperature projected to rise to "
                f"{projected_T_re_1hr:.1f}°C in 60m. High fluid replacement ({sweat_rate_liters:.2f} L/hr) required."
            )
        else:
            mechanism = (
                f"Compensable State: Sweating maintains thermal equilibrium. Fluid loss rate: {sweat_rate_liters:.2f} L/hr. "
                f"Safe for continuous shift under standard rest rotations."
            )

        return PHSAssessmentResult(
            activity_type=activity_type,
            activity_name=meta["name"],
            metabolic_rate_w_m2=M,
            ambient_temp_c=ambient_temp_c,
            relative_humidity_pct=relative_humidity_pct,
            globe_temp_c=globe_temp_c,
            air_velocity_m_s=air_velocity_m_s,
            convection_w_m2=C,
            radiation_w_m2=R,
            evaporation_required_w_m2=E_req,
            evaporation_max_capacity_w_m2=E_max,
            heat_storage_rate_w_m2=S,
            core_temp_rise_rate_c_per_hr=dT_re_dt,
            projected_core_temp_1hr_c=projected_T_re_1hr,
            max_allowable_exposure_mins=D_lim,
            sweat_rate_liters_per_hr=sweat_rate_liters,
            strain_status=strain_status,
            clinical_mechanism=mechanism,
        )

