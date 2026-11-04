"""
Scenario and Injected Event Catalog for Ground Truth Validation.
Defines the three flagship outbreak scenarios and decoy artefacts required
by the PRAHARI implementation specification.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import numpy as np

from prahari.models.canonical import InjectedEventTruth


class InjectedScenarioCatalog:
    """
    Catalog of ground truth scenarios:
    1. Heat stress cluster at outdoor worksites
    2. Air-pollution-driven respiratory surge
    3. Unexplained infectious (GI/fever) cluster
    4. Decoy: reporting backlog dump
    5. Decoy: holiday closure dip & rebound
    6. Decoy: new clinic opening step-shift
    """

    @staticmethod
    def generate_scenarios(
        start_date: str,
        end_date: str,
        region_profile: Dict[str, Any],
        seed: int = 42,
    ) -> List[InjectedEventTruth]:
        """
        Generate structured ground-truth events across the simulation window.
        """
        rng = np.random.RandomState(seed)
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end_dt - start_dt).days

        if total_days < 30:
            total_days = 30

        districts = region_profile.get("districts", [])
        sites = region_profile.get("sites", [])

        events: List[InjectedEventTruth] = []

        # 1. Flagship Scenario 1: Heat stress cluster at outdoor worksites (Summer)
        # Select 2-3 outdoor sites in the primary industrial district
        outdoor_sites = [s for s in sites if "outdoor" in s.get("site_type", "")]
        target_outdoor = outdoor_sites[:3] if outdoor_sites else sites[:2]

        # Place during mid-summer (July/August) or ~60% through window
        heat_offset = min(int(total_days * 0.60), total_days - 14)
        heat_start = start_dt + timedelta(days=heat_offset)
        heat_peak = heat_start + timedelta(days=4)
        heat_end = heat_start + timedelta(days=9)

        for site in target_outdoor:
            events.append(
                InjectedEventTruth(
                    scenario_type="heat_cluster",
                    target_geo_id=site["id"],
                    start_date=heat_start.strftime("%Y-%m-%d"),
                    peak_date=heat_peak.strftime("%Y-%m-%d"),
                    end_date=heat_end.strftime("%Y-%m-%d"),
                    multiplier=2.8,
                    is_decoy=False,
                    description=f"Heat stress cluster at {site['name']} under severe WBGT load",
                )
            )

        # 2. Flagship Scenario 2: Air-pollution-driven respiratory surge (Winter/Dust episode)
        # Spread across 2-3 adjacent districts
        target_districts = districts[:3]
        resp_offset = min(int(total_days * 0.35), total_days - 18)
        resp_start = start_dt + timedelta(days=resp_offset)
        resp_peak = resp_start + timedelta(days=5)
        resp_end = resp_start + timedelta(days=12)

        for dist in target_districts:
            events.append(
                InjectedEventTruth(
                    scenario_type="respiratory_surge",
                    target_geo_id=dist["id"],
                    start_date=resp_start.strftime("%Y-%m-%d"),
                    peak_date=resp_peak.strftime("%Y-%m-%d"),
                    end_date=resp_end.strftime("%Y-%m-%d"),
                    multiplier=2.4,
                    is_decoy=False,
                    description=f"Pollution-driven acute respiratory surge in district {dist['name']}",
                )
            )

        # 3. Flagship Scenario 3: Unexplained infectious cluster (GI / Food-waterborne)
        # Occurs at a specific facility (e.g. food processing / canteen or single site) with NORMAL weather
        target_site = sites[1] if len(sites) > 1 else sites[0]
        gi_offset = min(int(total_days * 0.80), total_days - 10)
        gi_start = start_dt + timedelta(days=gi_offset)
        gi_peak = gi_start + timedelta(days=3)
        gi_end = gi_start + timedelta(days=7)

        events.append(
            InjectedEventTruth(
                scenario_type="infectious_cluster",
                target_geo_id=target_site["id"],
                start_date=gi_start.strftime("%Y-%m-%d"),
                peak_date=gi_peak.strftime("%Y-%m-%d"),
                end_date=gi_end.strftime("%Y-%m-%d"),
                multiplier=3.5,
                is_decoy=False,
                description=f"Point-source gastrointestinal/fever cluster at {target_site['name']}",
            )
        )

        # 4. Decoy 1: Reporting backlog dump (artefact)
        # 3 days of near-zero reporting followed by a 4x dump on day 4
        decoy_dist = districts[-1] if len(districts) > 1 else districts[0]
        backlog_offset = min(int(total_days * 0.20), total_days - 8)
        backlog_start = start_dt + timedelta(days=backlog_offset)
        backlog_end = backlog_start + timedelta(days=4)

        events.append(
            InjectedEventTruth(
                scenario_type="decoy_backlog",
                target_geo_id=decoy_dist["id"],
                start_date=backlog_start.strftime("%Y-%m-%d"),
                peak_date=(backlog_start + timedelta(days=3)).strftime("%Y-%m-%d"),
                end_date=backlog_end.strftime("%Y-%m-%d"),
                multiplier=4.0,
                is_decoy=True,
                description=f"Reporting backlog dump in {decoy_dist['name']} (benign administrative artefact)",
            )
        )

        # 5. Decoy 2: Holiday dip and rebound
        holiday_dist = districts[0]
        hol_offset = min(int(total_days * 0.50), total_days - 6)
        hol_start = start_dt + timedelta(days=hol_offset)
        hol_end = hol_start + timedelta(days=3)

        events.append(
            InjectedEventTruth(
                scenario_type="decoy_holiday",
                target_geo_id=holiday_dist["id"],
                start_date=hol_start.strftime("%Y-%m-%d"),
                peak_date=(hol_start + timedelta(days=2)).strftime("%Y-%m-%d"),
                end_date=hol_end.strftime("%Y-%m-%d"),
                multiplier=0.2,
                is_decoy=True,
                description=f"Public holiday clinic closure dip in {holiday_dist['name']}",
            )
        )

        return events


def generate_ground_truth_events(
    start_date: str,
    end_date: str,
    region_profile: Dict[str, Any],
    seed: int = 42,
) -> List[InjectedEventTruth]:
    """Convenience factory function."""
    return InjectedScenarioCatalog.generate_scenarios(
        start_date=start_date,
        end_date=end_date,
        region_profile=region_profile,
        seed=seed,
    )

