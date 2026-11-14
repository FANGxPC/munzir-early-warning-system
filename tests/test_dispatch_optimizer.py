"""
Tests for Phase 16: Automated Municipal Cooling Fleet & EMS Pre-Staging Optimizer.
"""

from prahari.decision.dispatch_manifest import (
    export_dispatch_fhir_r4_task,
    format_dispatch_markdown_brief,
)
from prahari.decision.dispatch_optimizer import (
    DUBAI_MUNICIPAL_DEPOTS,
    DispatchRequest,
    optimize_municipal_dispatch,
)


def test_optimize_dispatch_jebel_ali_extreme_heat():
    """Tests resource optimization for 1,200 workers during an extreme heat alert."""
    req = DispatchRequest(
        alert_id="ALT-JA-20250818",
        site_id="SITE-JA-01",
        site_name="Jebel Ali Deepwater Port Terminal",
        district="Jebel Ali",
        latitude=24.9857,
        longitude=55.0872,
        workforce_size=1200,
        predicted_wbgt_peak=33.8,
        risk_tier="Warning",
        deployment_date="2025-08-19",
    )

    plan = optimize_municipal_dispatch(req)

    # 1,200 workers at 250 workers/bus -> 5 buses needed
    assert plan.total_cooling_buses == 5
    # 1,200 workers at 100 workers/trailer -> 12 misting trailers needed
    assert plan.total_misting_trailers == 12
    # 1,200 * 3.5L = 4.2 metric tons
    assert plan.total_water_tons == 4.2
    assert plan.total_electrolyte_sachets == 2400
    assert plan.dcas_ambulance_standby is True
    assert plan.operational_priority in ("High", "Immediate")
    assert plan.estimated_mobilization_cost_aed > 5000.0

    # Nearest depot (DEPOT-JA-01) should be assigned first
    first_alloc = plan.allocations[0]
    assert first_alloc.depot_id == "DEPOT-JA-01"
    assert first_alloc.cooling_buses_assigned > 0


def test_optimize_dispatch_moderate_heat():
    """Tests resource scaling for moderate risk (lower bus density)."""
    req = DispatchRequest(
        alert_id="ALT-AQ-20250818",
        site_id="SITE-AQ-01",
        site_name="Al Quoz Structural Steel Yard",
        district="Al Quoz",
        latitude=25.1324,
        longitude=55.2341,
        workforce_size=600,
        predicted_wbgt_peak=29.2,
        risk_tier="Watch",
        deployment_date="2025-08-19",
    )

    plan = optimize_municipal_dispatch(req)
    # Lower WBGT -> less intensive allocation
    assert plan.total_cooling_buses < 5
    assert plan.dcas_ambulance_standby is False
    assert plan.operational_priority == "Standard"


def test_format_dispatch_markdown_brief():
    """Verifies that the markdown brief is properly structured and cited."""
    req = DispatchRequest(
        alert_id="ALT-JA-20250818",
        site_id="SITE-JA-01",
        site_name="Jebel Ali Port",
        district="Jebel Ali",
        latitude=24.9857,
        longitude=55.0872,
        workforce_size=800,
        predicted_wbgt_peak=33.0,
        risk_tier="Warning",
        deployment_date="2025-08-19",
    )
    plan = optimize_municipal_dispatch(req)
    brief = format_dispatch_markdown_brief(plan, req)

    assert "# Dubai Municipality Operational Dispatch Manifest" in brief
    assert "Jebel Ali Port" in brief
    assert "Mobile Cooling Buses" in brief
    assert "MOHRE Ministerial Resolution No. 44 of 2022" in brief
    assert "| **" in brief  # Table formatting present


def test_export_dispatch_fhir_r4_task():
    """Verifies that the generated FHIR R4 Task resource complies with international standards."""
    req = DispatchRequest(
        alert_id="ALT-JA-20250818",
        site_id="SITE-JA-01",
        site_name="Jebel Ali Port",
        district="Jebel Ali",
        latitude=24.9857,
        longitude=55.0872,
        workforce_size=1000,
        predicted_wbgt_peak=34.0,
        risk_tier="Alert",
        deployment_date="2025-08-19",
    )
    plan = optimize_municipal_dispatch(req)
    fhir_task = export_dispatch_fhir_r4_task(plan, req)

    assert fhir_task["resourceType"] == "Task"
    assert fhir_task["status"] == "requested"
    assert fhir_task["intent"] == "order"
    assert fhir_task["priority"] == "stat"
    assert fhir_task["focus"]["reference"] == "Location/SITE-JA-01"
    assert fhir_task["requester"]["display"] == "Dubai Health Authority Public Health Surveillance Directorate"

    # Check input parameters
    input_types = [inp["type"]["text"] for inp in fhir_task["input"]]
    assert "cooling-buses-required" in input_types
    assert "potable-water-tons" in input_types
    assert "dcas-ambulance-standby" in input_types

