"""Privacy-preserving harmonisation layer package."""
from .spatial import SpatialHierarchyMapper, get_h3_index
from .suppression import SuppressionEngine, apply_small_cell_suppression, apply_complementary_suppression
from .differential_privacy import DifferentialPrivacyEngine
from .workplace import WorkplaceGovernanceEngine
from .pipeline import HarmonisationPipeline

__all__ = [
    "SpatialHierarchyMapper",
    "get_h3_index",
    "SuppressionEngine",
    "apply_small_cell_suppression",
    "apply_complementary_suppression",
    "DifferentialPrivacyEngine",
    "WorkplaceGovernanceEngine",
    "HarmonisationPipeline",
]

