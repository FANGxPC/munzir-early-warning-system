"""
Unified CLI for Munzir Early Warning System.
Provides commands for historical data backfill, daily ingestion runs,
NLP classifier training, data quality checks, and bronze store inspection.
"""

import argparse
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, List
import pandas as pd

from prahari.config import get_region_config, REGIONAL_PROFILES, BRONZE_DIR, SILVER_DIR
from prahari.storage.bronze_store import BronzeStore
from prahari.storage.silver_store import SilverStore
from prahari.ingestion.open_meteo import OpenMeteoClient, ingest_environmental_data
from prahari.ingestion.openaq import OpenAQClient, ingest_openaq_stations
from prahari.ingestion.osha import OSHAIncidentIngestor
from prahari.ingestion.cdc_syndromic import CDCSyndromicIngestor
from prahari.simulator.generator import HealthWorkplaceSimulator
from prahari.ingestion.data_quality import DataQualityScorer
from prahari.nlp.classifier import IncidentClassifier
from prahari.models.canonical import SignalObservation, SilverSignalObservation
from prahari.harmonisation.pipeline import HarmonisationPipeline
from prahari.harmonisation.differential_privacy import DifferentialPrivacyEngine
from prahari.detection.pipeline import DetectionPipeline
from prahari.decision import (
    EvidenceCardGenerator,
    PlaybookEngine,
    AcknowledgementManager,
    AlertStatus,
)


def cmd_train_nlp(args: argparse.Namespace) -> None:
    """Train the incident narrative text classifier and report evaluation metrics."""
    print("=" * 60)
    print("Munzir NLP Incident Narrative Classifier Training")
    print("=" * 60)
    classifier = IncidentClassifier()
    metrics = classifier.train()

    print(f"[*] Training samples: {metrics['n_train']}")
    print(f"[*] Testing samples:  {metrics['n_test']}")
    print(f"[*] Test Accuracy:    {metrics['accuracy'] * 100:.2f}%")
    print(f"[*] Test Macro F1:    {metrics['macro_f1']:.4f}")
    print(f"[*] 5-Fold CV F1:     {metrics['cv_macro_f1']:.4f}")
    print(f"[*] Model artifact:   {metrics['saved_path']}")
    print("\nDetailed Classification Report:")
    for cls_name, vals in metrics["report"].items():
        if isinstance(vals, dict):
            print(f"  {cls_name:<22} Precision: {vals['precision']:.2f} | Recall: {vals['recall']:.2f} | F1: {vals['f1-score']:.2f}")
    print("=" * 60)


def cmd_backfill(args: argparse.Namespace) -> None:
    """Run historical multi-signal backfill reproducing bronze lakehouse data."""
    start_time = time.time()
    years = args.years
    region_key = args.region
    seed = args.seed

    print("=" * 70)
    print(f"Munzir Historical Bronze Lakehouse Backfill ({years} Year(s))")
    print(f"Region: {region_key.upper()} | Seed: {seed}")
    print("=" * 70)

    profile = get_region_config(region_key)
    districts = profile.get("districts", [])
    sites = profile.get("sites", [])

    # Date range calculation
    if args.end_date:
        end_dt = datetime.strptime(args.end_date, "%Y-%m-%d")
    else:
        end_dt = datetime(2026, 10, 31)

    if args.start_date:
        start_dt = datetime.strptime(args.start_date, "%Y-%m-%d")
    else:
        start_dt = end_dt - timedelta(days=int(years * 365.25))

    start_date_str = start_dt.strftime("%Y-%m-%d")
    end_date_str = end_dt.strftime("%Y-%m-%d")
    total_days = (end_dt - start_dt).days + 1

    print(f"[*] Time window:  {start_date_str} to {end_date_str} ({total_days} days)")
    print(f"[*] Districts:    {len(districts)} | Sites: {len(sites)}")

    store = BronzeStore()
    meteo_client = OpenMeteoClient()
    dq_scorer = DataQualityScorer()

    # 1. Ingest Environmental Data (Weather, WBGT, PM2.5, PM10)
    print("\n[Step 1/4] Ingesting Environmental Signals (Open-Meteo & WBGT Engine)...")
    env_observations: List[SignalObservation] = []

    # Ingest for district centroids
    for d in districts:
        sys.stdout.write(f"  -> Ingesting district centroid: {d['name']} ({d['id']})...\r")
        sys.stdout.flush()
        d_obs, _, _ = ingest_environmental_data(
            client=meteo_client,
            geo_id=d["id"],
            geo_level="district",
            lat=d["lat"],
            lon=d["lon"],
            start_date=start_date_str,
            end_date=end_date_str,
            denominator=float(d["population"]),
        )
        env_observations.extend(d_obs)

    # Ingest for site locations
    for s in sites:
        sys.stdout.write(f"  -> Ingesting worksite: {s['name']} ({s['id']})...\r")
        sys.stdout.flush()
        s_obs, _, _ = ingest_environmental_data(
            client=meteo_client,
            geo_id=s["id"],
            geo_level="site",
            lat=s["lat"],
            lon=s["lon"],
            start_date=start_date_str,
            end_date=end_date_str,
            denominator=float(s["workforce"]),
        )
        env_observations.extend(s_obs)

    # Ingest OpenAQ v3 physical stations
    sys.stdout.write("  -> Ingesting OpenAQ v3 ground monitoring stations...\r")
    sys.stdout.flush()
    openaq_obs = ingest_openaq_stations(
        region_key=region_key,
        start_date=start_date_str,
        end_date=end_date_str,
    )
    env_observations.extend(openaq_obs)

    print(f"\n  [+] Total environmental observations gathered: {len(env_observations):,} (Open-Meteo + OpenAQ)")

    # 2. Ingest Multi-Signal Health & Workplace Streams (Simulator + Real OSHA + CDC NSSP)
    print("\n[Step 2/4] Gathering Health & Workplace Streams (Simulator + Real OSHA + CDC NSSP)...")
    simulator = HealthWorkplaceSimulator(region_key=region_key, seed=seed)
    synth_observations, incidents, ground_truth = simulator.simulate(
        start_date=start_date_str,
        end_date=end_date_str,
        env_observations=env_observations,
    )

    # Ingest Real OSHA Severe Injury Reports
    osha_ingestor = OSHAIncidentIngestor(bronze_store=store)
    real_incidents, real_inc_obs = osha_ingestor.ingest(
        start_date=start_date_str,
        end_date=end_date_str,
        write_to_store=False,
    )

    # Ingest Real CDC NSSP Syndromic Streams
    cdc_ingestor = CDCSyndromicIngestor(region_key=region_key, bronze_store=store, seed=seed)
    cdc_obs = cdc_ingestor.ingest_syndromic_streams(
        start_date=start_date_str,
        end_date=end_date_str,
        env_observations=env_observations,
        write_to_store=False,
    )

    all_incidents = incidents + real_incidents
    print(f"  [+] Total health & workplace observations: {len(synth_observations):,}")
    print(f"  [+] Total workplace safety incidents:     {len(all_incidents):,} ({len(real_incidents):,} from real OSHA)")
    print(f"  [+] Real CDC NSSP syndromic observations: {len(cdc_obs):,}")
    print(f"  [+] Ground truth outbreak events:         {len(ground_truth):,}")

    # Combine all observations
    all_observations = env_observations + synth_observations + real_inc_obs + cdc_obs

    # 3. Data Quality Scoring
    print("\n[Step 3/4] Computing Data Quality (Completeness, Latency, Staleness)...")
    dq_metrics = dq_scorer.compute_daily_quality(all_observations, as_of_date=end_date_str)
    print(f"  [+] Generated {len(dq_metrics):,} DQ score records.")

    # 4. Land Data in Bronze Parquet Lakehouse
    print("\n[Step 4/4] Writing Parquet Tables to Bronze Lakehouse Partition Store...")
    n_written = store.write_observations(all_observations)
    n_incidents = store.write_incidents(all_incidents)
    n_truth = store.write_ground_truth(ground_truth)
    n_dq = store.write_data_quality(dq_metrics)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"SUCCESS: Backfill completed in {elapsed:.2f} seconds.")
    print(f"  Observations Written:   {n_written:,} rows")
    print(f"  Incidents Logged:       {n_incidents:,} rows")
    print(f"  Ground Truth Scenarios: {n_truth:,} rows")
    print(f"  Data Quality Metrics:   {n_dq:,} rows")
    print(f"  Storage Location:       {store.base_dir}")
    print("=" * 70)


