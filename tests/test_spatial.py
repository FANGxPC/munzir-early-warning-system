"""Unit tests for Spatial Hierarchy Mapping and H3 Hexagonal Indexing."""

from prahari.harmonisation.spatial import SpatialHierarchyMapper, get_h3_index, get_h3_neighbors


def test_h3_indexing():
    # Jebel Ali coordinates
    lat, lon = 24.9857, 55.0272
    h3_res7 = get_h3_index(lat, lon, resolution=7)
    assert isinstance(h3_res7, str)
    assert len(h3_res7) == 15

    h3_res6 = get_h3_index(lat, lon, resolution=6)
    assert isinstance(h3_res6, str)
    assert len(h3_res6) == 15
    assert h3_res6 != h3_res7

    neighbors = get_h3_neighbors(h3_res7, k_ring=1)
    assert len(neighbors) == 7  # Center cell + 6 neighbors


def test_spatial_hierarchy_fallback():
    mapper = SpatialHierarchyMapper(region_key="uae")

    # 1. Exact site lookup
    site_res = mapper.resolve_hierarchy(site_id="SITE-JA-01")
    assert site_res["geo_level"] == "site"
    assert site_res["geo_id"] == "SITE-JA-01"
    assert site_res["district_id"] == "DXB-JA"
    assert site_res["location_confidence"] == "exact"
    assert site_res["cluster_eligible"] is True
    assert site_res["h3_index"] is not None

    # 2. Exact coordinates lookup (without site_id)
    coord_res = mapper.resolve_hierarchy(lat=25.2000, lon=55.2800)
    assert coord_res["location_confidence"] == "exact"
    assert coord_res["cluster_eligible"] is True
    assert coord_res["h3_index"] is not None

    # 3. District only lookup (e.g. clinic address in Deira)
    dist_res = mapper.resolve_hierarchy(district_id="DXB-DR")
    assert dist_res["geo_level"] == "district"
    assert dist_res["geo_id"] == "DXB-DR"
    assert dist_res["location_confidence"] == "district_only"
    assert dist_res["cluster_eligible"] is True

    # 4. Unknown / fallback to state bucket
    state_res = mapper.resolve_hierarchy()
    assert state_res["geo_level"] == "state"
    assert state_res["location_confidence"] == "inferred"
    assert state_res["cluster_eligible"] is False  # Excluded from cluster scan, included in totals

