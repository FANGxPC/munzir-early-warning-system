"""
Phase 7 What-If Intervention Simulator Unit & Integration Tests.
Verifies:
1. Deterministic exposure-hours recomputation against exact hand-calculated synthetic cases.
2. Sourced assumptions completeness (every assumption verified with citation/DOI or explicitly UNVERIFIED).
3. Non-empty unverified audit ledger.
4. Monte Carlo seed reproducibility and quantile stability.
5. Privacy boundary enforcement (workforce >= 50, small-cell suppression, no worker IDs, RBAC).
6. Tornado sensitivity ranking calculation.
7. REST API endpoints (/scenarios, /assumptions, /simulate).
"""

import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from fastapi.testclient import TestClient

from prahari.config import WORKPLACE_MIN_GROUP_SIZE, SMALL_CELL_K
from prahari.whatif.config import (
    load_assumptions_config,
    get_unverified_assumptions,
)
from prahari.whatif.exposure import (
    WorkSchedule,
    ExposureCalculator,
)
from prahari.whatif.monte_carlo import MonteCarloInterventionSimulator
from prahari.whatif.sensitivity import TornadoSensitivityAnalyzer
from prahari.whatif.simulator import WhatIfSimulator
from prahari.api.app import app


# --- Test 1: Hand-Checkable Deterministic Exposure Recomputation ---

def test_deterministic_exposure_hand_checkable():
    """
    Hand-calculated test on a 4-hour synthetic WBGT series.
    Hour 10 (10:00): WBGT = 33.0°C (Danger >= 32, Caution >= 28)
    Hour 13 (13:00): WBGT = 35.0°C (Danger, Caution)
    Hour 17 (17:00): WBGT = 29.0°C (Not Danger, Caution >= 28)
    Hour 20 (20:00): WBGT = 26.0°C (Neither)

    Baseline Schedule: Start 7.0, End 16.0, Break 12.5 - 14.0.
      - Hour 10: In shift [7-16], not in break [12.5-14] -> WORKING.
        WBGT = 33.0°C -> Danger (1), Caution (1).
      - Hour 13: In break [12.5-14.0] -> NOT working.
      - Hour 17: Outside shift (17 >= 16) -> NOT working.
      - Hour 20: Outside shift (20 >= 16) -> NOT working.
      Total Baseline Working Hours = 1
      Baseline Hours in Danger = 1
      Baseline Hours in Caution = 1

    Scenario Schedule (Split Shift): Start 5.5 to 11.5, Evening 16.5 to 18.5. Shade = 2.0°C.
      - Hour 10: In shift [5.5-11.5] -> WORKING.
        Raw WBGT = 33.0°C - 2.0°C shade = 31.0°C effective.
        31.0°C < 32°C -> NOT Danger (0).
        31.0°C >= 28°C -> Caution (1).
      - Hour 13: Not in working hours -> NOT working.
      - Hour 17: In evening shift [16.5-18.5] -> WORKING.
        Raw WBGT = 29.0°C - 2.0°C shade = 27.0°C effective.
        27.0°C < 32°C -> NOT Danger (0).
        27.0°C < 28°C -> NOT Caution (0).
      - Hour 20: Not working.
      Total Scenario Working Hours = 2 (Hours 10 and 17).
      Scenario Hours in Danger = 0
      Scenario Hours in Caution = 1

    Comparison:
      danger_hours_averted = 1 - 0 = 1.0 hr
      danger_hours_reduction_pct = 100.0%
      caution_hours_averted = 1 - 1 = 0.0 hr
    """
    df_synthetic = pd.DataFrame({
        "timestamp": [
            pd.Timestamp("2024-06-15 10:00:00"),
            pd.Timestamp("2024-06-15 13:00:00"),
            pd.Timestamp("2024-06-15 17:00:00"),
            pd.Timestamp("2024-06-15 20:00:00"),
        ],
        "date": ["2024-06-15"] * 4,
        "hour": [10.0, 13.0, 17.0, 20.0],
        "wbgt": [33.0, 35.0, 29.0, 26.0],
    })

    baseline_sched = WorkSchedule("Standard", start_hour=7.0, end_hour=16.0, break_start=12.5, break_end=14.0)
    scenario_sched = WorkSchedule(
        "Split Shift",
        start_hour=5.5,
        end_hour=11.5,
        break_start=11.5,
        break_end=16.5,
        split_shift_start_2=16.5,
        split_shift_end_2=18.5,
    )

    comp = ExposureCalculator.compare_interventions_deterministic(
        df_wbgt=df_synthetic,
        baseline_schedule=baseline_sched,
        scenario_schedule=scenario_sched,
        shade_delta_c=2.0,
        workforce_size=100,
    )

    base = comp["baseline"]
    scen = comp["scenario"]
    red = comp["exposure_reduction"]

    # Exact assertions on hand-calculated numbers
    assert base["total_working_hours"] == 1
    assert base["exposure_hours_danger"] == 1.0
    assert base["exposure_hours_caution"] == 1.0
    assert base["mean_wbgt_working"] == 33.0
    assert base["worker_hours_danger"] == 100.0

    assert scen["total_working_hours"] == 2
    assert scen["exposure_hours_danger"] == 0.0
    assert scen["exposure_hours_caution"] == 1.0
    assert scen["mean_wbgt_working"] == round((31.0 + 27.0) / 2.0, 2)
    assert scen["worker_hours_danger"] == 0.0

    assert red["danger_hours_averted"] == 1.0
    assert red["danger_hours_reduction_pct"] == 100.0
    assert red["danger_worker_hours_averted"] == 100.0
    assert red["caution_hours_averted"] == 0.0