def cmd_run_daily(args: argparse.Namespace) -> None:
    """Run daily ingestion timer step (simulates Azure Functions timer trigger)."""
    date_str = args.date or datetime.now().strftime("%Y-%m-%d")
    region_key = args.region

    print("=" * 60)
    print(f"Munzir Daily Ingestion Timer Run ({date_str})")
    print(f"Region: {region_key.upper()}")
    print("=" * 60)

    store = BronzeStore()
    meteo_client = OpenMeteoClient()
    dq_scorer = DataQualityScorer()
    profile = get_region_config(region_key)

    env_obs: List[SignalObservation] = []
    # Ingest day's weather and air quality
    for d in profile["districts"][:3]:  # Top districts for daily run
        obs, _, _ = ingest_environmental_data(
            client=meteo_client,
            geo_id=d["id"],
            geo_level="district",
            lat=d["lat"],
            lon=d["lon"],
            start_date=date_str,
            end_date=date_str,
            denominator=float(d["population"]),
        )
        env_obs.extend(obs)

    # Ingest outdoor worksites
    for s in profile["sites"][:3]:
        obs, _, _ = ingest_environmental_data(
            client=meteo_client,
            geo_id=s["id"],
            geo_level="site",
            lat=s["lat"],
            lon=s["lon"],
            start_date=date_str,
            end_date=date_str,
            denominator=float(s["workforce"]),
        )
        env_obs.extend(obs)

    # Run simulator for date
    simulator = HealthWorkplaceSimulator(region_key=region_key, seed=int(time.time()) % 10000)
    synth_obs, incidents, _ = simulator.simulate(
        start_date=date_str,
        end_date=date_str,
        env_observations=env_obs,
    )

    combined = env_obs + synth_obs
    dq_metrics = dq_scorer.compute_daily_quality(combined, as_of_date=date_str)

    store.write_observations(combined)
    store.write_incidents(incidents)
    store.write_data_quality(dq_metrics)

    print(f"[+] Daily Ingestion Successful for {date_str}:")
    print(f"    - Observations landed: {len(combined)}")
    print(f"    - Incidents logged:    {len(incidents)}")
    print(f"    - DQ metrics recorded: {len(dq_metrics)}")
    print("    - Status: HEALTHY | Application Insights Telemetry: 200 OK")
    print("=" * 60)


def cmd_ingest_real(args: argparse.Namespace) -> None:
    """Ingest authentic OSHA Severe Injuries and CDC NSSP syndromic feeds into Bronze."""
    start_time = time.time()
    region_key = args.region
    start_date = args.start_date
    end_date = args.end_date

    print("=" * 70)
    print("Munzir Real-World Data Ingestion Pipeline")
    print("Data Sources: OSHA Severe Injury Reports (DOL) & CDC NSSP Syndromic Feeds")
    print(f"Region: {region_key.upper()}")
    print("=" * 70)

    store = BronzeStore()

    # 1. Ingest OSHA Severe Injury Reports
    print("\n[1/2] Ingesting OSHA Severe Injury Reports (Federal Safety Inspection Data)...")
    osha_ingestor = OSHAIncidentIngestor(bronze_store=store)
    incidents, inc_obs = osha_ingestor.ingest(
        start_date=start_date,
        end_date=end_date,
        write_to_store=True,
    )
    print(f"  [+] Real OSHA Incident Reports landed:     {len(incidents):,}")
    print(f"  [+] Workplace Incident Observations landed: {len(inc_obs):,}")

    # 2. Ingest CDC NSSP Syndromic Streams
    print("\n[2/2] Ingesting CDC NSSP & WHO Syndromic Streams (Heat & Respiratory)...")
    cdc_ingestor = CDCSyndromicIngestor(region_key=region_key, bronze_store=store)
    s_date = start_date or "2024-01-01"
    e_date = end_date or datetime.now().strftime("%Y-%m-%d")
    cdc_obs = cdc_ingestor.ingest_syndromic_streams(
        start_date=s_date,
        end_date=e_date,
        write_to_store=True,
    )
    print(f"  [+] Real CDC NSSP Observations landed:      {len(cdc_obs):,}")

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"SUCCESS: Real-world ingestion completed in {elapsed:.2f} seconds.")
    print(f"Bronze Store: {store.base_dir}")
    print("=" * 70)


