"""
Munzir Automated Prevention Trigger: Municipal Cooling Fleet & EMS Optimizer (Phase 16).
Converts early warnings into an actionable, optimized municipal resource staging plan:
mobile cooling buses, misting trailers, hydration tonnage, and DCAS ambulance standby.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple


@dataclass(frozen=True)
class MunicipalDepot:
    """Municipal maintenance and emergency equipment staging depot."""
    depot_id: str
    name: str
    latitude: float
    longitude: float
    available_cooling_buses: int
    available_misting_trailers: int
    water_tanker_capacity_tons: float


@dataclass
class DispatchRequest:
    """Operational trigger request generated from an active alert."""
    alert_id: str
    site_id: str
    site_name: str
    district: str
    latitude: float
    longitude: float
    workforce_size: int
    predicted_wbgt_peak: float
    risk_tier: str  # Watch, Warning, Alert
    deployment_date: str  # YYYY-MM-DD
    target_start_time_utc: str = "07:00"
    target_end_time_utc: str = "15:00"


@dataclass
class StagingAllocation:
    """Allocated resource deployment from a specific municipal depot."""
    depot_id: str
    depot_name: str
    distance_km: float
    cooling_buses_assigned: int
    misting_trailers_assigned: int
    potable_water_tons: float
    electrolyte_sachets: int
    transit_duration_minutes: int


@dataclass
class DispatchPlan:
    """Complete municipal and emergency services dispatch plan."""
    plan_id: str
    alert_id: str
    site_id: str
    generated_at_utc: str
    allocations: List[StagingAllocation]
    total_cooling_buses: int
    total_misting_trailers: int
    total_water_tons: float
    total_electrolyte_sachets: int
    dcas_ambulance_standby: bool
    dcas_staging_coordinates: Tuple[float, float]
    estimated_mobilization_cost_aed: float
    operational_priority: str  # Standard, High, Immediate


# Dubai Municipality Official Maintenance & Emergency Staging Depots
DUBAI_MUNICIPAL_DEPOTS: Dict[str, MunicipalDepot] = {
    "DEPOT-JA-01": MunicipalDepot(
        depot_id="DEPOT-JA-01",
        name="Jebel Ali Municipal Operations Yard",
        latitude=25.0080,
        longitude=55.1120,
        available_cooling_buses=12,
        available_misting_trailers=20,
        water_tanker_capacity_tons=150.0,
    ),
    "DEPOT-AQ-01": MunicipalDepot(
        depot_id="DEPOT-AQ-01",
        name="Al Quoz Central Fleet Depot",
        latitude=25.1480,
        longitude=55.2420,
        available_cooling_buses=15,
        available_misting_trailers=25,
        water_tanker_capacity_tons=200.0,
    ),
    "DEPOT-WAR-01": MunicipalDepot(
        depot_id="DEPOT-WAR-01",
        name="Al Warsan Regional Emergency Hub",
        latitude=25.1610,
        longitude=55.4020,
        available_cooling_buses=18,
        available_misting_trailers=30,
        water_tanker_capacity_tons=250.0,
    ),
}


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Helper for great-circle distance."""
    r = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return r * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def optimize_municipal_dispatch(
    request: DispatchRequest,
    available_depots: Optional[Dict[str, MunicipalDepot]] = None,
) -> DispatchPlan:
    """
    Optimizes municipal cooling assets and ambulance standby allocation.
    Matches nearest available municipal depot, calculating bus ratios, water tonnage,
    and DCAS pre-deployment positioning.
    """
    if available_depots is None:
        available_depots = DUBAI_MUNICIPAL_DEPOTS

    # Determine resource requirements based on workforce size & heat intensity
    # Standard: 1 cooling bus per 250 workers; 1 misting trailer per 100 workers
    if request.predicted_wbgt_peak >= 32.0 or request.risk_tier == "Alert":
        bus_ratio = 250
        trailer_ratio = 100
        priority = "Immediate"
        ambulance_standby = True
    elif request.predicted_wbgt_peak >= 30.0 or request.risk_tier == "Warning":
        bus_ratio = 350
        trailer_ratio = 150
        priority = "High"
        ambulance_standby = True
    else:
        bus_ratio = 500
        trailer_ratio = 250
        priority = "Standard"
        ambulance_standby = False

    needed_buses = max(1, math.ceil(request.workforce_size / bus_ratio)) if request.workforce_size > 0 else 0
    needed_trailers = max(1, math.ceil(request.workforce_size / trailer_ratio)) if request.workforce_size > 0 else 0

    # Water logistics: 3.5 Liters per worker = 3.5 kg = 0.0035 metric tons
    total_water_tons = round(request.workforce_size * 0.0035, 2)
    total_electrolytes = request.workforce_size * 2  # 2 sachets per shift

    # Rank depots by distance to target site
    depot_distances: List[Tuple[MunicipalDepot, float]] = []
    for depot in available_depots.values():
        dist = _haversine_km(depot.latitude, depot.longitude, request.latitude, request.longitude)
        depot_distances.append((depot, dist))

    depot_distances.sort(key=lambda x: x[1])

    # Greedy allocation from nearest depots
    remaining_buses = needed_buses
    remaining_trailers = needed_trailers
    remaining_water = total_water_tons
    remaining_electrolytes = total_electrolytes

    allocations: List[StagingAllocation] = []

    for depot, dist in depot_distances:
        if remaining_buses == 0 and remaining_trailers == 0:
            break

        buses_from_here = min(remaining_buses, depot.available_cooling_buses)
        trailers_from_here = min(remaining_trailers, depot.available_misting_trailers)
        water_from_here = round(min(remaining_water, depot.water_tanker_capacity_tons), 2)
        sachets_from_here = int(remaining_electrolytes * (water_from_here / (total_water_tons or 1.0)))

        # Average speed 40 km/h in urban industrial corridors
        transit_mins = int((dist / 40.0) * 60.0) + 15  # 15m mobilization buffer

        allocations.append(
            StagingAllocation(
                depot_id=depot.depot_id,
                depot_name=depot.name,
                distance_km=round(dist, 1),
                cooling_buses_assigned=buses_from_here,
                misting_trailers_assigned=trailers_from_here,
                potable_water_tons=water_from_here,
                electrolyte_sachets=sachets_from_here,
                transit_duration_minutes=transit_mins,
            )
        )

        remaining_buses -= buses_from_here
        remaining_trailers -= trailers_from_here
        remaining_water = max(0.0, round(remaining_water - water_from_here, 2))
        remaining_electrolytes -= sachets_from_here

    actual_buses = sum(a.cooling_buses_assigned for a in allocations)
    actual_trailers = sum(a.misting_trailers_assigned for a in allocations)

    # Estimate mobilization costs (AED 1,200 per bus shift, AED 400 per trailer, AED 0.25/L water)
    est_cost = (
        (actual_buses * 1200.0)
        + (actual_trailers * 400.0)
        + (total_water_tons * 1000.0 * 0.25)
        + (total_electrolytes * 1.50)
    )

    # DCAS Ambulance Standby coordinates (offset 150m from site centroid)
    dcas_coords = (round(request.latitude + 0.0012, 4), round(request.longitude + 0.0012, 4))

    now_utc = datetime.now(timezone.utc)
    plan_id = f"DISPATCH-{request.site_id}-{now_utc.strftime('%Y%m%d%H%M')}"

    return DispatchPlan(
        plan_id=plan_id,
        alert_id=request.alert_id,
        site_id=request.site_id,
        generated_at_utc=now_utc.isoformat(),
        allocations=allocations,
        total_cooling_buses=actual_buses,
        total_misting_trailers=actual_trailers,
        total_water_tons=total_water_tons,
        total_electrolyte_sachets=total_electrolytes,
        dcas_ambulance_standby=ambulance_standby,
        dcas_staging_coordinates=dcas_coords,
        estimated_mobilization_cost_aed=round(est_cost, 2),
        operational_priority=priority,
    )

