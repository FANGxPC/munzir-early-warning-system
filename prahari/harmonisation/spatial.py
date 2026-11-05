"""
Spatial Hierarchy and Geolocation Fallback Engine.
Provides H3 hexagonal spatial indexing (resolutions 6 and 7) and resolves
the fallback hierarchy: Site/Exact GPS -> H3 Hexagon -> District -> State.
"""

from typing import Dict, List, Any, Optional, Tuple
import math
import h3
from shapely.geometry import Point, Polygon

from prahari.config import H3_RES_DETECTION, H3_RES_COARSE, REGIONAL_PROFILES, get_region_config


def get_h3_index(lat: float, lon: float, resolution: int = H3_RES_DETECTION) -> str:
    """
    Calculate Uber H3 hexagonal cell index from latitude and longitude.
    Default resolution is 7 (~5.16 km2 area, chosen so cell > individual workplace).
    """
    return h3.latlng_to_cell(float(lat), float(lon), int(resolution))


def get_h3_neighbors(h3_index: str, k_ring: int = 1) -> List[str]:
    """
    Get neighboring H3 cells within k-ring radius (used for prospective space-time scans).
    """
    return list(h3.grid_disk(h3_index, k_ring))


class SpatialHierarchyMapper:
    """
    Resolves spatial queries, maps coordinates to H3 cells and districts,
    and applies the multi-tiered Geolocation Fallback Hierarchy.
    """

    def __init__(self, region_key: str = "uae"):
        self.region_key = region_key.lower()
        self.region_profile = get_region_config(self.region_key)
        self.state_name = self.region_profile.get("state_name", "Dubai")
        self.districts = self.region_profile.get("districts", [])
        self.sites = self.region_profile.get("sites", [])

        # Build site lookup by ID and district lookup by ID
        self.site_map: Dict[str, Dict[str, Any]] = {s["id"]: s for s in self.sites}
        self.district_map: Dict[str, Dict[str, Any]] = {d["id"]: d for d in self.districts}

        # Precompute H3 indices for all sites
        for s in self.sites:
            s["h3_res7"] = get_h3_index(s["lat"], s["lon"], H3_RES_DETECTION)
            s["h3_res6"] = get_h3_index(s["lat"], s["lon"], H3_RES_COARSE)

        # Precompute H3 indices for district centroids
        for d in self.districts:
            d["h3_res7"] = get_h3_index(d["lat"], d["lon"], H3_RES_DETECTION)
            d["h3_res6"] = get_h3_index(d["lat"], d["lon"], H3_RES_COARSE)

    def resolve_hierarchy(
        self,
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        site_id: Optional[str] = None,
        district_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Resolves geolocation fallback hierarchy:
        1. Exact site coordinates / site_id -> 'site' + H3 resolution 7 (location_confidence='exact')
        2. Exact lat/lon without site -> 'h3_res7' (location_confidence='exact')
        3. District only (address or district_id) -> 'district' (location_confidence='district_only')
        4. Neither -> 'state' level bucket (location_confidence='inferred')
        """
        # Case 1: Known site
        if site_id and site_id in self.site_map:
            site = self.site_map[site_id]
            d_id = site["district_id"]
            return {
                "geo_level": "site",
                "geo_id": site_id,
                "site_id": site_id,
                "district_id": d_id,
                "state_id": self.state_name,
                "h3_index": site["h3_res7"],
                "h3_res6": site["h3_res6"],
                "location_confidence": "exact",
                "cluster_eligible": True,
                "lat": site["lat"],
                "lon": site["lon"],
            }

        # Case 2: Exact coordinates provided
        if lat is not None and lon is not None:
            # Check if within proximity to a known site (< 300m)
            matched_site = None
            for s in self.sites:
                dist_km = self._haversine(lat, lon, s["lat"], s["lon"])
                if dist_km <= 0.3:
                    matched_site = s
                    break

            if matched_site:
                return {
                    "geo_level": "site",
                    "geo_id": matched_site["id"],
                    "site_id": matched_site["id"],
                    "district_id": matched_site["district_id"],
                    "state_id": self.state_name,
                    "h3_index": matched_site["h3_res7"],
                    "h3_res6": matched_site["h3_res6"],
                    "location_confidence": "exact",
                    "cluster_eligible": True,
                    "lat": lat,
                    "lon": lon,
                }

            # Exact coordinates outside known site -> H3 resolution 7 cell
            nearest_district = self._find_nearest_district(lat, lon)
            h3_res7 = get_h3_index(lat, lon, H3_RES_DETECTION)
            h3_res6 = get_h3_index(lat, lon, H3_RES_COARSE)
            return {
                "geo_level": "h3_res7",
                "geo_id": h3_res7,
                "site_id": None,
                "district_id": nearest_district["id"] if nearest_district else district_id,
                "state_id": self.state_name,
                "h3_index": h3_res7,
                "h3_res6": h3_res6,
                "location_confidence": "exact",
                "cluster_eligible": True,
                "lat": lat,
                "lon": lon,
            }

        # Case 3: District known, but no exact coordinates (e.g., patient clinic address)
        if district_id and district_id in self.district_map:
            dist = self.district_map[district_id]
            return {
                "geo_level": "district",
                "geo_id": district_id,
                "site_id": None,
                "district_id": district_id,
                "state_id": self.state_name,
                "h3_index": dist["h3_res7"],  # Centroid H3
                "h3_res6": dist["h3_res6"],
                "location_confidence": "district_only",
                "cluster_eligible": True,  # Included in district-level aberration scans
                "lat": dist["lat"],
                "lon": dist["lon"],
            }

        # Case 4: Neither coordinates nor district known -> State bucket
        return {
            "geo_level": "state",
            "geo_id": self.state_name,
            "site_id": None,
            "district_id": None,
            "state_id": self.state_name,
            "h3_index": None,
            "h3_res6": None,
            "location_confidence": "inferred",
            "cluster_eligible": False,  # Excluded from cluster scanning, included in totals
            "lat": None,
            "lon": None,
        }

    def _find_nearest_district(self, lat: float, lon: float) -> Optional[Dict[str, Any]]:
        """Find the closest district centroid by distance."""
        best_dist = float("inf")
        best_district = None
        for d in self.districts:
            dist_km = self._haversine(lat, lon, d["lat"], d["lon"])
            if dist_km < best_dist:
                best_dist = dist_km
                best_district = d
        return best_district

    @staticmethod
    def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
        """Great circle distance in kilometers."""
        r = 6371.0
        phi1 = math.radians(lat1)
        phi2 = math.radians(lat2)
        delta_phi = math.radians(lat2 - lat1)
        delta_lambda = math.radians(lon2 - lon1)

        a = math.sin(delta_phi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * (math.sin(delta_lambda / 2.0) ** 2)
        c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
        return r * c