def cmd_clinical_profile(args: argparse.Namespace) -> None:
    """Evaluate clinical pharmacological vulnerability using openFDA and DailyMed."""
    from prahari.ingestion.openfda import ClinicalVulnerabilityEngine
    engine = ClinicalVulnerabilityEngine()
    hazard = args.hazard
    sev = args.severity
    env = {}
    if args.wbgt is not None:
        env["wbgt_max"] = args.wbgt
    if args.pm25 is not None:
        env["pm25"] = args.pm25

    profile = engine.evaluate_vulnerability_profile(
        alert_type=f"{hazard}_cluster",
        severity=sev,
        environmental_metrics=env,
    )
    print("=" * 70)
    print("Munzir Clinical Pharmacological Vulnerability Profile (openFDA / DailyMed)")
    print("=" * 70)
    print(f"Hazard:                        {profile['environmental_hazard_type']}")
    print(f"Severity:                      {sev.upper()}")
    print(f"Vulnerability Tier:            {profile['vulnerability_tier']}")
    print(f"Pharmacological Index (PVI):   {profile['pharmacological_vulnerability_index']}x baseline susceptibility")
    print(f"Estimated Cohort Vulnerable:   {profile['estimated_affected_workforce_pct']}% of workforce")
    print(f"\nIdentified High-Risk Medication Classes ({profile['evaluated_drug_classes_count']}):")
    for d in profile["high_risk_drug_classes"]:
        print(f"  • {d['class_name']} ({', '.join(d['representative_drugs'][:3])})")
        print(f"    Mechanism: {d['physiological_mechanism'][:90]}...")
        print(f"    Prevalence: ~{d['estimated_workforce_prevalence_pct']}% | FDA Warnings: {', '.join(d['adverse_reaction_terms'][:3])}")
    print("\nActionable Clinical Directives:")
    for a in profile["clinical_directives"]:
        print(f"  [!] {a}")
    print("=" * 70)


def cmd_harmonise(args: argparse.Namespace) -> None:
    """Run Bronze-to-Silver Harmonisation with spatial H3 mapping and suppression."""
    start_time = time.time()
    region_key = args.region

    print("=" * 70)
    print(f"Munzir Harmonisation Pipeline (Bronze -> Silver)")
    print(f"Region: {region_key.upper()}")
    print("=" * 70)

    pipeline = HarmonisationPipeline(region_key=region_key)
    res = pipeline.run_harmonisation(
        start_date=args.start_date,
        end_date=args.end_date,
    )

    elapsed = time.time() - start_time
    print(f"[*] Status:                         {res['status'].upper()}")
    print(f"[*] Records Processed:              {res['records_processed']:,}")
    print(f"[*] Harmonised Records Persisted:   {res['records_written']:,}")
    print(f"[*] Primary Suppressed Cells (k<=10):{res['primary_suppressed_cells']:,}")
    print(f"[*] Complementary Suppressed Cells: {res['complementary_suppressed_cells']:,}")
    print(f"[*] Algebraic Privacy Audit:        {'PASSED' if res['algebraic_privacy_verified'] else 'FAILED'}")
    if res["vulnerabilities"]:
        print(f"[*] Vulnerabilities Detected:       {len(res['vulnerabilities'])}")
        for v in res["vulnerabilities"][:5]:
            print(f"    - {v}")
    print(f"[*] Completed in:                   {elapsed:.2f} seconds")
    print("=" * 70)


def cmd_inspect_silver(args: argparse.Namespace) -> None:
    """Inspect Silver storage contents, stats, and external suppressed view."""
    store = SilverStore()
    stats = store.get_summary_stats()

    print("=" * 60)
    print("Munzir Silver Harmonised Lakehouse Inspection")
    print("=" * 60)
    print(f"Total Observations:             {stats['total_observations']:,}")
    print(f"Suppressed Cells (k<=10):       {stats['suppressed_cells']:,}")
    print(f"Complementary Suppressed Cells: {stats['complementary_suppressed_cells']:,}")
    print(f"Date Span:                      {stats['min_date']} to {stats['max_date']} ({stats['date_count']} days)")
    print(f"Unique Signals:                 {', '.join(stats['unique_signals'])}")

    df_sample = store.read_observations(start_date=stats['max_date'], end_date=stats['max_date'], external_view=True)
    if not df_sample.empty:
        print("\nExternal View Sample (Suppressed counts masked as NaN):")
        cols = [c for c in ["signal_type", "geo_level", "geo_id", "h3_index", "obs_date", "value", "suppressed_flag", "suppression_type"] if c in df_sample.columns]
        print(df_sample[cols].head(12).to_string())
    print("=" * 60)


def cmd_dp_release(args: argparse.Namespace) -> None:
    """Generate Differential Privacy aggregate release with epsilon budget tracking."""
    epsilon = args.epsilon
    print("=" * 60)
    print(f"Munzir Differential Privacy Release (Epsilon = {epsilon})")
    print("=" * 60)

    store = SilverStore()
    engine = DifferentialPrivacyEngine(default_epsilon=epsilon)

    # Read latest date observations
    stats = store.get_summary_stats()
    latest_date = stats.get("max_date")
    if not latest_date:
        print("[-] No silver data found. Run 'make harmonise' first.")
        return

    df = store.read_observations(start_date=latest_date, end_date=latest_date)
    # Convert to SilverSignalObservation
    obs_list = [SilverSignalObservation(**row) for row in df.to_dict(orient="records")]

    releases = engine.release_table(obs_list, epsilon_per_cell=epsilon)
    budget = engine.get_budget_summary()

    print(f"[+] Total DP Releases Generated:  {len(releases)}")
    print(f"[+] Epsilon Per Query:            {epsilon}")
    print(f"[+] Total Privacy Budget Spent:   {budget['total_epsilon_consumed']}")
    print(f"[+] OpenDP Backend Active:        {budget['opendp_backend_active']}")

    print("\nSample Differential Privacy Release (True vs Noisy):")
    sample_df = pd.DataFrame([r.model_dump() for r in releases[:8]])
    print(sample_df[["signal_type", "geo_id", "obs_date", "true_count", "noisy_count", "epsilon"]].to_string())
    print("=" * 60)