# --- Test 2: Assumptions Sourcing Completeness & Non-Empty Unverified Audit ---

def test_assumptions_completeness_and_unverified_audit():
    """
    Verifies that:
    1. Every assumption parameter has either 'VERIFIED' with citation/DOI/authority,
       or 'UNVERIFIED' with explicit notes/disclosures.
    2. The unverified audit list is non-empty (confirms audit actively caught unverified items).
    3. UAE statutory mandate references official MOHRE Ministerial Resolution No. (44) of 2022.
    """
    cfg = load_assumptions_config()
    assert isinstance(cfg, dict)

    categories = [
        "statutory_regulations",
        "intervention_effects",
        "epidemiological_baselines",
        "economic_valuations",
        "intervention_costs",
    ]

    for cat in categories:
        assert cat in cfg, f"Missing category '{cat}' in assumptions config"
        params = cfg[cat]
        assert len(params) > 0, f"Category '{cat}' is empty"

        for p_name, p_data in params.items():
            status = p_data.get("verification_status")
            assert status in ["VERIFIED", "UNVERIFIED"], f"Invalid status '{status}' for {p_name}"

            if status == "VERIFIED":
                # Must possess verifiable literature, official authority, or statute
                has_authors = "authors" in p_data or "authority" in p_data
                has_reference = "doi_or_url" in p_data or "url" in p_data or "resolution_name" in p_data
                assert has_authors and has_reference, (
                    f"VERIFIED parameter '{p_name}' must have authors/authority and DOI/URL/resolution"
                )
            else:
                # UNVERIFIED must disclose basis/notes
                assert "notes" in p_data or "source_title" in p_data, (
                    f"UNVERIFIED parameter '{p_name}' must include notes disclosing why unverified"
                )

    # Statutory resolution check
    midday_rule = cfg["statutory_regulations"]["uae_midday_break_rule"]
    assert "44" in str(midday_rule.get("resolution_name", ""))
    assert midday_rule["year"] == 2022
    assert midday_rule["restricted_hours"]["start_time"] == "12:30"
    assert midday_rule["restricted_hours"]["end_time"] == "15:00"

    # Audit list must be non-empty
    unverified = get_unverified_assumptions(cfg)
    assert len(unverified) >= 3, f"Expected at least 3 unverified items, found {len(unverified)}"
    unverified_keys = [item["key"] for item in unverified]
    assert "cost_shade_canopy_rental_per_worker_month_aed" in unverified_keys
    assert "cost_hydration_point_per_worker_day_aed" in unverified_keys
    assert "cost_shift_reschedule_friction_per_worker_month_aed" in unverified_keys


