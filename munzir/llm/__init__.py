"""
Munzir LLM Package — Inception 42 Jais-3-0.9B & Multilingual Frontline Dispatch (Phase 17).
"""

from munzir.llm.fenced_validator import FencedHallucinationGate
from munzir.llm.jais_runner import JaisGenerationResult, JaisInferenceRunner
from munzir.llm.multilingual_dispatch import (
    MultilingualDispatchCard,
    generate_multilingual_dispatch,
)

__all__ = [
    "JaisInferenceRunner",
    "JaisGenerationResult",
    "FencedHallucinationGate",
    "MultilingualDispatchCard",
    "generate_multilingual_dispatch",
]