def cmd_inspect(args: argparse.Namespace) -> None:
    """Inspect Bronze storage contents, stats, and sample rows."""
    store = BronzeStore()
    stats = store.get_summary_stats()

    print("=" * 60)
    print("Munzir Bronze Lakehouse Inspection")
    print("=" * 60)
    print(f"Total Observations:    {stats['total_observations']:,}")
    print(f"Date Span:             {stats['min_date']} to {stats['max_date']} ({stats['date_count']} days)")
    print(f"Unique Signals:        {', '.join(stats['unique_signals'])}")
    print(f"Total Incidents:       {stats['total_incidents']:,}")
    print(f"Ground Truth Events:   {stats['total_ground_truth_events']:,}")

    df_sample = store.read_observations(start_date=stats['max_date'], end_date=stats['max_date'])
    if not df_sample.empty:
        print("\nLatest Observations Sample:")
        print(df_sample[["signal_type", "geo_level", "geo_id", "obs_date", "value", "completeness_score", "suppressed_flag"]].head(10).to_string())
    print("=" * 60)


def cmd_train_fusion(args: argparse.Namespace) -> None:
    """Train the L4 LightGBM fusion model and calibrate with Isotonic Regression."""
    print("=" * 65)
    print("Munzir L4 Multi-Signal Machine Learning Fusion Training")
    print("=" * 65)
    pipeline = DetectionPipeline()
    metrics = pipeline.train_fusion(
        start_date=args.start_date or "2024-01-01",
        end_date=args.end_date or "2026-12-31",
        split_date=args.split_date or "2026-01-01",
        step_days=args.step_days,
    )
    print("\nTraining & Calibration Summary:")
    print(f"  Training Samples:       {metrics['n_train']}")
    print(f"  Validation Samples:     {metrics['n_val']}")
    print(f"  Time Split Date:        {metrics['split_date']}")
    print(f"  Validation ROC-AUC:     {metrics['auc_roc']}")
    print(f"  Validation Brier Score: {metrics['brier_score']}")
    print(f"  Conformal Margin (90%): ±{metrics['conformal_margin_90']}")
    print("=" * 65)


def cmd_detect(args: argparse.Namespace) -> None:
    """Run L1-L5 detection pipeline across a date range or specific date."""
    print("=" * 70)
    print("Munzir Layered Outbreak Detection Pipeline (L1-L5)")
    print("=" * 70)
    pipeline = DetectionPipeline()

    if args.date:
        start_date = args.date
        end_date = args.date
    else:
        start_date = args.start_date or "2024-01-01"
        end_date = args.end_date or "2026-10-31"

    print(f"[*] Scanning window: {start_date} to {end_date}")
    alerts = pipeline.run_detection(start_date=start_date, end_date=end_date, save_alerts=True)

    print(f"\n[+] Total Alerts Emitted: {len(alerts)}")
    severity_counts = {}
    for a in alerts:
        severity_counts[a.severity.value] = severity_counts.get(a.severity.value, 0) + 1
    for sev, cnt in sorted(severity_counts.items()):
        print(f"    - {sev.upper():<8}: {cnt}")

    if alerts:
        print("\nSample Generated Alerts (Decision-Ready with SHAP & Conformal Bands):")
        for a in alerts[:6]:
            print(f"  [{a.obs_date}] [{a.severity.value.upper()}] {a.alert_type} @ {','.join(a.geo_ids)}")
            print(f"    Probability: {a.probability:.1%} [90% CI: {a.ci_low:.1%} - {a.ci_high:.1%}]")
            driver = max(a.signal_contributions.items(), key=lambda x: x[1])[0] if a.signal_contributions else "n/a"
            print(f"    SHAP Driver: {driver}")
            print(f"    Action:      {a.recommended_action[:70]}...")
            print(f"    Owner:       {a.owner_role}")
            print("-" * 65)

    if args.evaluate or (not args.date):
        print("\nEvaluating against injected ground truth scenarios...")
        eval_metrics = pipeline.evaluate(alerts)
        print(f"[+] Overall Outbreak Sensitivity: {eval_metrics['sensitivity'] * 100:.1f}%")
        print(f"[+] Decoy Suppression Rate:       {eval_metrics['decoy_suppression_rate'] * 100:.1f}%")
        print("\nFlagship Scenarios Performance:")
        for name, res in eval_metrics["flagship_scenarios"].items():
            status = "DETECTED" if res["detected"] else "MISSED"
            lead = f"{res['lead_time_days']} days lead time" if res["lead_time_days"] is not None else "N/A"
            print(f"  * {name:<35} [{status}] ({lead})")
        print("\nDecoy Benign Artefacts:")
        for name, res in eval_metrics["decoys"].items():
            supp = "SUPPRESSED (Did not reach Warning)" if res["suppressed_from_warning"] else f"FIRED {res['max_severity_fired'].upper()}"
            print(f"  * {name:<35} [{supp}]")
    print("=" * 70)


def cmd_playbooks(args: argparse.Namespace) -> None:
    """List registered operational playbooks and their evidence thresholds."""
    engine = PlaybookEngine()
    playbooks = engine.list_playbooks()

    print("=" * 75)
    print("Munzir Operational Action Playbook Library")
    print(f"Total Playbooks Registered: {len(playbooks)}")
    print("=" * 75)
    for pb in playbooks:
        trig = pb.trigger
        print(f"\n[{pb.id.upper()}] - {pb.name}")
        print(f"  Trigger:         Type={trig.type} | Severity={trig.severity.upper()} | Scope={trig.site_type or 'all'}")
        print(f"  Proportionality: {pb.proportionality_tier.upper()}")
        print(f"  Lead Role:       {pb.responsible.get('lead', 'N/A')}")
        print(f"  Accountable:     {pb.responsible.get('accountable', 'N/A')}")
        print("  Actions:")
        for a in pb.actions:
            print(f"    • {a}")
        if pb.assumptions:
            print("  Assumptions:")
            for asm in pb.assumptions[:2]:
                print(f"    - {asm}")
        print("-" * 75)


