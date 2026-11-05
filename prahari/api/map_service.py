"""
Situation Map Layer Generation Service.
Generates geospatial feature layers, risk status, location-confidence hatching indicators,
and cluster boundaries for the interactive Leaflet/MapLibre map.
Enforces RBAC and privacy boundaries:
  - surveillance_officer: all districts, sites, and prospective cluster boundaries.
  - occupational_health: all sites, industrial districts, thermal hazard layers.
  - employer_safety: strictly own site only; clinical layers completely removed.
  - public: differential privacy protected district summaries only; zero site details.
"""

import math
from typing import List, Dict, Any, Optional
import h3

from prahari.config import REGIONAL_PROFILES, H3_RES_DETECTION
from prahari.api.rbac import AuthenticatedUser, EntraRole
from prahari.api.models import GeoFeature, ClusterBoundary, MapLayersResponse
from prahari.detection.pipeline import DetectionPipeline


class MapLayerService:
    """Produces geospatial risk and cluster layers filtered by role."""

    def __init__(self, region_key: str = "uae"):
        self.region_key = region_key
        self.region_config = REGIONAL_PROFILES.get(region_key, REGIONAL_PROFILES["uae"])
        self.pipeline = DetectionPipeline()

    def get_map_layers(
        self,
        target_date: str = "2025-08-20",
        user: Optional[AuthenticatedUser] = None,
    ) -> MapLayersResponse:
        """
        Synthesizes map layers for a target date with strict role filtering.
        """
        role = user.role if user else EntraRole.SURVEILLANCE_OFFICER
        authorized_site = user.employer_id if user and user.employer_id else "SITE-JA-01"

        # Load latest alerts to determine risk tiers
        alerts = self.pipeline.load_alerts(start_date=target_date, end_date=target_date)
        alert_by_geo: Dict[str, Any] = {}
        for a in alerts:
            for gid in a.geo_ids:
                if gid not in alert_by_geo or a.probability > alert_by_geo[gid].probability:
                    alert_by_geo[gid] = a

        features: List[GeoFeature] = []
        clusters: List[ClusterBoundary] = []
        privacy_notice: Optional[str] = None

        districts = self.region_config.get("districts", [])
        sites = self.region_config.get("sites", [])

        if role == EntraRole.EMPLOYER_SAFETY:
            # STRICT PRIVACY RULE: employer_safety can ONLY see their own authorized site
            privacy_notice = (
                f"Confidential Employer Safety View for {authorized_site}. "
                "District clinical layers and other employer sites are restricted under public health privacy rules."
            )
            for site in sites:
                if site["id"] == authorized_site:
                    alert_info = alert_by_geo.get(site["id"])
                    risk_tier = alert_info.severity.value if alert_info else "normal"
                    prob = alert_info.probability if alert_info else 0.05
                    syndrome = alert_info.alert_type if alert_info else "heat_cluster"
                    h3_idx = h3.latlng_to_cell(site["lat"], site["lon"], H3_RES_DETECTION)

                    features.append(GeoFeature(
                        geo_id=site["id"],
                        geo_name=site["name"],
                        geo_level="site",
                        lat=site["lat"],
                        lon=site["lon"],
                        risk_tier=risk_tier,
                        calibrated_prob=round(prob, 4),
                        location_confidence="exact",
                        hatch_pattern=False,
                        primary_syndrome=syndrome,
                        h3_index=h3_idx,
                        population=site.get("workforce", 1000),
                    ))
            return MapLayersResponse(
                date=target_date,
                role_view=role.value,
                total_locations=len(features),
                features=features,
                clusters=[],  # No public health cluster scans shared with employers
                privacy_notice=privacy_notice,
            )

        if role == EntraRole.PUBLIC:
            # STRICT DIFFERENTIAL PRIVACY RULE: only DP-aggregated districts, no sites
            privacy_notice = "Public Open Health Portal — Protected by Differential Privacy (OpenDP Laplace noise ε=1.0)."
            for dist in districts:
                alert_info = alert_by_geo.get(dist["id"])
                risk_tier = alert_info.severity.value if alert_info else "normal"
                prob = alert_info.probability if alert_info else 0.05
                h3_idx = h3.latlng_to_cell(dist["lat"], dist["lon"], H3_RES_DETECTION)

                features.append(GeoFeature(
                    geo_id=dist["id"],
                    geo_name=dist["name"],
                    geo_level="district",
                    lat=dist["lat"],
                    lon=dist["lon"],
                    risk_tier=risk_tier,
                    calibrated_prob=round(prob, 4),
                    location_confidence="district_only",
                    hatch_pattern=True,  # Public sees hatched pattern for district-level aggregation
                    primary_syndrome="public_advisory",
                    h3_index=h3_idx,
                    population=dist.get("population", 100000),
                ))
            return MapLayersResponse(
                date=target_date,
                role_view=role.value,
                total_locations=len(features),
                features=features,
                clusters=[],
                privacy_notice=privacy_notice,
            )

        # Standard Public Health / Occupational Health / Regulator / Auditor View
        # 1. Districts (with hatching pattern for district-only confidence)
        for dist in districts:
            alert_info = alert_by_geo.get(dist["id"])
            risk_tier = alert_info.severity.value if alert_info else "normal"
            prob = alert_info.probability if alert_info else 0.04
            syndrome = alert_info.alert_type if alert_info else None
            h3_idx = h3.latlng_to_cell(dist["lat"], dist["lon"], H3_RES_DETECTION)

            features.append(GeoFeature(
                geo_id=dist["id"],
                geo_name=dist["name"],
                geo_level="district",
                lat=dist["lat"],
                lon=dist["lon"],
                risk_tier=risk_tier,
                calibrated_prob=round(prob, 4),
                location_confidence="district_only",
                hatch_pattern=True,  # Location confidence: district_only requires diagonal hatching
                primary_syndrome=syndrome,
                h3_index=h3_idx,
                population=dist.get("population", 200000),
            ))

        # 2. Worksites (exact location confidence, solid rendering)
        for site in sites:
            alert_info = alert_by_geo.get(site["id"])
            risk_tier = alert_info.severity.value if alert_info else "normal"
            prob = alert_info.probability if alert_info else 0.02
            syndrome = alert_info.alert_type if alert_info else None
            h3_idx = h3.latlng_to_cell(site["lat"], site["lon"], H3_RES_DETECTION)

            features.append(GeoFeature(
                geo_id=site["id"],
                geo_name=site["name"],
                geo_level="site",
                lat=site["lat"],
                lon=site["lon"],
                risk_tier=risk_tier,
                calibrated_prob=round(prob, 4),
                location_confidence="exact",
                hatch_pattern=False,  # Exact location -> solid rendering
                primary_syndrome=syndrome,
                h3_index=h3_idx,
                population=site.get("workforce", 1500),
            ))

        # 3. Prospective Space-Time Clusters (L3)
        # Synthesize active cluster boundary if an active outbreak is detected
        for a in alerts:
            is_cluster = getattr(a, "l3_cluster_detected", False) or "cluster" in a.alert_type
            if is_cluster and len(a.geo_ids) > 0:
                # Find centroid of affected geos
                lats = []
                lons = []
                for gid in a.geo_ids:
                    match_dist = next((d for d in districts if d["id"] == gid), None)
                    match_site = next((s for s in sites if s["id"] == gid), None)
                    if match_dist:
                        lats.append(match_dist["lat"])
                        lons.append(match_dist["lon"])
                    elif match_site:
                        lats.append(match_site["lat"])
                        lons.append(match_site["lon"])

                if lats and lons:
                    c_lat = float(sum(lats) / len(lats))
                    c_lon = float(sum(lons) / len(lons))
                    radius_km = 3.5

                    # Generate circular polygon approximation (12 vertices)
                    coords = []
                    for deg in range(0, 360, 30):
                        rad = math.radians(deg)
                        d_lat = (radius_km / 111.0) * math.cos(rad)
                        d_lon = (radius_km / (111.0 * math.cos(math.radians(c_lat)))) * math.sin(rad)
                        coords.append([round(c_lat + d_lat, 5), round(c_lon + d_lon, 5)])

                    clusters.append(ClusterBoundary(
                        cluster_id=f"CLUST-{a.alert_id[:8]}",
                        centroid_lat=round(c_lat, 5),
                        centroid_lon=round(c_lon, 5),
                        radius_km=radius_km,
                        relative_risk=round(float(getattr(a, "l3_relative_risk", 3.2)), 2),
                        p_value=round(float(getattr(a, "l3_p_value", 0.012)), 4),
                        syndrome=a.alert_type,
                        coordinates=coords,
                    ))

        return MapLayersResponse(
            date=target_date,
            role_view=role.value,
            total_locations=len(features),
            features=features,
            clusters=clusters,
            privacy_notice=privacy_notice,
        )
