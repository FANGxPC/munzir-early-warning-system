"""
HL7 FHIR R4 Surveillance Export Adapter for Munzir (منذر).
Converts calibrated early-warning alerts and aggregated syndromic observations into
standards-compliant HL7 FHIR R4 resources (MeasureReport, RiskAssessment, Bundle)
for seamless integration with national health information exchanges (e.g. DHA NABIDH,
Abu Dhabi Malaffi, CDC NSSP, WHO EIOS).
"""

from datetime import datetime, timezone
from typing import Dict, List, Any, Optional
from uuid import uuid4

from prahari.detection.l5_policy import PrahariAlert, MunzirAlert, AlertSeverity
from prahari.models.canonical import SignalObservation


class FHIRSurveillanceAdapter:
    """
    Translates Munzir internal data representations into standard HL7 FHIR Release 4
    JSON representations, preserving privacy guarantees (aggregate counts only).
    """

    SYSTEM_MUNZIR_MEASURES = "urn:ietf:rfc:3986:urn:munzir:surveillance:measures"
    SYSTEM_SNOMED_CT = "http://snomed.info/sct"
    SYSTEM_LOINC = "http://loinc.org"
    SYSTEM_RISK_CODE = "http://terminology.hl7.org/CodeSystem/risk-probability"

    @classmethod
    def alert_to_risk_assessment(cls, alert: PrahariAlert) -> Dict[str, Any]:
        """
        Converts a MunzirAlert into an HL7 FHIR R4 RiskAssessment resource.
        """
        severity_map = {
            AlertSeverity.WATCH: {
                "system": cls.SYSTEM_RISK_CODE,
                "code": "low",
                "display": "Low risk / Active Watch"
            },
            AlertSeverity.WARNING: {
                "system": cls.SYSTEM_RISK_CODE,
                "code": "moderate",
                "display": "Moderate risk / Preventive Warning"
            },
            AlertSeverity.ALERT: {
                "system": cls.SYSTEM_RISK_CODE,
                "code": "high",
                "display": "High risk / Outbreak Alert"
            },
            AlertSeverity.NONE: {
                "system": cls.SYSTEM_RISK_CODE,
                "code": "negligible",
                "display": "Baseline / Normal"
            }
        }

        # Map alert type to standard SNOMED/LOINC codes where applicable
        outcome_concepts = {
            "heat_cluster": {
                "system": cls.SYSTEM_SNOMED_CT,
                "code": "403190006",
                "display": "Heat-related illness risk"
            },
            "respiratory_surge": {
                "system": cls.SYSTEM_SNOMED_CT,
                "code": "50043002",
                "display": "Respiratory tract disorder surge"
            },
            "infectious_cluster": {
                "system": cls.SYSTEM_SNOMED_CT,
                "code": "40733004",
                "display": "Infectious disease cluster"
            },
            "cluster": {
                "system": cls.SYSTEM_SNOMED_CT,
                "code": "64572001",
                "display": "Epidemiological aberration cluster"
            }
        }
        outcome_concept = outcome_concepts.get(alert.alert_type, outcome_concepts["cluster"])

        risk_level = severity_map.get(alert.severity, severity_map[AlertSeverity.WATCH])

        risk_assessment = {
            "resourceType": "RiskAssessment",
            "id": f"risk-{alert.alert_id.lower().replace('_', '-')}",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/RiskAssessment"
                ],
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "identifier": [
                {
                    "system": "urn:munzir:alert-id",
                    "value": alert.alert_id
                }
            ],
            "status": "final",
            "subject": {
                "reference": f"Location/{alert.geo_ids[0] if alert.geo_ids else 'UNKNOWN'}",
                "display": f"Spatial Jurisdictions: {', '.join(alert.geo_ids)}"
            },
            "occurrenceDateTime": f"{alert.obs_date}T00:00:00Z",
            "basis": [
                {
                    "display": f"Data Quality Status: {alert.dq_status.upper()}"
                }
            ],
            "prediction": [
                {
                    "outcome": {
                        "coding": [outcome_concept],
                        "text": alert.alert_type.replace("_", " ").title()
                    },
                    "probabilityDecimal": round(float(alert.probability), 4),
                    "qualitativeRisk": {
                        "coding": [risk_level],
                        "text": alert.severity.value.upper()
                    },
                    "whenPeriod": {
                        "start": f"{alert.obs_date}T00:00:00Z"
                    },
                    "rationale": (
                        f"Multi-signal fusion model calibrated probability: {round(alert.probability*100, 1)}% "
                        f"[90% Conformal CI: {round(alert.ci_low*100, 1)}% - {round(alert.ci_high*100, 1)}%]. "
                        f"Top contributing features: {', '.join(f'{k} ({round(v, 2)})' for k, v in list(alert.signal_contributions.items())[:3])}."
                    )
                }
            ],
            "mitigation": alert.recommended_action,
            "note": [
                {
                    "text": f"Designated Primary Responder: {alert.owner_role}"
                }
            ]
        }
        return risk_assessment

    @classmethod
    def observations_to_measure_report(
        cls,
        observations: List[SignalObservation],
        district_id: str,
        period_start: str,
        period_end: str,
    ) -> Dict[str, Any]:
        """
        Converts aggregate SignalObservation records into an HL7 FHIR R4 MeasureReport summary.
        Complies with aggregate surveillance reporting standards (no individual patient rows).
        """
        # Aggregate counts and scores by signal_type
        groups: Dict[str, Dict[str, float]] = {}
        for obs in observations:
            st = obs.signal_type
            if st not in groups:
                groups[st] = {"count": 0.0, "denominator": 0.0, "records": 0}
            groups[st]["count"] += obs.value
            groups[st]["denominator"] += (obs.denominator or 0.0)
            groups[st]["records"] += 1

        measure_groups = []
        for signal_type, data in sorted(groups.items()):
            denom = data["denominator"]
            score = (data["count"] / denom) if denom > 0 else data["count"]

            measure_groups.append({
                "code": {
                    "coding": [
                        {
                            "system": cls.SYSTEM_MUNZIR_MEASURES,
                            "code": signal_type,
                            "display": signal_type.replace("_", " ").title()
                        }
                    ]
                },
                "population": [
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "initial-population",
                                    "display": "Initial Population / Workforce at Risk"
                                }
                            ]
                        },
                        "count": int(denom) if denom > 0 else int(data["records"])
                    },
                    {
                        "code": {
                            "coding": [
                                {
                                    "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                                    "code": "numerator",
                                    "display": "Observed Aggregate Count"
                                }
                            ]
                        },
                        "count": int(data["count"])
                    }
                ],
                "measureScore": {
                    "value": round(float(score), 4)
                }
            })

        measure_report = {
            "resourceType": "MeasureReport",
            "id": f"mr-{district_id.lower().replace('_', '-')}-{str(uuid4())[:8]}",
            "meta": {
                "profile": [
                    "http://hl7.org/fhir/StructureDefinition/MeasureReport"
                ],
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "status": "complete",
            "type": "summary",
            "measure": f"{cls.SYSTEM_MUNZIR_MEASURES}:syndromic-heat-resilience",
            "subject": {
                "reference": f"Location/{district_id}",
                "display": f"Jurisdiction: {district_id}"
            },
            "date": datetime.now(timezone.utc).isoformat(),
            "period": {
                "start": f"{period_start}T00:00:00Z",
                "end": f"{period_end}T23:59:59Z"
            },
            "group": measure_groups
        }
        return measure_report

    @classmethod
    def create_surveillance_bundle(
        cls,
        alerts: List[PrahariAlert],
        observations: Optional[List[SignalObservation]] = None,
        district_id: str = "UAE-REGION",
        period_start: str = "2026-06-01",
        period_end: str = "2026-06-07"
    ) -> Dict[str, Any]:
        """
        Creates a complete HL7 FHIR R4 Bundle containing RiskAssessments and
        MeasureReports for automated export to external public health registries.
        """
        entries = []

        # Add RiskAssessments for each active alert
        for alert in alerts:
            ra = cls.alert_to_risk_assessment(alert)
            entries.append({
                "fullUrl": f"urn:uuid:{uuid4()}",
                "resource": ra
            })

        # Add MeasureReport if observations provided
        if observations:
            mr = cls.observations_to_measure_report(
                observations=observations,
                district_id=district_id,
                period_start=period_start,
                period_end=period_end
            )
            entries.append({
                "fullUrl": f"urn:uuid:{uuid4()}",
                "resource": mr
            })

        bundle = {
            "resourceType": "Bundle",
            "id": f"munzir-bundle-{str(uuid4())[:8]}",
            "meta": {
                "lastUpdated": datetime.now(timezone.utc).isoformat()
            },
            "type": "collection",
            "total": len(entries),
            "entry": entries
        }
        return bundle