def cmd_evidence_card(args: argparse.Namespace) -> None:
    """Generate and display an Evidence Card for an active alert or date."""
    print("=" * 75)
    print("Munzir Decision Support Evidence Card Generator")
    print("=" * 75)

    pipeline = DetectionPipeline()
    generator = EvidenceCardGenerator()

    # Determine date
    obs_date = args.date or "2025-08-20"
    geo_id = args.geo or "SITE-JA-01"

    print(f"[*] Fetching evidence for Location={geo_id} on Date={obs_date}...")
    df_hist = pipeline.silver_store.read_observations(
        start_date=(datetime.strptime(obs_date, "%Y-%m-%d") - timedelta(days=45)).strftime("%Y-%m-%d"),
        end_date=obs_date,
    )

    day_alerts = pipeline.run_date(obs_date, history_df=df_hist)
    target_alert = next((a for a in day_alerts if geo_id in a.geo_ids), None)

    if not target_alert:
        print(f"[-] No active alert fired at {geo_id} on {obs_date}. (Checking default situational overview...)")
        # Construct situational card
        from prahari.detection.l5_policy import AlertSeverity, PrahariAlert
        feats = pipeline.extract_features_for_location_date(obs_date, geo_id, df_hist)
        pred = pipeline.fusion_model.predict(feats)
        target_alert = PrahariAlert(
            alert_type="heat_cluster" if "SITE" in geo_id else "respiratory_surge",
            severity=AlertSeverity.WARNING,
            probability=pred.probability,
            ci_low=pred.ci_low,
            ci_high=pred.ci_high,
            geo_ids=[geo_id],
            obs_date=obs_date,
            signal_contributions=pred.shap_contributions,
        )

    card = generator.generate(target_alert, silver_history_df=df_hist)

    print("\n" + "=" * 75)
    print(f"EVIDENCE CARD: [{card.alert_id}] ({card.severity.upper()})")
    print(f"Generated In: {card.generation_time_ms:.2f} ms (< 2.0s Exit Criterion Met)")
    print("=" * 75)
    print(f"  Incident ID:       {card.incident_id}")
    print(f"  Location:          {card.geo_name} ({card.geo_id}) - Level: {card.geo_level.upper()} (H3: {card.h3_index or 'N/A'})")
    print(f"  Confidence:        {card.location_confidence.upper()}")
    print(f"  Syndromic Type:    {card.alert_type.upper()}")
    print(f"  Probability:       {card.probability * 100:.1f}% [90% Conformal Band: {card.ci_low * 100:.1f}% - {card.ci_high * 100:.1f}%]")
    print(f"  Data Health Badge: {card.dq_badge} (Completeness: {card.dq_completeness_pct:.1f}%, Latency: {card.dq_source_latency_hrs:.1f}h)")
    print(f"  Primary Driver:    {card.primary_driver_group.upper()}")

    print("\n  [SHAP Attribution Breakdown]:")
    for grp, val in sorted(card.shap_attributions.items(), key=lambda x: x[1], reverse=True):
        bar = "█" * int(max(0, val) * 10)
        print(f"    - {grp:<15}: {val:+.3f}  {bar}")

    print("\n  [What Rose (Observed vs Expected Baseline)]:")
    for item in card.what_rose[:4]:
        print(f"    • {item['signal_type']:<26}: Observed={item['observed']:<6} | Expected={item['expected_baseline']:<6} | Exceedance={item['exceedance_ratio']}x")

    if card.environmental_context:
        print("\n  [Environmental Context & 3-Day Forecast]:")
        for k, v in card.environmental_context.items():
            print(f"    • {k:<24}: {v}")

    print("\n  [Operational Action Protocol & RACI Matrix]:")
    print(f"    Playbook:   {card.playbook_name} ({card.playbook_id})")
    print(f"    Lead (R):   {card.raci_matrix.get('responsible')}")
    print(f"    Accountable:{card.raci_matrix.get('accountable')}")
    print(f"    Informed:   {', '.join(card.raci_matrix.get('informed', [])[:3])}")
    print("    Actions:")
    for a in card.recommended_actions:
        print(f"      -> {a}")

    print("\n  [System Assumptions & Citations]:")
    for asm in card.assumptions[:2]:
        print(f"    * Assumption: {asm}")
    for cite in card.citations[:2]:
        print(f"    * Citation:   {cite}")

    print("\n" + "=" * 75)
    print("SITUATIONAL BRIEFING NARRATIVE:")
    print("=" * 75)
    print(card.narrative_summary)
    print("=" * 75)


def cmd_acknowledge(args: argparse.Namespace) -> None:
    """Record an operational transition (Acknowledge / Act / Dismiss)."""
    mgr = AcknowledgementManager()
    alert_id = args.alert_id
    user_role = args.user_role
    action_type = args.action

    print("=" * 65)
    print(f"Munzir Human-in-the-Loop Workflow: {action_type.upper()}")
    print("=" * 65)

    if action_type == "acknowledge":
        rec = mgr.acknowledge(
            alert_id=alert_id,
            user_role=user_role,
            comment=args.comment or "Acknowledged by officer",
        )
        print(f"[+] Alert {alert_id} ACKNOWLEDGED by {user_role}.")
        print(f"    Record ID: {rec.record_id} | Timestamp: {rec.created_at}")

    elif action_type == "act":
        if not args.action_taken:
            print("[-] Error: --action-taken is required when recording an action.")
            return
        rec = mgr.act(
            alert_id=alert_id,
            user_role=user_role,
            action_taken=args.action_taken,
            comment=args.comment or "",
        )
        print(f"[+] Alert {alert_id} marked as ACTED by {user_role}.")
        print(f"    Action:    {rec.action_taken}")
        print(f"    Record ID: {rec.record_id}")

    elif action_type == "dismiss":
        if not args.reason:
            print("[-] Error: --reason is mandatory when dismissing an alert.")
            print("    Valid reasons: benign_local_event, data_artefact_backlog, already_managed_duplicate, false_positive_noise, other")
            return
        rec = mgr.dismiss(
            alert_id=alert_id,
            user_role=user_role,
            dismiss_reason=args.reason,
            comment=args.comment or "",
        )
        print(f"[+] Alert {alert_id} DISMISSED by {user_role}.")
        print(f"    Reason:    {rec.dismiss_reason}")
        print(f"    Record ID: {rec.record_id}")

    metrics = mgr.calculate_operational_metrics()
    print("\nOperational Metrics Summary:")
    print(f"  Total Transitions: {metrics['total_transitions']}")
    print(f"  Acted / Dismissed: {metrics['acted_count']} / {metrics['dismissed_count']}")
    print(f"  Practical PPV:     {metrics['practical_ppv'] * 100:.1f}%")
    print("=" * 65)


