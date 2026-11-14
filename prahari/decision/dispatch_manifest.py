"""
Munzir Municipal Dispatch Manifest & HL7 FHIR R4 Task Exporter (Phase 16).
Converts operational resource staging plans into international FHIR R4 Task resources
and downloadable municipal command briefs.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from typing import Any, Dict, List

from prahari.decision.dispatch_optimizer import DispatchPlan, DispatchRequest


def format_dispatch_markdown_brief(plan: DispatchPlan, request: DispatchRequest) -> str:
    """Formats the dispatch plan into an executive municipal operations briefing."""
    md = [
        f"# Dubai Municipality Operational Dispatch Manifest: {plan.plan_id}",
        f"**Target Site:** {request.site_name} (`{request.site_id}`, {request.district})",
        f"**Operational Priority:** `{plan.operational_priority}` | **Associated Alert:** `{plan.alert_id}`",
        f"**Deployment Window:** {request.deployment_date} ({request.target_start_time_utc} – {request.target_end_time_utc} UTC)",
        "",
        "## 1. Summary of Allocated Prevention Assets",
        f"- **Mobile Cooling Buses:** {plan.total_cooling_buses} units (Air-conditioned shelter capacity for {request.workforce_size} workers)",
        f"- **Misting Fan Trailers:** {plan.total_misting_trailers} high-pressure evaporative cooling units",
        f"- **Chilled Potable Water Supply:** {plan.total_water_tons} Metric Tons ({plan.total_water_tons * 1000:.0f} Liters)",
        f"- **Oral Electrolyte Sachets:** {plan.total_electrolyte_sachets:,} units",
        f"- **DCAS Ambulance Standby:** {'REQUIRED (Pre-positioned at ' + str(plan.dcas_staging_coordinates) + ')' if plan.dcas_ambulance_standby else 'On Routine Dispatch'}",
        f"- **Estimated Mobilization Budget:** AED {plan.estimated_mobilization_cost_aed:,.2f}",
        "",
        "## 2. Depot Staging & Mobilization Route Order",
        "| Staging Depot | Distance | Cooling Buses | Misting Trailers | Water Tonnage | Mobilization Time |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for alloc in plan.allocations:
        md.append(
            f"| **{alloc.depot_name}** | {alloc.distance_km} km | {alloc.cooling_buses_assigned} buses | "
            f"{alloc.misting_trailers_assigned} trailers | {alloc.potable_water_tons} tons | ~{alloc.transit_duration_minutes} mins |"
        )

    md.extend([
        "",
        "## 3. Statutory & Regulatory Alignment",
        "- **Enforcement Basis:** UAE MOHRE Ministerial Resolution No. 44 of 2022 on Occupational Safety.",
        "- **Dubai Municipality Code of Construction Safety Practice:** Section 8 (Thermal Stress Management).",
        "- **Immediate Field Order:** Mandate on-site deployment of misting units prior to 10:00 AM local time.",
    ])

    return "\n".join(md)


def export_dispatch_fhir_r4_task(plan: DispatchPlan, request: DispatchRequest) -> Dict[str, Any]:
    """
    Converts a municipal dispatch plan into an international HL7 FHIR Release 4 Task resource.
    Complies with standard FHIR Task schema for smart city emergency dispatch intake.
    """
    fhir_task = {
        "resourceType": "Task",
        "id": plan.plan_id.lower().replace("-", "_"),
        "meta": {
            "profile": [
                "http://hl7.org/fhir/StructureDefinition/Task",
                "http://dha.gov.ae/fhir/StructureDefinition/dha-occupational-dispatch-task",
            ],
            "lastUpdated": plan.generated_at_utc,
        },
        "identifier": [
            {
                "system": "http://munzir.dha.gov.ae/dispatch",
                "value": plan.plan_id,
            }
        ],
        "basedOn": [
            {
                "reference": f"RiskAssessment/{plan.alert_id.lower()}",
                "display": f"Early Warning Alert {plan.alert_id}",
            }
        ],
        "status": "requested",
        "intent": "order",
        "priority": "stat" if plan.operational_priority == "Immediate" else "urgent",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "410617001",
                    "display": "Preventive intervention (procedure)",
                },
                {
                    "system": "http://munzir.dha.gov.ae/codes/dispatch",
                    "code": "municipal-cooling-dispatch",
                    "display": "Municipal Cooling Bus and Hydration Staging",
                },
            ],
            "text": "Municipal Mobile Cooling Bus and Hydration Asset Staging",
        },
        "focus": {
            "reference": f"Location/{request.site_id}",
            "display": request.site_name,
        },
        "for": {
            "reference": f"Group/{request.site_id}_workforce",
            "display": f"Frontline Cohort ({request.workforce_size} workers)",
        },
        "executionPeriod": {
            "start": f"{request.deployment_date}T{request.target_start_time_utc}:00Z",
            "end": f"{request.deployment_date}T{request.target_end_time_utc}:00Z",
        },
        "authoredOn": plan.generated_at_utc,
        "requester": {
            "reference": "Organization/dha-public-health",
            "display": "Dubai Health Authority Public Health Surveillance Directorate",
        },
        "owner": {
            "reference": "Organization/dubai-municipality-waste-environment",
            "display": "Dubai Municipality Environment & Emergency Operations",
        },
        "note": [
            {
                "text": (
                    f"Automated prevention trigger: Deploy {plan.total_cooling_buses} cooling buses, "
                    f"{plan.total_misting_trailers} misting trailers, and {plan.total_water_tons} tons potable water. "
                    f"Ambulance standby: {plan.dcas_ambulance_standby}."
                )
            }
        ],
        "input": [
            {
                "type": {"text": "cooling-buses-required"},
                "valueInteger": plan.total_cooling_buses,
            },
            {
                "type": {"text": "potable-water-tons"},
                "valueDecimal": plan.total_water_tons,
            },
            {
                "type": {"text": "dcas-ambulance-standby"},
                "valueBoolean": plan.dcas_ambulance_standby,
            },
            {
                "type": {"text": "mobilization-cost-aed"},
                "valueMoney": {
                    "value": plan.estimated_mobilization_cost_aed,
                    "currency": "AED",
                },
            },
        ],
    }

    return fhir_task