# --- Test 3: Monte Carlo Seed Reproducibility ---

def test_monte_carlo_seed_reproducibility():
    """
    Verifies that Monte Carlo simulation produces byte-identical quantile distributions
    when run with the same random seed, and distinct results with different seeds.
    """
    df_wbgt = ExposureCalculator.load_site_wbgt_series("SITE-JA-01", "2024-06-01", "2024-06-15")
    baseline_sched = WorkSchedule("Baseline", 7.0, 16.0, 12.5, 14.0)
    scenario_sched = WorkSchedule("Split", 5.5, 11.5, 11.5, 16.5, 16.5, 18.5)

    comp = ExposureCalculator.compare_interventions_deterministic(
        df_wbgt, baseline_sched, scenario_sched, shade_delta_c=2.5, workforce_size=1000
    )

    sim1 = MonteCarloInterventionSimulator(n_iterations=500, seed=42)
    res1 = sim1.run_simulation(comp, duration_days=15.0, workforce_size=1000, is_shade_active=True)

    sim2 = MonteCarloInterventionSimulator(n_iterations=500, seed=42)
    res2 = sim2.run_simulation(comp, duration_days=15.0, workforce_size=1000, is_shade_active=True)

    # Identical with same seed
    for metric in ["cases_averted", "severe_incidents_averted", "gross_savings_aed", "benefit_cost_ratio"]:
        assert res1[metric]["median"] == res2[metric]["median"]
        assert res1[metric]["p05"] == res2[metric]["p05"]
        assert res1[metric]["p95"] == res2[metric]["p95"]

    # Different with different seed
    sim3 = MonteCarloInterventionSimulator(n_iterations=500, seed=999)
    res3 = sim3.run_simulation(comp, duration_days=15.0, workforce_size=1000, is_shade_active=True)
    assert res1["cases_averted"]["mean"] != res3["cases_averted"]["mean"]


# --- Test 4: Privacy Boundaries & Small-Cell Suppression ---

def test_privacy_enforcement_and_small_cell_suppression():
    """
    Verifies:
    1. Workforce < 50 raises PermissionError (prevents individual or small-cohort surveillance).
    2. Outputs contain strictly cohort-level statistics with zero worker identifiers.
    3. Small-cell suppression flag activates when projected cases < 10.
    """
    simulator = WhatIfSimulator(seed=42)

    # Rejection under threshold
    with pytest.raises(PermissionError) as exc_info:
        simulator.simulate(site_id="SITE-JA-01", action_type="shift_hours", workforce_override=49)
    assert f"below minimum group size ({WORKPLACE_MIN_GROUP_SIZE})" in str(exc_info.value)

    # Valid run above threshold
    results = simulator.simulate(
        site_id="SITE-JA-01",
        action_type="shift_hours",
        start_date="2024-06-01",
        end_date="2024-06-30",
        workforce_override=100,
    )

    # Check absence of worker-level fields
    res_str = str(results).lower()
    for forbidden in ["worker_id", "employee_id", "patient_id", "subteam", "gang_id"]:
        assert forbidden not in res_str

    # Small cell suppression test: short window + low workforce
    short_results = simulator.simulate(
        site_id="SITE-JA-01",
        action_type="shift_hours",
        start_date="2024-06-01",
        end_date="2024-06-02",
        workforce_override=50,
    )
    if short_results["stochastic_outcomes"]["cases_averted"]["median"] < SMALL_CELL_K:
        assert short_results["metadata"]["is_suppressed"] is True
        assert short_results["metadata"]["suppression_notice"] is not None


# --- Test 5: Tornado Sensitivity Ranking ---

