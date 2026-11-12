"""
Configuration and Sourced Assumptions Loader for the What-If Intervention Simulator.
Loads config/assumptions.yaml and provides typed access to peer-reviewed effect sizes,
statutory MOHRE regulations, and explicitly tracks UNVERIFIED parameters.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import yaml

from prahari.config import BASE_DIR

CONFIG_DIR = BASE_DIR / "config"
ASSUMPTIONS_FILE = CONFIG_DIR / "assumptions.yaml"


def load_assumptions_config(file_path: Optional[Path] = None) -> Dict[str, Any]:
    """Loads and validates the declarative YAML assumptions ledger."""
    path = file_path or ASSUMPTIONS_FILE
    if not path.exists():
        raise FileNotFoundError(f"Assumptions configuration missing at {path}")

    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    return data or {}


def get_unverified_assumptions(data: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    Extracts all parameters where verification_status == 'UNVERIFIED'.
    Guarantees strict compliance with the truth-in-science hard rule.
    """
    assumptions = data or load_assumptions_config()
    unverified = []

    for section_name, section_data in assumptions.items():
        if isinstance(section_data, dict):
            for param_key, param_info in section_data.items():
                if isinstance(param_info, dict):
                    if param_info.get("verification_status") == "UNVERIFIED" or param_info.get("doi_or_url") is None:
                        unverified.append({
                            "section": section_name,
                            "key": param_key,
                            "name": param_info.get("name", param_key),
                            "value": param_info.get("value"),
                            "range": param_info.get("range"),
                            "unit": param_info.get("unit"),
                            "source_title": param_info.get("source_title"),
                            "status": "UNVERIFIED",
                            "notes": param_info.get("notes", ""),
                        })

    return unverified

