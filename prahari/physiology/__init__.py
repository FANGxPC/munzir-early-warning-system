"""
Munzir Occupational Physiology Module (Phase 22).
Implements ISO 7933:2004 Predicted Heat Strain (PHS) and 72-Hour Cumulative
Nocturnal Thermal Debt Accumulation over authentic Lakehouse telemetry.
"""

from prahari.physiology.iso7933_phs import (
    ISO7933PredictedHeatStrainEngine,
    METABOLIC_PROFILES,
    PHSAssessmentResult,
    WorkerPhysicalProfile,
)
from prahari.physiology.thermal_debt import (
    CumulativeThermalDebtAssessment,
    DailyThermalProfile,
    ThermalDebtAccumulator,
)

__all__ = [
    "ISO7933PredictedHeatStrainEngine",
    "METABOLIC_PROFILES",
    "PHSAssessmentResult",
    "WorkerPhysicalProfile",
    "CumulativeThermalDebtAssessment",
    "DailyThermalProfile",
    "ThermalDebtAccumulator",
]

