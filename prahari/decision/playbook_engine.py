"""
Decision Support Playbook Engine.
Loads declarative YAML action playbooks, matches operational guidance to alerts,
and enforces the strict proportionality ladder preventing disproportionate interventions.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
import yaml
from pydantic import BaseModel, Field

from prahari.config import BASE_DIR
from prahari.detection.l5_policy import AlertSeverity

logger = logging.getLogger(__name__)

DEFAULT_PLAYBOOKS_DIR = Path(BASE_DIR) / "playbooks"


class PlaybookTrigger(BaseModel):
    type: str
    severity: str
    site_type: Optional[str] = None


class Playbook(BaseModel):
    """Declarative operational playbook entry."""
    id: str
    name: str
    trigger: PlaybookTrigger
    proportionality_tier: str = "monitor"  # monitor, targeted_preventive, field_response
    actions: List[str] = Field(default_factory=list)
    responsible: Dict[str, Any] = Field(default_factory=dict)
    escalate_to_alert_if: str = ""
    evidence_required: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)
    references: List[str] = Field(default_factory=list)


# Allowed proportionality ladder mappings
TIER_HIERARCHY = {
    "monitor": 1,
    "targeted_preventive": 2,
    "field_response": 3,
}

SEVERITY_MAX_ALLOWED_TIER = {
    AlertSeverity.NONE: "monitor",
    AlertSeverity.WATCH: "monitor",
    AlertSeverity.WARNING: "targeted_preventive",
    AlertSeverity.ALERT: "field_response",
}


class PlaybookEngine:
    """
    Manages loading, matching, and validating action playbooks against active alerts.
    """

    def __init__(self, playbooks_dir: Optional[Path] = None):
        self.playbooks_dir = Path(playbooks_dir or DEFAULT_PLAYBOOKS_DIR)
        self.playbooks: Dict[str, Playbook] = {}
        self.load_playbooks()

    def load_playbooks(self) -> int:
        """Loads and parses all YAML files from the playbooks directory."""
        if not self.playbooks_dir.exists():
            logger.warning(f"Playbooks directory not found: {self.playbooks_dir}")
            return 0

        loaded = 0
        for yaml_path in self.playbooks_dir.glob("*.yaml"):
            try:
                with open(yaml_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    pb = Playbook(**data)
                    self.playbooks[pb.id] = pb
                    loaded += 1
            except Exception as e:
                logger.error(f"Error loading playbook {yaml_path}: {e}")

        logger.info(f"Loaded {loaded} playbooks from {self.playbooks_dir}")
        return loaded

    def get_playbook(
        self,
        alert_type: str,
        severity: AlertSeverity,
        is_site: bool = False,
    ) -> Playbook:
        """
        Matches an alert to the most relevant playbook according to type, severity, and context.
        """
        sev_str = severity.value if isinstance(severity, AlertSeverity) else str(severity).lower()

        # 1. Exact match by trigger
        for pb in self.playbooks.values():
            p_type = pb.trigger.type.lower()
            p_sev = pb.trigger.severity.lower()
            if p_type == alert_type.lower() and p_sev == sev_str:
                if pb.trigger.site_type:
                    if is_site and pb.trigger.site_type in ["outdoor", "facility"]:
                        return pb
                    elif not is_site and pb.trigger.site_type in ["district", "facility"]:
                        return pb
                else:
                    return pb

        # 2. Relaxed match by alert_type and severity
        for pb in self.playbooks.values():
            if pb.trigger.type.lower() == alert_type.lower() and pb.trigger.severity.lower() == sev_str:
                return pb

        # 3. Match by alert_type only
        for pb in self.playbooks.values():
            if pb.trigger.type.lower() == alert_type.lower():
                return pb

        # 4. Fallback to default generic playbook
        return Playbook(
            id=f"generic_{sev_str}",
            name=f"Standard Epidemiological {sev_str.capitalize()} Protocol",
            trigger=PlaybookTrigger(type=alert_type, severity=sev_str),
            proportionality_tier=SEVERITY_MAX_ALLOWED_TIER.get(severity, "monitor"),
            actions=[
                "Monitor regional health feeds and verify reporting facility data completeness",
                "Cross-check environmental forecast against clinic admission trends",
            ],
            responsible={
                "lead": "District Surveillance Officer",
                "accountable": "District Health Officer",
            },
            escalate_to_alert_if="Sustained elevated incidence over 48 hours or lab pathogen confirmation",
            evidence_required=["l1_exceedance", "completeness_score"],
            assumptions=["Data represents syndromic clinical presentation without definitive laboratory typing"],
            references=["WHO Outbreak Surveillance and Response Guidelines"],
        )

    @staticmethod
    def enforce_proportionality(severity: AlertSeverity, action_tier: str) -> bool:
        """
        Validates that a proposed action tier is legally and operationally proportionate.
        Returns True if action_tier is permissible under the evidence tier; False otherwise.
        """
        max_allowed = SEVERITY_MAX_ALLOWED_TIER.get(severity, "monitor")
        action_rank = TIER_HIERARCHY.get(action_tier.lower(), 1)
        allowed_rank = TIER_HIERARCHY.get(max_allowed.lower(), 1)
        return action_rank <= allowed_rank

    def get_proportionate_actions(self, playbook: Playbook, severity: AlertSeverity) -> List[str]:
        """
        Filters actions in the playbook to guarantee they never exceed the severity tier.
        """
        if not self.enforce_proportionality(severity, playbook.proportionality_tier):
            # Downgrade actions to monitoring level
            return [
                "Verify syndromic surveillance feeds and maintain enhanced monitoring (disruptive intervention withheld at current evidence tier)",
                "Review multi-day rolling incidence and await confirmatory signal corroboration",
            ]
        return playbook.actions

    def list_playbooks(self) -> List[Playbook]:
        """Returns all registered playbooks."""
        return list(self.playbooks.values())