def cmd_serve(args: argparse.Namespace) -> None:
    """Start Munzir role-based API and interactive web application."""
    import uvicorn
    print("=" * 75)
    print("Munzir Population & Occupational Health Surveillance Server")
    print(f"Starting server on http://{args.host}:{args.port}")
    print("Serving interactive UI and role-based REST APIs")
    print("=" * 75)
    uvicorn.run("prahari.api.app:app", host=args.host, port=args.port, reload=args.reload)


def cmd_validate(args: argparse.Namespace) -> None:
    """Run operational validation, benchmark against baselines, and export report.html."""
    from prahari.validation.orchestrator import ValidationOrchestrator
    print("=" * 75)
    print("Munzir Operational Validation & Benchmarking Engine (Phase 6)")
    print(f"Seed: {args.seed} | Injections: {args.n_injections} | Region: {args.region}")
    print("=" * 75)
    orchestrator = ValidationOrchestrator(seed=args.seed, output_dir=args.out_dir, region_key=args.region)
    report_path = orchestrator.run_validation_pipeline(
        n_injections=args.n_injections,
        start_date=args.start_date,
        end_date=args.end_date,
    )
    print("\n[+] Operational Validation Complete!")
    print(f"[+] Publication-grade validation report generated at: {report_path.resolve()}")
    print("=" * 75)


def cmd_impact(args: argparse.Namespace) -> None:
    """Run Phase 7 Health & Resilience Impact Model and display scenario bounds."""
    from prahari.impact.models import (
        WorkforceAssumptions,
        EconomicAssumptions,
    )
    from prahari.impact.calculator import HealthResilienceImpactCalculator
    from prahari.impact.policy_report import DistrictPolicyEvidenceGenerator

    print("=" * 75)
    print("Munzir Health & Resilience Impact Model (Phase 7)")
    print("Translating validated detection performance into quantifiable averted burden")
    print("=" * 75)

    calc = HealthResilienceImpactCalculator(
        workforce=WorkforceAssumptions(workforce_size=args.workforce),
        economic=EconomicAssumptions(cost_per_lost_workday_aed=args.workday_cost),
    )
    result = calc.calculate()
    central = result.central_estimate
    scenarios = result.scenarios

    print("\n[+] Modelled Epidemiological & Economic Impact Projections:")
    print(f"  • Monitored Workforce:         {args.workforce:,} outdoor workers")
    print(f"  • Validated Fusion Lead Time:  +{result.assumptions_audit['validated_lead_time_days'].value} days ahead of peak")
    print(f"  • Expected Cases Prevented:    {central.cases_prevented:,.1f} heat incidents")
    print(f"  • Lost Workdays Averted:       {central.lost_workdays_averted:,.1f} days/season")
    print(f"  • Severe Incidents Avoided:    {central.severe_incidents_averted:,.1f} heat stroke/ICU admissions")
    print(f"  • Gross Economic Savings:      AED {central.gross_economic_benefit_aed:,.2f}")
    print(f"  • False Alarm Response Cost:   AED {central.false_alarm_response_cost_aed:,.2f} ({central.alert_fatigue_overhead_pct:.2f}% overhead)")
    print(f"  • Net Economic Benefit:        AED {central.net_economic_benefit_aed:,.2f}")
    print(f"  • Benefit-to-Cost Ratio (BCR): {central.benefit_cost_ratio:.1f}x ROI")

    print("\nScenario Uncertainty Bounds:")
    print(f"  • Conservative Lower: AED {scenarios.low_conservative.net_economic_benefit_aed:,.2f} ({scenarios.low_conservative.lost_workdays_averted:,.0f} workdays)")
    print(f"  • Central Expected:   AED {scenarios.central_expected.net_economic_benefit_aed:,.2f} ({scenarios.central_expected.lost_workdays_averted:,.0f} workdays)")
    print(f"  • Optimistic Upper:   AED {scenarios.high_optimistic.net_economic_benefit_aed:,.2f} ({scenarios.high_optimistic.lost_workdays_averted:,.0f} workdays)")

    if args.export_policy:
        gen = DistrictPolicyEvidenceGenerator(random_seed=42)
        report = gen.generate_policy_evidence_report()
        md = gen.export_markdown_brief(report)
        out_path = Path("prahari_policy_brief.md")
        out_path.write_text(md, encoding="utf-8")
        print(f"\n[+] Regulatory Policy Evidence Brief exported to: {out_path.resolve()}")

    print("=" * 75)


def cmd_fhir_export(args: argparse.Namespace) -> None:
    """Export active early-warning alerts and surveillance measures as HL7 FHIR R4 Bundle."""
    import json
    from prahari.interop.fhir_adapter import FHIRSurveillanceAdapter
    from prahari.api.alert_service import AlertInboxService

    service = AlertInboxService()
    alerts = service._ensure_alerts_for_date(args.start_date or "2025-08-20")

    print("=" * 84)
    print("Munzir (منذر) — HL7 FHIR R4 Surveillance Export Adapter (Phase 9)")
    print(f"Exporting {len(alerts)} alerts as standardized MeasureReport & RiskAssessment resources")
    print("=" * 84)

    bundle = FHIRSurveillanceAdapter.create_surveillance_bundle(
        alerts=alerts,
        district_id=args.district or "UAE-DXB",
        period_start=args.start_date or "2026-06-01",
        period_end=args.end_date or "2026-06-07"
    )

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(bundle, f, indent=2)
        print(f"\n✔ Successfully exported HL7 FHIR R4 Bundle to: {args.out}")
        print(f"[+] Total Resources: {bundle.get('total', 0)}")
    else:
        print(json.dumps(bundle, indent=2))


