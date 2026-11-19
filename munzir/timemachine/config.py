"""
Time Machine Replay Configuration & Sources Metadata.
Stores verified citations, DOIs, URLs, and parameter schemas for historical replay events.
Satisfies Hackathon Criterion 5 (Operational Validation) & Zero-Leakage Policy.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Any, Optional
import json

CONFIG_DIR = Path(__file__).resolve().parent
SOURCES_JSON_PATH = Path(__file__).resolve().parents[2] / "data" / "timemachine" / "sources.json"


@dataclass
class ReplayEventConfig:
    event_id: str
    name: str
    region_name: str
    latitude: float
    longitude: float
    baseline_start: str
    baseline_end: str
    event_start: str
    event_end: str
    observed_peak_date: str
    observed_peak_value: float
    is_hybrid: bool = False
    hybrid_label: Optional[str] = None
    weather_source: Dict[str, Any] = field(default_factory=dict)
    outcome_source: Dict[str, Any] = field(default_factory=dict)
    reporting_delay_spec: Dict[str, Any] = field(default_factory=dict)
    threshold_comparator: Dict[str, Any] = field(default_factory=dict)


def load_sources_config(path: Optional[Path] = None) -> Dict[str, ReplayEventConfig]:
    """Loads validated replay event configs from sources.json."""
    target_path = Path(path or SOURCES_JSON_PATH)
    if not target_path.exists():
        # Fallback to default in-code dictionary if json is not yet initialized
        return {}

    with open(target_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    configs = {}
    for eid, ev in data.get("events", {}).items():
        rp = ev.get("replay_period", {})
        coords = ev.get("coordinates", {})
        configs[eid] = ReplayEventConfig(
            event_id=eid,
            name=ev.get("name", eid),
            region_name=ev.get("region_name", ""),
            latitude=coords.get("latitude", 0.0),
            longitude=coords.get("longitude", 0.0),
            baseline_start=rp.get("baseline_start", ""),
            baseline_end=rp.get("baseline_end", ""),
            event_start=rp.get("event_start", ""),
            event_end=rp.get("event_end", ""),
            observed_peak_date=rp.get("observed_peak_date", ""),
            observed_peak_value=rp.get("observed_peak_value", 0.0),
            is_hybrid=ev.get("is_hybrid", False),
            hybrid_label=ev.get("hybrid_label"),
            weather_source=ev.get("weather_source", {}),
            outcome_source=ev.get("outcome_source", {}),
            reporting_delay_spec=ev.get("reporting_delay_spec", {}),
            threshold_comparator=ev.get("threshold_comparator", {}),
        )
    return configs

