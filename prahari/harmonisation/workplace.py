"""
Workplace Governance and Minimum-Group Policy Engine.
Enforces the N >= 50 cohort threshold, transforms counts into aggregate rates,
prohibits sub-site breakdowns (shift, team), and attaches non-disciplinary disclaimers.
"""

from typing import List, Dict, Any, Optional
from prahari.config import WORKPLACE_MIN_GROUP_SIZE
from prahari.models.canonical import WorkplaceRateView, SilverSignalObservation

MANDATORY_WORKPLACE_BANNER = (
    "Aggregate data — not for individual employment or disciplinary decisions."
)

PROHIBITED_BREAKDOWN_DIMENSIONS = {
    "worker_id", "employee_name", "shift", "team", "department",
    "contractor_id", "crew_lead", "badge_no"
}


class WorkplaceGovernanceEngine:
    """
    Enforces privacy by architecture for employer and workplace views.
    """

    def __init__(self, min_group_size: int = WORKPLACE_MIN_GROUP_SIZE):
        self.min_group_size = min_group_size

    def enforce_rate_view(
        self,
        site_id: str,
        district_id: str,
        obs_date: str,
        signal_type: str,
        raw_count: float,
        workforce_size: int,
    ) -> WorkplaceRateView:
        """
        Creates a safe workplace rate view. If workforce < min_group_size (50),
        rate is withheld to prevent individual re-identification.
        """
        if workforce_size < self.min_group_size:
            return WorkplaceRateView(
                site_id=site_id,
                district_id=district_id,
                obs_date=obs_date,
                signal_type=signal_type,
                workforce_size=workforce_size,
                rate_per_1000=None,
                is_eligible=False,
                disclaimer=MANDATORY_WORKPLACE_BANNER,
            )

        rate = round((raw_count / float(workforce_size)) * 1000.0, 3)
        return WorkplaceRateView(
            site_id=site_id,
            district_id=district_id,
            obs_date=obs_date,
            signal_type=signal_type,
            workforce_size=workforce_size,
            rate_per_1000=rate,
            is_eligible=True,
            disclaimer=MANDATORY_WORKPLACE_BANNER,
        )

    def validate_query_filters(self, requested_filters: Dict[str, Any]) -> None:
        """
        Security gate: rejects any query attempting to slice workplace data
        by shift, team, or individual identifiers.
        """
        for field in requested_filters.keys():
            if field.lower() in PROHIBITED_BREAKDOWN_DIMENSIONS:
                raise PermissionError(
                    f"Prohibited Query: Dimension '{field}' is disabled by architecture. "
                    "Workplace surveillance is restricted to site-level aggregate rates."
                )

