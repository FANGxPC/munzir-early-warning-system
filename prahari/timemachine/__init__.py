"""
Munzir Historical Time Machine Replay Package.
Strict as-of-date historical surveillance evaluation with zero hindsight leakage.
"""

from prahari.timemachine.config import ReplayEventConfig, load_sources_config
from prahari.timemachine.data_loader import (
    AsOfSnapshot,
    LeakageError,
    get_data_as_of,
    generate_reported_vintages,
)
from prahari.timemachine.detector import TimeMachineDetector, DayReplayResult
from prahari.timemachine.engine import TimeMachineEngine
from prahari.timemachine.metrics import ReplayOperationalMetrics, compute_replay_metrics

__all__ = [
    "ReplayEventConfig",
    "load_sources_config",
    "AsOfSnapshot",
    "LeakageError",
    "get_data_as_of",
    "generate_reported_vintages",
    "TimeMachineDetector",
    "DayReplayResult",
    "TimeMachineEngine",
    "ReplayOperationalMetrics",
    "compute_replay_metrics",
]

