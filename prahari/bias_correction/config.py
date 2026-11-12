"""
Configuration parameters, thresholds, regimes, and data paths for the
Munzir Sentinel WBGT Microclimate Bias Correction Module.
"""

from pathlib import Path
from typing import Dict, Any, Tuple
import json

from prahari.config import BASE_DIR, DATA_DIR

BIAS_CORRECTION_DIR = BASE_DIR / "prahari" / "bias_correction"
SOURCES_FILE = BIAS_CORRECTION_DIR / "sources.json"
TELEMETRY_DATA_DIR = DATA_DIR / "sentinel_telemetry"
RESULTS_DATA_DIR = DATA_DIR / "bias_correction"

# Humidity regimes based on occupational heat balance dynamics
HUMIDITY_REGIMES = {
    "low": (0.0, 40.0),       # Arid desert daytime conditions
    "moderate": (40.0, 70.0), # Transitional / morning industrial conditions
    "high": (70.0, 100.0),    # Coastal marine layer / night humidity traps
}

# Physical sensor sanity bounds (flag and filter sensor failures)
SANITY_BOUNDS = {
    "air_temp_c": (-10.0, 65.0),
    "rh_pct": (0.0, 100.0),
    "globe_temp_c": (-10.0, 85.0),
    "wbgt_c": (-5.0, 50.0),
}

# Quality gates
DHT22_SATURATION_RH = 99.0
DHT22_SATURATION_MAX_HOURS = 6
GLOBE_MIN_OFFSET_C = -5.0   # Tg cannot drop > 5°C below Ta in physical environments
GLOBE_MAX_OFFSET_C = 35.0   # Maximum plausible radiant solar excess over Ta
STUCK_SENSOR_MAX_REPEATS = 10

# Validation settings
DEFAULT_TIME_BLOCK_FOLDS = 5
CONFORMAL_CONFIDENCE_LEVEL = 0.90  # 90% two-sided coverage (z = 1.645)
CONFORMAL_Z = 1.645
UNSENSORED_SITE_PENALTY_MULTIPLIER = 1.50  # 50% widening for unvalidated spatial transfer


def load_sources_config() -> Dict[str, Any]:
    """Loads traceable academic literature and standards citations."""
    if not SOURCES_FILE.exists():
        raise FileNotFoundError(f"Sources metadata missing at {SOURCES_FILE}")
    return json.loads(SOURCES_FILE.read_text(encoding="utf-8"))


def get_humidity_regime(rh_pct: float) -> str:
    """Categorizes relative humidity into low, moderate, or high regimes."""
    if rh_pct < 40.0:
        return "low"
    elif rh_pct <= 70.0:
        return "moderate"
    else:
        return "high"

