"""
Synthetic Health & Workplace Multi-Signal Generator.
Simulates daily district-level clinical syndromic counts (respiratory, GI, fever),
lab test positivity, site-level sickness absence, and workplace incident reports
driven by real/synthesized environmental exposures and injected outbreak truth.
"""

import math
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import numpy as np
import pandas as pd

from prahari.config import REGIONAL_PROFILES, get_region_config
from prahari.models.canonical import SignalObservation, IncidentReport, InjectedEventTruth
from prahari.simulator.events import InjectedScenarioCatalog
from prahari.simulator.defects import DataDefectEngine
from prahari.nlp.classifier import IncidentClassifier
from prahari.nlp.anonymizer import sanitize_incident_narrative


class HealthWorkplaceSimulator:
    """
    Master synthetic generator calibrated to environmental exposures and epidemiological dynamics.
    """

    def __init__(
        self,
        region_key: str = "uae",
        seed: int = 42,
        missing_rate: float = 0.03,
        degrade_geo_rate: float = 0.05,
        disable_clinical_feed: bool = False,
    ):
        self.region_key = region_key
        self.region_profile = get_region_config(region_key)
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        self.defect_engine = DataDefectEngine(
            seed=seed,
            missing_rate=missing_rate,
            degrade_geo_rate=degrade_geo_rate,
            disable_clinical_feed=disable_clinical_feed,
        )
        self.classifier = IncidentClassifier()

    def simulate(
        self,
        start_date: str,
        end_date: str,
        env_observations: List[SignalObservation],
    ) -> Tuple[List[SignalObservation], List[IncidentReport], List[InjectedEventTruth]]:
        """
        Run the multi-signal simulation across the given date range.
        Takes environmental observations (WBGT, PM2.5, etc.) to drive exposure-responses.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        total_days = (end_dt - start_dt).days + 1

        districts = self.region_profile.get("districts", [])
        sites = self.region_profile.get("sites", [])

        # 1. Generate Ground Truth Injected Scenarios
        ground_truth = InjectedScenarioCatalog.generate_scenarios(
            start_date=start_date,
            end_date=end_date,
            region_profile=self.region_profile,
            seed=self.seed,
        )

        # Index environmental exposures by (geo_id, obs_date, signal_type)
        env_map: Dict[Tuple[str, str, str], float] = {}
        for obs in env_observations:
            env_map[(obs.geo_id, obs.obs_date, obs.signal_type)] = obs.value

        all_observations: List[SignalObservation] = []
        all_incidents: List[IncidentReport] = []

        # Track backlog accumulators for decoy scenarios
        backlog_accumulator: Dict[Tuple[str, str], float] = {}

        # 2. Daily Simulation Loop
        for day_idx in range(total_days):
            current_dt = start_dt + timedelta(days=day_idx)
            date_str = current_dt.strftime("%Y-%m-%d")
            day_of_week = current_dt.weekday()  # 0=Monday ... 6=Sunday
            day_of_year = current_dt.timetuple().tm_yday

            # Weekend effect: in UAE Friday/Saturday or Sunday lower OPD visits (0.65x)
            dow_multiplier = 0.70 if day_of_week in [4, 5, 6] else 1.12
            annual_phase = 2 * math.pi * (day_of_year - 20) / 365.25  # winter peak for respiratory

            # --- A. District-level Clinical Syndromic Feeds ---
            for dist in districts:
                dist_id = dist["id"]
                pop = dist["population"]
                pop_100k = pop / 100000.0

                # Environmental exposures for this district
                # PM2.5 lag-adjusted (lags 0-3 days approximated by today's exposure)
                pm25 = env_map.get((dist_id, date_str, "pm25"), 35.0)
                wbgt_max = env_map.get((dist_id, date_str, "wbgt_max"), 27.0)

                # Baseline respiratory rate: ~12 visits per 100k/day
                # Exposure response: +0.6% visits per 1 ug/m3 PM2.5 above 25 ug/m3
                pm25_excess = max(0.0, pm25 - 25.0)
                resp_exposure_mult = math.exp(0.006 * pm25_excess)
                resp_seasonal_mult = 1.0 + 0.35 * math.cos(annual_phase)

                lambda_resp = 12.0 * pop_100k * dow_multiplier * resp_exposure_mult * resp_seasonal_mult

                # Baseline GI (gastrointestinal): ~6 visits per 100k/day
                lambda_gi = 6.0 * pop_100k * dow_multiplier

                # Baseline Fever: ~8 visits per 100k/day
                lambda_fever = 8.0 * pop_100k * dow_multiplier * (1.0 + 0.2 * math.cos(annual_phase))

                # Baseline Heat Illness OPD visits (district level): rises when WBGT > 29C
                heat_excess_deg = max(0.0, wbgt_max - 29.0)
                heat_exposure_mult = math.exp(0.35 * heat_excess_deg) if heat_excess_deg > 0 else 1.0
                lambda_heat = 1.5 * pop_100k * heat_exposure_mult

                # Check for active injected events
                for ev in ground_truth:
                    if ev.target_geo_id == dist_id and ev.start_date <= date_str <= ev.end_date:
                        p_dt = datetime.strptime(ev.peak_date, "%Y-%m-%d")
                        days_from_peak = abs((current_dt - p_dt).days)
                        surge = max(0.0, 1.0 + (ev.multiplier - 1.0) * math.exp(-0.5 * (days_from_peak / 2.0) ** 2))

                        if ev.scenario_type == "respiratory_surge":
                            lambda_resp *= surge
                        elif ev.scenario_type == "decoy_backlog":
                            # If early in backlog, suppress and accumulate; if peak date, dump!
                            key = (dist_id, "clinical_resp")
                            if current_dt < p_dt:
                                backlog_accumulator[key] = backlog_accumulator.get(key, 0.0) + lambda_resp * 0.8
                                lambda_resp *= 0.2
                            else:
                                dump = backlog_accumulator.pop(key, 0.0)
                                lambda_resp += dump
                        elif ev.scenario_type == "decoy_holiday":
                            lambda_resp *= ev.multiplier
                            lambda_gi *= ev.multiplier
                            lambda_fever *= ev.multiplier

                # Sample negative binomial counts (approximated via Poisson-Gamma mixture)
                # alpha = dispersion parameter ~ 0.15
                resp_count = float(self._sample_neg_binom(lambda_resp, dispersion=0.15))
                gi_count = float(self._sample_neg_binom(lambda_gi, dispersion=0.12))
                fever_count = float(self._sample_neg_binom(lambda_fever, dispersion=0.12))
                heat_count = float(self._sample_neg_binom(lambda_heat, dispersion=0.20))

                # Lab test positivity (% positive among tested syndromic cases)
                # Baseline 6-12%; rises during infectious outbreaks
                lab_tested = max(5, int(fever_count * 0.4))
                lab_pos_rate = 0.08
                for ev in ground_truth:
                    if ev.target_geo_id == dist_id and ev.start_date <= date_str <= ev.end_date and not ev.is_decoy:
                        lab_pos_rate = 0.28
                lab_positives = float(self.rng.binomial(lab_tested, np.clip(lab_pos_rate, 0.01, 0.95)))

                all_observations.extend([
                    SignalObservation(
                        signal_type="clinical_resp",
                        geo_level="district",
                        geo_id=dist_id,
                        obs_date=date_str,
                        value=resp_count,
                        denominator=float(pop),
                        location_confidence="district_only",
                    ),
                    SignalObservation(
                        signal_type="clinical_gi",
                        geo_level="district",
                        geo_id=dist_id,
                        obs_date=date_str,
                        value=gi_count,
                        denominator=float(pop),
                        location_confidence="district_only",
                    ),
                    SignalObservation(
                        signal_type="clinical_fever",
                        geo_level="district",
                        geo_id=dist_id,
                        obs_date=date_str,
                        value=fever_count,
                        denominator=float(pop),
                        location_confidence="district_only",
                    ),
                    SignalObservation(
                        signal_type="clinical_heat",
                        geo_level="district",
                        geo_id=dist_id,
                        obs_date=date_str,
                        value=heat_count,
                        denominator=float(pop),
                        location_confidence="district_only",
                    ),
                    SignalObservation(
                        signal_type="lab_pos",
                        geo_level="district",
                        geo_id=dist_id,
                        obs_date=date_str,
                        value=lab_positives,
                        denominator=float(lab_tested),
                        location_confidence="district_only",
                    ),
                ])

            # --- B. Site-Level Workplace Absence & Incident Feeds ---
            for site in sites:
                site_id = site["id"]
                dist_id = site["district_id"]
                workforce = site["workforce"]
                site_type = site.get("site_type", "outdoor_construction")
                is_outdoor = "outdoor" in site_type

                site_wbgt = env_map.get((site_id, date_str, "wbgt_max"), 28.0)
                site_pm25 = env_map.get((site_id, date_str, "pm25"), 35.0)

                # Heat absence rate:
                # Baseline 0.5 per 1,000 workers/day
                # If outdoor and WBGT > 29C: exponential rise
                baseline_absence_rate = 0.0005
                heat_factor = 1.0
                if is_outdoor and site_wbgt > 29.0:
                    heat_delta = site_wbgt - 29.0
                    heat_factor = math.exp(0.45 * heat_delta)

                lambda_absence = workforce * baseline_absence_rate * heat_factor * (0.4 if day_of_week in [4, 5] else 1.0)

                # Check active site events
                is_heat_event_active = False
                for ev in ground_truth:
                    if ev.target_geo_id == site_id and ev.start_date <= date_str <= ev.end_date:
                        p_dt = datetime.strptime(ev.peak_date, "%Y-%m-%d")
                        days_from_peak = abs((current_dt - p_dt).days)
                        surge = max(1.0, 1.0 + (ev.multiplier - 1.0) * math.exp(-0.5 * (days_from_peak / 1.5) ** 2))
                        lambda_absence *= surge
                        if ev.scenario_type == "heat_cluster":
                            is_heat_event_active = True

                absence_count = float(self._sample_neg_binom(lambda_absence, dispersion=0.25))

                all_observations.append(
                    SignalObservation(
                        signal_type="absence_heat",
                        geo_level="site",
                        geo_id=site_id,
                        obs_date=date_str,
                        value=absence_count,
                        denominator=float(workforce),
                        location_confidence="exact",
                    )
                )

                # Generate Safety Incident Reports (first aid logs)
                # Baseline 0.08 incidents / 1000 workers / day
                incident_lambda = workforce * 0.00008
                if is_outdoor and site_wbgt > 31.0:
                    incident_lambda *= 3.0
                if is_heat_event_active:
                    incident_lambda *= 4.5

                n_incidents = int(self.rng.poisson(incident_lambda))
                for _ in range(n_incidents):
                    raw_text, cat = self._generate_incident_narrative(
                        site=site,
                        wbgt=site_wbgt,
                        pm25=site_pm25,
                        is_heat_event=is_heat_event_active,
                    )
                    sanitized_text = sanitize_incident_narrative(raw_text)
                    pred_cat, conf = self.classifier.predict(sanitized_text)

                    all_incidents.append(
                        IncidentReport(
                            site_id=site_id,
                            district_id=dist_id,
                            obs_date=date_str,
                            narrative_sanitized=sanitized_text,
                            predicted_category=pred_cat,
                            confidence=conf,
                        )
                    )

        # 3. Apply Realistic Data Quality Defects & Latencies
        final_observations = self.defect_engine.apply_defects(all_observations)

        return final_observations, all_incidents, ground_truth

    def _sample_neg_binom(self, mean: float, dispersion: float = 0.15) -> int:
        """Sample from Negative Binomial distribution given mean and dispersion (var = mu + disp * mu^2)."""
        mu = max(mean, 0.01)
        # Parameterization: gamma shape k = 1 / dispersion, scale theta = disp * mu
        shape = 1.0 / dispersion
        scale = dispersion * mu
        poisson_lambda = self.rng.gamma(shape, scale)
        return int(self.rng.poisson(poisson_lambda))

    def _generate_incident_narrative(
        self,
        site: Dict[str, Any],
        wbgt: float,
        pm25: float,
        is_heat_event: bool,
    ) -> Tuple[str, str]:
        """Synthesize realistic narrative with embedded employee context."""
        site_name = site["name"]
        names = ["Ahmed Al-Balooshi", "Rajesh Kumar", "Muhammad Farooq", "Sanjay Patel", "Tariq Mansoor"]
        worker_name = self.rng.choice(names)
        badge_num = f"EMP-{self.rng.randint(1000, 9999)}"

        if (is_heat_event or wbgt >= 32.0) and self.rng.rand() < 0.75:
            # Heat scenario incident
            templates = [
                f"Worker {worker_name} ({badge_num}) suffered acute heat exhaustion and dizziness while pouring concrete at {site_name}. High ambient thermal stress.",
                f"Foreman observed {worker_name} staggering and disoriented due to sun exposure and heat cramps on staging platform at {site_name}.",
                f"Laborer {worker_name} collapsed during afternoon shift with signs of hyperthermia and dehydration at {site_name}. First aid administered.",
            ]
            return str(self.rng.choice(templates)), "heat"

        elif pm25 > 80.0 and self.rng.rand() < 0.40:
            # Pollution / respiratory incident
            templates = [
                f"Worker {worker_name} experienced severe coughing and acute asthma wheezing while handling dusty materials at {site_name}.",
                f"Painter {worker_name} ({badge_num}) inhaled airborne particulate and fumes, complaining of lung tightness at {site_name}.",
            ]
            return str(self.rng.choice(templates)), "respiratory_chemical"

        else:
            # Typical physical injury / slip / fall
            templates = [
                f"Worker {worker_name} ({badge_num}) slipped on metal grating and sprained right wrist at {site_name}.",
                f"Laborer {worker_name} sustained puncture wound to boot from protruding rebar wire at {site_name}.",
                f"Carpenter {worker_name} suffered finger laceration from hand tool while assembling formwork at {site_name}.",
            ]
            return str(self.rng.choice(templates)), "injury"

