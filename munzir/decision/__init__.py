"""
Decision support and operational playbook engine package (Phase 4).
Translates calibrated alerts into proportionate, owned, evidence-backed recommendations.
"""

from .raci import RoleType, RACIRoleMatrix, RACIAssignment
from .playbook_engine import Playbook, PlaybookEngine
from .evidence_card import EvidenceCard, EvidenceCardGenerator
from .acknowledgement import AcknowledgementManager, AcknowledgementRecord, AlertStatus
from .narrative import NarrativeGenerator

__all__ = [
    "RoleType",
    "RACIRoleMatrix",
    "RACIAssignment",
    "Playbook",
    "PlaybookEngine",
    "EvidenceCard",
    "EvidenceCardGenerator",
    "AcknowledgementManager",
    "AcknowledgementRecord",
    "AlertStatus",
    "NarrativeGenerator",
]