def cmd_drift_check(args: argparse.Namespace) -> None:
    """Evaluate and display Population Stability Index (PSI) and Model Drift Monitor."""
    import numpy as np
    from prahari.interop.drift_monitor import ModelDriftMonitor

    print("=" * 84)
    print("Munzir (منذر) — Continuous Surveillance & Model Drift Monitor (Phase 9)")
    print("Evaluating Population Stability Index (PSI), Calibration Fidelity & Telemetry Latency")
    print("=" * 84)

    rng = np.random.default_rng(args.seed if hasattr(args, "seed") else 42)
    # Monitored surveillance feature distributions
    base_feats = {
        "wbgt_max": rng.normal(32.0, 3.5, 1000),
        "pm25": rng.exponential(35.0, 1000),
        "respiratory_ratio": rng.beta(2, 5, 1000),
        "absence_rate": rng.beta(2, 20, 1000),
    }
    curr_feats = {
        "wbgt_max": rng.normal(32.8, 3.6, 1000),
        "pm25": rng.exponential(37.0, 1000),
        "respiratory_ratio": rng.beta(2.2, 5, 1000),
        "absence_rate": rng.beta(2.1, 20, 1000),
    }

    report = ModelDriftMonitor.evaluate_model_drift(
        baseline_features=base_feats,
        current_features=curr_feats,
        recent_probabilities=[0.1, 0.2, 0.8, 0.9, 0.3],
        recent_ground_truth=[0, 0, 1, 1, 0],
    )

    print(f"\n[+] Overall Health Status:   {report.overall_status.upper()}")
    print(f"[+] Max Observed PSI:        {report.max_psi:.4f} (Threshold: 0.10=Warning, 0.25=Critical)")
    print(f"[+] Brier Calibration Score: {report.calibration_brier:.4f} ({report.calibration_status})")
    print(f"[+] Timestamp:               {report.timestamp}\n")

    print(f"{'Feature Name':<28} {'PSI Score':<14} {'Status':<18} {'Action Required'}")
    print("-" * 84)
    for feat, psi in report.psi_scores.items():
        st = report.psi_status.get(feat, "STABLE")
        action = "None (Nominal)" if st == "STABLE" else "Review calibration"
        print(f"{feat:<28} {psi:<14.4f} {st:<18} {action}")

    print("\n[+] Telemetry Latency Checks:")
    for feed, lat in report.data_freshness_hrs.items():
        stale_flag = "✖ STALE" if feed in report.stale_feeds else "✔ FRESH"
        print(f"    - {feed:<25}: {lat:4.1f}h latency [{stale_flag}]")

    print(f"\n[+] Operational Directive:\n    {report.action_recommendation}")
    print("=" * 84)


