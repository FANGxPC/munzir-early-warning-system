"""Synthetic signal generation and outbreak simulation package."""
from .events import InjectedScenarioCatalog, generate_ground_truth_events
from .defects import DataDefectEngine
from .generator import HealthWorkplaceSimulator

__all__ = [
    "InjectedScenarioCatalog",
    "generate_ground_truth_events",
    "DataDefectEngine",
    "HealthWorkplaceSimulator",
]

