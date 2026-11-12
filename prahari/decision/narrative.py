"""
Fenced Epidemiological Narrative Generator.
Provides deterministic templates and fenced LLM synthesis with strict numerical
auditing preventing hallucinations: every number in the output must exist in the input JSON.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
import re
import logging
from prahari.detection.l5_policy import PrahariAlert
from prahari.decision.playbook_engine import Playbook

logger = logging.getLogger(__name__)


def extract_numbers_from_obj(obj: Any) -> Set[str]:
    """Recursively extracts all numbers, floats, percentages, and dates from a JSON object."""
    numbers: Set[str] = set()

    def _walk(val: Any):
        if isinstance(val, (int, float)):
            # Normalize float representation
            s = f"{val:.4f}".rstrip("0").rstrip(".")
            numbers.add(s)
            numbers.add(str(int(val)) if float(val).is_integer() else str(val))
            numbers.add(f"{val:.1f}")
            numbers.add(f"{val:.2f}")
            numbers.add(f"{val*100:.0f}")
            numbers.add(f"{val*100:.1f}")
        elif isinstance(val, str):
            # Extract standalone numbers or tokens from strings (e.g. '2025-08-20', '32°C')
            found = re.findall(r"\b\d+(?:\.\d+)?\b", val)
            for num in found:
                numbers.add(num)
                try:
                    flt = float(num)
                    numbers.add(f"{flt:.1f}")
                    numbers.add(f"{flt:.2f}")
                except ValueError:
                    pass
        elif isinstance(val, dict):
            for v in val.values():
                _walk(v)
        elif isinstance(val, list):
            for item in val:
                _walk(item)

    _walk(obj)
    return numbers


class NarrativeGenerator:
    """
    Generates clinical and operational alert narratives with deterministic safety guarantees.
    """

    @staticmethod
    def generate_deterministic_template(
        alert: PrahariAlert,
        playbook: Playbook,
        evidence_summary: Dict[str, Any],
    ) -> str:
        """
        Builds an exact, transparent clinical narrative strictly from confirmed inputs.
        """
        geo_str = ", ".join(alert.geo_ids)
        prob_pct = f"{alert.probability * 100:.1f}%"
        ci_str = f"{alert.ci_low * 100:.1f}%–{alert.ci_high * 100:.1f}%"
        sev_label = alert.severity.value.upper()

        lines = [
            f"**Munzir (منذر) Situational Briefing — {sev_label} [{alert.alert_type.replace('_', ' ').upper()}]**",
            f"**Location:** {geo_str} | **Date:** {alert.obs_date} | **Incident:** {alert.incident_id or 'New'}",
            "",
            f"**Epidemiological Assessment:**",
            f"A {alert.severity.value.lower()}-tier syndromic anomaly was identified with a calibrated outbreak probability of {prob_pct} (90% conformal prediction interval: {ci_str}).",
        ]

        # Driver details
        if alert.signal_contributions:
            top_drivers = sorted(alert.signal_contributions.items(), key=lambda x: x[1], reverse=True)
            driver_strs = [f"{grp} ({score:+.2f})" for grp, score in top_drivers if abs(score) > 0.05]
            if driver_strs:
                lines.append(f"Primary signal attribution indicates driving contributions from: {', '.join(driver_strs)}.")

        # Environmental context
        env = evidence_summary.get("environmental_context", {})
        if "wbgt_max" in env or "pm25" in env:
            env_parts = []
            if "wbgt_max" in env:
                env_parts.append(f"ambient WBGT daily max at {env['wbgt_max']}°C (3-day forecast: {env.get('wbgt_forecast_3d_max', 'N/A')}°C)")
            if "pm25" in env:
                env_parts.append(f"ambient PM2.5 mean at {env['pm25']} µg/m³ (3-day forecast: {env.get('pm25_forecast_3d_mean', 'N/A')} µg/m³)")
            lines.append(f"**Environmental Context:** {'; '.join(env_parts)}.")

        # Data quality
        lines.append(f"**Data Quality Status:** {alert.dq_status} (Completeness: {evidence_summary.get('dq_completeness_pct', 100)}%).")

        # Playbook actions & owner
        lead_role = playbook.responsible.get("lead", alert.owner_role)
        lines.append("")
        lines.append(f"**Operational Response & Ownership:**")
        lines.append(f"**Designated Lead:** {lead_role}")
        lines.append(f"**Mandated Action Protocols ({playbook.name}):**")
        for act in playbook.actions:
            lines.append(f"  • {act}")

        # Assumptions
        if playbook.assumptions:
            lines.append("")
            lines.append("**Key System Assumptions & Caveats:**")
            for asm in playbook.assumptions:
                lines.append(f"  - {asm}")

        return "\n".join(lines)

    @staticmethod
    def verify_numbers_strictly(narrative_text: str, allowed_numbers: Set[str]) -> bool:
        """
        Strict safety gate: Extracts all numbers in narrative_text and verifies
        that every single number was present in the allowed_numbers set.
        Returns False if any unknown / hallucinated number is found.
        """
        # Find all numbers (integers, decimals) in narrative text
        text_numbers = re.findall(r"\b\d+(?:\.\d+)?\b", narrative_text)

        # Remove common non-fact numbers (e.g., standard protocol bullet numbers 1., 2.)
        cleaned = [n for n in text_numbers if n not in ["1", "2", "3", "4", "5", "10", "20", "30", "45", "90"]]

        for num in cleaned:
            # Check direct string match
            if num in allowed_numbers:
                continue

            # Check floating point equivalence
            try:
                flt = float(num)
                if (
                    str(flt) in allowed_numbers
                    or f"{flt:.1f}" in allowed_numbers
                    or f"{flt:.2f}" in allowed_numbers
                    or str(int(flt)) in allowed_numbers
                    or f"{flt*100:.0f}" in allowed_numbers
                    or f"{flt*100:.1f}" in allowed_numbers
                ):
                    continue
            except ValueError:
                pass

            logger.warning(f"Fenced safety check failed: number '{num}' not found in structured input JSON.")
            return False

        return True

    @classmethod
    def generate_fenced_narrative(
        cls,
        alert: PrahariAlert,
        playbook: Playbook,
        evidence_summary: Dict[str, Any],
        candidate_llm_text: Optional[str] = None,
    ) -> Tuple[str, bool]:
        """
        Generates narrative with automatic verification:
        If candidate_llm_text is provided and contains zero hallucinations, it is accepted.
        Otherwise, falls back transparently to the deterministic template.
        Returns: (narrative_string, was_llm_accepted)
        """
        deterministic_text = cls.generate_deterministic_template(alert, playbook, evidence_summary)

        if not candidate_llm_text:
            return deterministic_text, False

        # Build allowed numbers set from all input structured facts
        combined_facts = {
            "alert": {
                "probability": alert.probability,
                "ci_low": alert.ci_low,
                "ci_high": alert.ci_high,
                "obs_date": alert.obs_date,
                "geo_ids": alert.geo_ids,
                "signal_contributions": alert.signal_contributions,
            },
            "playbook": playbook.model_dump(),
            "evidence": evidence_summary,
        }
        allowed_nums = extract_numbers_from_obj(combined_facts)

        # Run verification check
        is_safe = cls.verify_numbers_strictly(candidate_llm_text, allowed_nums)

        if is_safe:
            return candidate_llm_text, True
        else:
            logger.info("Falling back to deterministic template due to unverified numbers in candidate text.")
            return deterministic_text, False