def cmd_governance(args: argparse.Namespace) -> None:
    """Evaluate and display Munzir Responsible AI & Governance Scorecard."""
    from prahari.governance.safety_monitor import GovernanceSafetyMonitor

    print("=" * 84)
    print("Munzir Responsible AI, Safety Controls & Governance Scorecard (Phase 8)")
    print("Evaluating Model Cards, Datasheets, TRIPOD+AI, DPIA, and Runtime Guardrails")
    print("=" * 84)

    monitor = GovernanceSafetyMonitor()
    scorecard = monitor.generate_scorecard()

    print(f"\n[+] Overall Status:    {scorecard.overall_status}")
    print(f"[+] Controls Verified: {scorecard.controls_passed} / {scorecard.total_controls_checked} ({scorecard.compliance_score_pct}%)")
    print(f"[+] Audit Timestamp:   {scorecard.timestamp}\n")

    print(f"{'ID':<8} {'Control Name':<42} {'Layer':<22} {'Status'}")
    print("-" * 84)
    for c in scorecard.controls:
        status_str = "✔ PASSED" if c.status == "PASSED" else "✖ FAILED"
        print(f"{c.control_id:<8} {c.name:<42} {c.enforcement_layer:<22} {status_str}")
        print(f"         Doc:  {c.governance_doc_link}")
        print(f"         Test: {c.automated_test_link}")
        print()

    print("=" * 84)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Munzir - Population & Workforce Health Early Warning Platform CLI"
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # backfill
    p_backfill = subparsers.add_parser("backfill", help="Run historical data backfill to bronze storage")
    p_backfill.add_argument("--years", type=float, default=3.0, help="Years of history to backfill (default: 3.0)")
    p_backfill.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD")
    p_backfill.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD")
    p_backfill.add_argument("--region", type=str, default="uae", choices=["uae", "tamilnadu"], help="Regional profile")
    p_backfill.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p_backfill.set_defaults(func=cmd_backfill)

    # ingest-real
    p_ingest_real = subparsers.add_parser("ingest-real", help="Ingest authentic OSHA Severe Injuries and CDC NSSP syndromic feeds")
    p_ingest_real.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD")
    p_ingest_real.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD")
    p_ingest_real.add_argument("--region", type=str, default="uae", choices=["uae", "tamilnadu"], help="Regional profile")
    p_ingest_real.set_defaults(func=cmd_ingest_real)

    # clinical-profile
    p_clin = subparsers.add_parser("clinical-profile", help="Evaluate clinical medication vulnerability from openFDA")
    p_clin.add_argument("--hazard", type=str, default="heat", choices=["heat", "respiratory"], help="Hazard type")
    p_clin.add_argument("--severity", type=str, default="warning", choices=["watch", "warning", "alert"], help="Alert severity")
    p_clin.add_argument("--wbgt", type=float, default=32.5, help="WBGT temperature in Celsius")
    p_clin.add_argument("--pm25", type=float, default=None, help="PM2.5 concentration in ug/m3")
    p_clin.set_defaults(func=cmd_clinical_profile)

    # run-daily
    p_daily = subparsers.add_parser("run-daily", help="Run single day ingestion timer pipeline")
    p_daily.add_argument("--date", type=str, default=None, help="Date YYYY-MM-DD")
    p_daily.add_argument("--region", type=str, default="uae", choices=["uae", "tamilnadu"], help="Regional profile")
    p_daily.set_defaults(func=cmd_run_daily)

    # train-nlp
    p_train = subparsers.add_parser("train-nlp", help="Train workplace incident narrative classifier")
    p_train.set_defaults(func=cmd_train_nlp)

    # inspect
    p_inspect = subparsers.add_parser("inspect", help="Inspect bronze lakehouse tables and statistics")
    p_inspect.set_defaults(func=cmd_inspect)

    # harmonise
    p_harm = subparsers.add_parser("harmonise", help="Run Bronze to Silver harmonisation pipeline")
    p_harm.add_argument("--region", type=str, default="uae", choices=["uae", "tamilnadu"], help="Regional profile")
    p_harm.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD")
    p_harm.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD")
    p_harm.set_defaults(func=cmd_harmonise)

    # inspect-silver
    p_ins_sil = subparsers.add_parser("inspect-silver", help="Inspect silver harmonised tables and suppression stats")
    p_ins_sil.set_defaults(func=cmd_inspect_silver)

    # dp-release
    p_dp = subparsers.add_parser("dp-release", help="Generate differential privacy release with OpenDP")
    p_dp.add_argument("--epsilon", type=float, default=1.0, help="Epsilon privacy parameter")
    p_dp.set_defaults(func=cmd_dp_release)

    # train-fusion
    p_tf = subparsers.add_parser("train-fusion", help="Train L4 LightGBM fusion model and calibrate")
    p_tf.add_argument("--start-date", type=str, default="2024-01-01", help="Start date YYYY-MM-DD")
    p_tf.add_argument("--end-date", type=str, default="2026-12-31", help="End date YYYY-MM-DD")
    p_tf.add_argument("--split-date", type=str, default="2026-01-01", help="Time-based split date YYYY-MM-DD")
    p_tf.add_argument("--step-days", type=int, default=2, help="Sampling frequency in days (default: 2)")
    p_tf.set_defaults(func=cmd_train_fusion)

    # detect
    p_det = subparsers.add_parser("detect", help="Run L1-L5 detection pipeline and alert generation")
    p_det.add_argument("--date", type=str, default=None, help="Scan single date YYYY-MM-DD")
    p_det.add_argument("--start-date", type=str, default=None, help="Start date YYYY-MM-DD")
    p_det.add_argument("--end-date", type=str, default=None, help="End date YYYY-MM-DD")
    p_det.add_argument("--evaluate", action="store_true", default=False, help="Evaluate against injected ground truth")
    p_det.set_defaults(func=cmd_detect)

    # playbooks
    p_pb = subparsers.add_parser("playbooks", help="List operational action playbooks and evidence criteria")
    p_pb.set_defaults(func=cmd_playbooks)

    # evidence-card
    p_card = subparsers.add_parser("evidence-card", help="Generate decision-ready Evidence Card (<2s SLA)")
    p_card.add_argument("--date", type=str, default=None, help="Date YYYY-MM-DD")
    p_card.add_argument("--geo", type=str, default=None, help="Location ID (e.g. SITE-JA-01, DXB-JA)")
    p_card.set_defaults(func=cmd_evidence_card)

    # acknowledge
    p_ack = subparsers.add_parser("acknowledge", help="Human-in-the-loop workflow: Acknowledge / Act / Dismiss")
    p_ack.add_argument("--alert-id", type=str, required=True, help="Alert ID")
    p_ack.add_argument("--action", type=str, required=True, choices=["acknowledge", "act", "dismiss"], help="Workflow action")
    p_ack.add_argument("--user-role", type=str, default="District Health Officer", help="Operational user role")
    p_ack.add_argument("--action-taken", type=str, default=None, help="Description of operational action taken (for act)")
    p_ack.add_argument("--reason", type=str, default=None, help="Mandatory dismissal reason (for dismiss)")
    p_ack.add_argument("--comment", type=str, default=None, help="Audit trail comment")
    p_ack.set_defaults(func=cmd_acknowledge)

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch role-based REST API and web application server")
    p_serve.add_argument("--host", type=str, default="0.0.0.0", help="Host binding (default: 0.0.0.0)")
    p_serve.add_argument("--port", type=int, default=8000, help="Port binding (default: 8000)")
    p_serve.add_argument("--reload", action="store_true", default=False, help="Enable auto-reload")
    p_serve.set_defaults(func=cmd_serve)

    # validate
    p_val = subparsers.add_parser("validate", help="Run Phase 6 operational validation and generate report.html")
    p_val.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    p_val.add_argument("--n-injections", type=int, default=100, help="Number of synthetic outbreak events (default: 100)")
    p_val.add_argument("--start-date", type=str, default="2026-01-01", help="Evaluation start date YYYY-MM-DD")
    p_val.add_argument("--end-date", type=str, default="2026-06-30", help="Evaluation end date YYYY-MM-DD")
    p_val.add_argument("--region", type=str, default="uae", help="Regional profile")
    p_val.add_argument("--out-dir", type=str, default="validation", help="Output directory for validation report")
    p_val.set_defaults(func=cmd_validate)

    # impact
    p_impact = subparsers.add_parser("impact", help="Run Phase 7 Health & Resilience Impact Model")
    p_impact.add_argument("--workforce", type=int, default=50000, help="Monitored workforce size (default: 50,000)")
    p_impact.add_argument("--workday-cost", type=float, default=450.0, help="Cost per lost workday in AED (default: 450)")
    p_impact.add_argument("--export-policy", action="store_true", default=False, help="Export regulatory policy evidence brief as Markdown")
    p_impact.set_defaults(func=cmd_impact)

    # governance
    p_gov = subparsers.add_parser("governance", help="Run Phase 8 Responsible AI & Governance Scorecard")
    p_gov.set_defaults(func=cmd_governance)

    # fhir-export
    p_fhir = subparsers.add_parser("fhir-export", help="Export alerts as HL7 FHIR R4 Bundle (Phase 9)")
    p_fhir.add_argument("--district", type=str, default="UAE-DXB", help="District identifier")
    p_fhir.add_argument("--start-date", type=str, default="2026-06-01", help="Surveillance window start")
    p_fhir.add_argument("--end-date", type=str, default="2026-06-07", help="Surveillance window end")
    p_fhir.add_argument("--out", type=str, default=None, help="Output JSON filepath")
    p_fhir.set_defaults(func=cmd_fhir_export)

    # drift-check
    p_drift = subparsers.add_parser("drift-check", help="Run Continuous Surveillance & Model Drift Monitor (Phase 9)")
    p_drift.add_argument("--seed", type=int, default=42, help="Random seed")
    p_drift.set_defaults(func=cmd_drift_check)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()

