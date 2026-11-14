"""
Role-Based Access Control (RBAC) and Privacy Gating for PRAHARI.
Implements Entra ID app roles and strict privacy boundaries:
  - surveillance_officer: Full epidemiological & clinical syndromic access.
  - occupational_health: Workplace sector & district aggregate data, WBGT, site aggregate rates.
  - employer_safety: Strictly own registered sites only, rates per 1,000, cohort >= 50,
                     strictly prohibited from accessing district clinical data or sub-site breakdowns.
  - regulator: District policy & compliance view, thermal thresholds, multi-site heat warnings.
  - public: Differential-privacy aggregate releases only (Laplace noise, no workplace/clinic identifiers).
  - auditor: Immutable audit log inspector, view history, access logs, acknowledgement records.
"""

from enum import Enum
from typing import Optional, List, Dict, Any, Set
from pydantic import BaseModel, Field
from fastapi import HTTPException, Header, Security, Depends, status


class EntraRole(str, Enum):
    """The 6 official Entra ID application roles specified in PRAHARI implementation plan."""
    SURVEILLANCE_OFFICER = "surveillance_officer"
    OCCUPATIONAL_HEALTH = "occupational_health"
    EMPLOYER_SAFETY = "employer_safety"
    REGULATOR = "regulator"
    PUBLIC = "public"
    AUDITOR = "auditor"


class AuthenticatedUser(BaseModel):
    """Authenticated user context extracted from Entra ID JWT claims."""
    user_id: str = Field(default="demo-user-01")
    email: str = Field(default="officer@health.gov.ae")
    role: EntraRole = Field(default=EntraRole.SURVEILLANCE_OFFICER)
    employer_id: Optional[str] = Field(
        default=None,
        description="Authorized site/employer ID if role is employer_safety (e.g. SITE-JA-01)"
    )
    organization: str = Field(default="Dubai Health Authority")
    purpose: str = Field(default="public_health_surveillance")


# Forbidden query parameters for occupational privacy (to prevent sub-site / individual tracking)
PROHIBITED_SUBSITE_PARAMS: Set[str] = {
    "worker_id", "employee_id", "subteam", "shift_id", "gang_id",
    "crew_id", "age_group", "gender", "nationality", "patient_id"
}

# Clinical syndromic signals that employer_safety is strictly forbidden from accessing
RESTRICTED_CLINICAL_SIGNALS: Set[str] = {
    "clinical_resp", "clinical_gi", "clinical_fever", "lab_pos", "otc_pharmacy"
}


def get_current_user(
    x_role: Optional[str] = Header(default="surveillance_officer", alias="X-Role"),
    x_user_id: Optional[str] = Header(default="user-surveillance-01", alias="X-User-ID"),
    x_employer_id: Optional[str] = Header(default="SITE-JA-01", alias="X-Employer-ID"),
    x_purpose: Optional[str] = Header(default="epidemiological_surveillance", alias="X-Purpose"),
) -> AuthenticatedUser:
    """
    Extracts and validates simulated Entra ID authentication context from HTTP headers.
    In production, this extracts verified claims from the Azure Entra ID Bearer token.
    """
    try:
        role_enum = EntraRole(x_role.lower() if x_role else "surveillance_officer")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid Entra ID role '{x_role}'. Allowed: {[r.value for r in EntraRole]}"
        )

    # For employer_safety, assign default authorized site if not explicitly specified
    emp_id = x_employer_id
    if role_enum == EntraRole.EMPLOYER_SAFETY and not emp_id:
        emp_id = "SITE-JA-01"

    org_mapping = {
        EntraRole.SURVEILLANCE_OFFICER: "Dubai Health Authority (Epi Surveillance)",
        EntraRole.OCCUPATIONAL_HEALTH: "Ministry of Human Resources & Emiratisation (MOHRE)",
        EntraRole.EMPLOYER_SAFETY: f"Registered Employer Worksites ({emp_id})",
        EntraRole.REGULATOR: "Dubai Health Regulatory Agency / OSHA Liaison",
        EntraRole.PUBLIC: "Public Open Data Portal",
        EntraRole.AUDITOR: "Office of the Inspector General / Audit & Compliance",
    }

    return AuthenticatedUser(
        user_id=x_user_id or "demo-user",
        email=f"{role_enum.value}@prahari.gov.ae",
        role=role_enum,
        employer_id=emp_id if role_enum == EntraRole.EMPLOYER_SAFETY else None,
        organization=org_mapping.get(role_enum, "Munzir Surveillance System"),
        purpose=x_purpose or "authorized_operation",
    )


class RequireRoles:
    """Dependency for securing endpoints based on allowed Entra ID roles."""

    def __init__(self, allowed_roles: List[EntraRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: AuthenticatedUser = Depends(get_current_user)) -> AuthenticatedUser:
        if user.role not in self.allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access Denied: Role '{user.role.value}' does not have permission for this endpoint. "
                    f"Required: {[r.value for r in self.allowed_roles]}"
                )
            )
        return user


def enforce_employer_privacy_boundary(
    user: AuthenticatedUser,
    target_geo_id: Optional[str] = None,
    query_params: Optional[Dict[str, Any]] = None,
    signal_type: Optional[str] = None,
) -> None:
    """
    Strict privacy boundary validation:
    1. Prohibits employer_safety from accessing district clinical data.
    2. Prohibits employer_safety from accessing sites other than their own authorized site.
    3. Prohibits sub-site / sub-cohort parameters that could enable individual re-identification.
    """
    if user.role != EntraRole.EMPLOYER_SAFETY:
        return

    # Check 1: Clinical signal restriction
    if signal_type and signal_type.lower() in RESTRICTED_CLINICAL_SIGNALS:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Access Denied: Employer Safety role is strictly prohibited from accessing "
                f"district clinical syndromic data ('{signal_type}') under health privacy law."
            )
        )

    # Check 2: Site authorization restriction
    if target_geo_id:
        if not target_geo_id.startswith("SITE-"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access Denied: Employer Safety role cannot access district/regional data ('{target_geo_id}'). "
                    "Access is limited strictly to authorized worksites."
                )
            )
        if user.employer_id and target_geo_id != user.employer_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Access Denied: Employer Safety role is authorized only for site '{user.employer_id}', "
                    f"not for site '{target_geo_id}'."
                )
            )

    # Check 3: Sub-site / individual identification parameter restriction
    if query_params:
        for param in query_params.keys():
            if param.lower() in PROHIBITED_SUBSITE_PARAMS:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=(
                        f"Access Denied: Parameter '{param}' is strictly forbidden. Sub-site and sub-cohort "
                        "breakdowns are prohibited to prevent worker re-identification."
                    )
                )