def test_tornado_sensitivity_ranking():
    """
    Verifies that TornadoSensitivityAnalyzer correctly identifies and ranks
    the primary outcome variance drivers.
    """
    simulator = WhatIfSimulator(seed=42)
    results = simulator.simulate(
        site_id="SITE-JA-01",
        action_type="combined_protocol",
        start_date="2024-06-01",
        end_date="2024-06-30",
        workforce_override=3200,
    )

    tornado = results["tornado_sensitivity"]
    assert len(tornado) >= 4

    # Influence percentages should sum close to 100%
    total_pct = sum(item["relative_importance_pct"] for item in tornado)
    assert 90.0 <= total_pct <= 105.0

    # Ranks must be monotonic non-increasing by influence
    influences = [item["relative_importance_pct"] for item in tornado]
    assert influences == sorted(influences, reverse=True)

    # Primary driver should be baseline incidence or exposure slope
    assert tornado[0]["param_key"] in [
        "baseline_rate",
        "slope",
    ]


# --- Test 6: REST API Endpoints & RBAC Integration ---

def test_whatif_api_endpoints():
    """
    Tests REST API endpoints:
    1. GET /api/v1/whatif/scenarios
    2. GET /api/v1/whatif/assumptions
    3. GET /api/v1/whatif/simulate
    4. RBAC boundary enforcement
    """
    client = TestClient(app)

    # 1. Scenarios endpoint
    res_scen = client.get("/api/v1/whatif/scenarios")
    assert res_scen.status_code == 200
    scenarios = res_scen.json()["scenarios"]
    scen_ids = [s["id"] for s in scenarios]
    assert "combined_protocol" in scen_ids
    assert "shift_hours" in scen_ids
    assert "extend_break" in scen_ids
    assert "add_shade" in scen_ids
    assert "add_water_cooling" in scen_ids

    # 2. Assumptions endpoint
    res_asm = client.get("/api/v1/whatif/assumptions")
    assert res_asm.status_code == 200
    asm_data = res_asm.json()
    assert asm_data["unverified_count"] >= 3
    assert len(asm_data["unverified_items"]) >= 3

    # 3. Simulate endpoint (Authorized Surveillance Officer)
    res_sim = client.get(
        "/api/v1/whatif/simulate?site_id=SITE-JA-01&action=combined_protocol&workforce=3200",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res_sim.status_code == 200
    sim_data = res_sim.json()
    assert "deterministic_exposure" in sim_data
    assert "stochastic_outcomes" in sim_data
    assert "tornado_sensitivity" in sim_data
    assert sim_data["deterministic_exposure"]["exposure_reduction"]["danger_hours_averted"] > 0

    # 4. Custom parameter override (shade reduction & break extension)
    res_custom = client.get(
        "/api/v1/whatif/simulate?site_id=SITE-JA-01&action=extend_break&workforce=3200&break_extension_minutes=60",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res_custom.status_code == 200
    custom_data = res_custom.json()
    assert custom_data["deterministic_exposure"]["exposure_reduction"]["danger_hours_averted"] > 0

    # 5. Privacy rejection for cohort < 50
    res_small = client.get(
        "/api/v1/whatif/simulate?site_id=SITE-JA-01&action=combined_protocol&workforce=30",
        headers={"X-Role": "surveillance_officer"},
    )
    assert res_small.status_code == 403
    assert "minimum group size" in res_small.json()["detail"]

    # 6. Public role rejection (proprietary simulation forbidden)
    res_pub = client.get(
        "/api/v1/whatif/simulate?site_id=SITE-JA-01&action=combined_protocol",
        headers={"X-Role": "public"},
    )
    assert res_pub.status_code == 403
    assert "Public role cannot run proprietary site-level simulations" in res_pub.json()["detail"]

    # 7. Employer Safety cross-site rejection
    res_cross = client.get(
        "/api/v1/whatif/simulate?site_id=SITE-DH-02&action=combined_protocol",
        headers={"X-Role": "employer_safety", "X-Employer-ID": "SITE-JA-01"},
    )
    assert res_cross.status_code == 403
    assert "authorized only for site 'SITE-JA-01'" in res_cross.json()["detail"]
