"""
RACI Stakeholder Role Definitions and Assignment Matrix.
Defines public health and occupational safety governance roles, permissions,
and notification hierarchies according to WHO and OSHA operational standards.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Any, Optional

from prahari.detection.l5_policy import AlertSeverity


class RoleType(str, Enum):
    DISTRICT_SURVEILLANCE_OFFICER = "District Surveillance Officer"
    DISTRICT_HEALTH_OFFICER = "District Health Officer"
    OCCUPATIONAL_HEALTH_OFFICER = "Occupational Health Officer / Factory Inspectorate"
    SITE_SAFETY_OFFICER = "Site Safety Officer"
    EMPLOYER_HR = "Employer HR (Aggregate Only)"
    POLLUTION_CONTROL_LIAISON = "Pollution Control Liaison"
    PUBLIC_ADVISORY_LIAISON = "Public Advisory Liaison"
    DATA_QUALITY_OFFICER = "Data Quality Officer"


@dataclass
class RACIAssignment:
    """RACI governance mapping for an incident / alert tier."""
    responsible: str                     # Lead who performs the action (R)
    accountable: str                     # Approver with ultimate authority (A)
    consulted: List[str]                 # Subject matter advisors (C)
    informed: List[str]                  # Stakeholders notified for awareness (I)


class RACIRoleMatrix:
    """
    Resolves official RACI stakeholders based on alert category,
    severity level, and site vs. district jurisdiction.
    """

    @staticmethod
    def get_raci(
        alert_type: str,
        severity: AlertSeverity,
        is_site: bool = False,
    ) -> RACIAssignment:
        """Resolves responsible stakeholders according to public health governance."""
        sev_val = severity.value if isinstance(severity, AlertSeverity) else str(severity).lower()

        # 1. Worksite Heat Cluster
        if alert_type == "heat_cluster" or (is_site and alert_type != "data_artefact"):
            if sev_val == "alert":
                return RACIAssignment(
                    responsible=RoleType.SITE_SAFETY_OFFICER.value,
                    accountable="General Contractor Project Director",
                    consulted=[
                        RoleType.OCCUPATIONAL_HEALTH_OFFICER.value,
                        "District Emergency Medical Services (EMS)",
                    ],
                    informed=[
                        RoleType.DISTRICT_HEALTH_OFFICER.value,
                        RoleType.EMPLOYER_HR.value,
                        RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
                    ],
                )
            else:  # Warning or Watch
                return RACIAssignment(
                    responsible=RoleType.SITE_SAFETY_OFFICER.value,
                    accountable="Construction Project Director / Employer Management",
                    consulted=[
                        RoleType.OCCUPATIONAL_HEALTH_OFFICER.value,
                    ],
                    informed=[
                        RoleType.EMPLOYER_HR.value,
                        RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
                    ],
                )

        # 2. Respiratory Surge (Air Quality Driven)
        elif alert_type == "respiratory_surge":
            if sev_val == "alert":
                return RACIAssignment(
                    responsible=RoleType.DISTRICT_HEALTH_OFFICER.value,
                    accountable="Director General of Health Authority",
                    consulted=[
                        RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
                        RoleType.POLLUTION_CONTROL_LIAISON.value,
                        "Hospital Emergency Department Directors",
                    ],
                    informed=[
                        RoleType.PUBLIC_ADVISORY_LIAISON.value,
                        RoleType.OCCUPATIONAL_HEALTH_OFFICER.value,
                        "Disaster Management Committee",
                    ],
                )
            else:
                return RACIAssignment(
                    responsible=RoleType.DISTRICT_HEALTH_OFFICER.value,
                    accountable="Director of Public Health Surveillance",
                    consulted=[
                        RoleType.POLLUTION_CONTROL_LIAISON.value,
                        RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
                    ],
                    informed=[
                        RoleType.PUBLIC_ADVISORY_LIAISON.value,
                        "Primary Care Clinic Directors",
                        RoleType.SITE_SAFETY_OFFICER.value,
                    ],
                )

        # 3. Infectious / Point-Source Enteric Cluster
        elif alert_type == "infectious_cluster":
            if sev_val == "alert":
                return RACIAssignment(
                    responsible=RoleType.DISTRICT_SURVEILLANCE_OFFICER.value + " (Rapid Response Team Leader)",
                    accountable="Public Health Authority Director",
                    consulted=[
                        "Municipal Health & Hygiene Inspectorate",
                        "Public Health Reference Laboratory",
                        "Hospital Epidemiologist",
                    ],
                    informed=[
                        RoleType.DISTRICT_HEALTH_OFFICER.value,
                        "Facility Executive Management",
                        RoleType.OCCUPATIONAL_HEALTH_OFFICER.value,
                    ],
                )
            else:
                return RACIAssignment(
                    responsible=RoleType.DISTRICT_SURVEILLANCE_OFFICER.value + " (Rapid Response Team)",
                    accountable="Chief Medical Officer / Public Health Authority",
                    consulted=[
                        "Facility Occupational Health Nurse",
                        "Municipal Food Safety Inspectorate",
                    ],
                    informed=[
                        "Facility General Manager",
                        RoleType.SITE_SAFETY_OFFICER.value,
                        RoleType.DISTRICT_HEALTH_OFFICER.value,
                    ],
                )

        # 4. Data Quality Artefact (Backlog Dump)
        elif alert_type == "data_artefact":
            return RACIAssignment(
                responsible=RoleType.DATA_QUALITY_OFFICER.value,
                accountable="Health Informatics Director",
                consulted=[
                    "Facility Electronic Health Record (EHR) Administrator",
                ],
                informed=[
                    RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
                ],
            )

        # Default fallback
        return RACIAssignment(
            responsible=RoleType.DISTRICT_SURVEILLANCE_OFFICER.value,
            accountable=RoleType.DISTRICT_HEALTH_OFFICER.value,
            consulted=[RoleType.OCCUPATIONAL_HEALTH_OFFICER.value],
            informed=[RoleType.EMPLOYER_HR.value],
        )

