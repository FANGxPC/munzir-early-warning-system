"""
Detection Pipeline (L1 to L5 Orchestration).
Integrates L1 aberration, L2 exposure adjustment, L3 prospective space-time clustering,
L4 multi-signal machine learning fusion, and L5 anti-alert-fatigue policy.
"""

from dataclasses import asdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple, Set
import json
import logging
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

from prahari.config import GOLD_DIR
from prahari.storage.silver_store import SilverStore
from prahari.storage.bronze_store import BronzeStore
from prahari.detection.l1_aberration import L1AberrationDetector, L1Result
from prahari.detection.l2_exposure import L2ExposureBaselineModel, L2ResidualResult
from prahari.detection.l3_spacetime import ProspectiveSpaceTimeScan, L3ClusterResult
from prahari.detection.l4_fusion import (
    L4FusionModel,
    FusionFeatureExtractor,
    FusionPrediction,
    FEATURE_NAMES,
)
from prahari.detection.l5_policy import L5AlertPolicyEngine, PrahariAlert, AlertSeverity

logger = logging.getLogger(__name__)


class DetectionPipeline:
    """
    End-to-end detection engine orchestrator executing L1 to L5.
    """

    def __init__(
        self,
        silver_store: Optional[SilverStore] = None,
        bronze_store: Optional[BronzeStore] = None,
        fusion_model: Optional[L4FusionModel] = None,
        policy_engine: Optional[L5AlertPolicyEngine] = None,
        gold_alerts_dir: Optional[Path] = None,
    ):
        self.silver_store = silver_store or SilverStore()
        self.bronze_store = bronze_store or BronzeStore()
        self.fusion_model = fusion_model or L4FusionModel()
        self.policy_engine = policy_engine or L5AlertPolicyEngine()
        self.l1_detector = L1AberrationDetector()
        self.l2_model = L2ExposureBaselineModel(min_train_samples=20)
        self.l3_scanner = ProspectiveSpaceTimeScan(
            max_duration_days=7,
            max_k_ring=1,
            n_permutations=49,
            significance_threshold=0.05,
        )

        self.gold_alerts_dir = Path(gold_alerts_dir or (Path(GOLD_DIR) / "alerts"))
        self.gold_alerts_dir.mkdir(parents=True, exist_ok=True)

    def extract_features_for_location_date(
        self,
        obs_date: str,
        geo_id: str,
        history_df: pd.DataFrame,
        l3_clusters: Optional[List[L3ClusterResult]] = None,
    ) -> Dict[str, float]:
        """
        Extracts L1, L2, L3 metrics and environmental context for a single (geo_id, obs_date).
        """
        loc_history = history_df[history_df["geo_id"] == geo_id]
        if loc_history.empty:
            return {k: 0.0 for k in FEATURE_NAMES}

        # 1. L1 Aberration baselines (EARS C2 / Farrington)
        l1_results: Dict[str, float] = {}
        for sig, key in [
            ("clinical_resp", "resp_exceedance"),
            ("clinical_gi", "gi_exceedance"),
            ("clinical_fever", "fever_exceedance"),
            ("absence_heat", "absence_exceedance"),
        ]:
            sig_df = loc_history[loc_history["signal_type"] == sig]
            if len(sig_df) >= 7:
                res = self.l1_detector.process_series(
                    sig_df, current_date_str=obs_date, algorithm="ears_c2"
                )
                l1_results[key] = res.exceedance_score
            else:
                l1_results[key] = 1.0

        # 2. L2 Exposure-adjusted baselines (Resp vs PM2.5, Absence vs WBGT)
        l2_results: Dict[str, float] = {}
        # Prepare merged dataframe for L2 model
        # Get environmental records for this geo_id or district
        wbgt_df = loc_history[loc_history["signal_type"] == "wbgt_max"][["obs_date", "value"]].rename(columns={"value": "wbgt_max"})
        pm25_df = loc_history[loc_history["signal_type"] == "pm25"][["obs_date", "value"]].rename(columns={"value": "pm25"})

        resp_df = loc_history[loc_history["signal_type"] == "clinical_resp"]
        if len(resp_df) >= 20 and not pm25_df.empty and not wbgt_df.empty:
            merged_resp = resp_df.merge(wbgt_df, on="obs_date", how="left").merge(pm25_df, on="obs_date", how="left")
            merged_resp["wbgt_max"] = merged_resp["wbgt_max"].ffill().bfill().fillna(28.0)
            merged_resp["pm25"] = merged_resp["pm25"].ffill().bfill().fillna(35.0)
            if obs_date in merged_resp["obs_date"].values:
                try:
                    res_l2 = self.l2_model.evaluate_date(merged_resp, obs_date, "clinical_resp", geo_id)
                    l2_results["resp_unexplained"] = res_l2.unexplained_excess
                    l2_results["resp_explained_frac"] = res_l2.explained_fraction
                except Exception:
                    pass

        abs_df = loc_history[loc_history["signal_type"] == "absence_heat"]
        if len(abs_df) >= 20 and not wbgt_df.empty:
            merged_abs = abs_df.merge(wbgt_df, on="obs_date", how="left").merge(pm25_df, on="obs_date", how="left")
            merged_abs["wbgt_max"] = merged_abs["wbgt_max"].ffill().bfill().fillna(28.0)
            merged_abs["pm25"] = merged_abs["pm25"].ffill().bfill().fillna(35.0)
            if obs_date in merged_abs["obs_date"].values:
                try:
                    res_l2_heat = self.l2_model.evaluate_date(merged_abs, obs_date, "absence_heat", geo_id)
                    l2_results["heat_unexplained"] = res_l2_heat.unexplained_excess
                except Exception:
                    pass

        # 3. L3 Space-time cluster check
        l3_dict: Dict[str, Any] = {"is_significant": False, "relative_risk": 1.0}
        if l3_clusters:
            for cl in l3_clusters:
                if geo_id in cl.member_geo_ids and cl.is_significant:
                    l3_dict["is_significant"] = True
                    l3_dict["relative_risk"] = max(l3_dict["relative_risk"], cl.relative_risk)

        # 4. Extract standardized feature vector
        return FusionFeatureExtractor.extract_features_for_row(
            geo_id=geo_id,
            obs_date=obs_date,
            obs_df=loc_history,
            l1_results=l1_results,
            l2_results=l2_results,
            l3_results=l3_dict,
        )

    def run_date(
        self,
        obs_date: str,
        history_df: Optional[pd.DataFrame] = None,
        lookback_days: int = 45,
    ) -> List[PrahariAlert]:
        """
        Executes L1 to L5 detection across all locations for a single day.
        """
        if history_df is None:
            curr_dt = datetime.strptime(obs_date, "%Y-%m-%d")
            start_lookback = (curr_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            history_df = self.silver_store.read_observations(
                start_date=start_lookback, end_date=obs_date
            )

        if history_df.empty:
            return []

        # Impute suppressed small cells (CMS guideline k <= 10) with expected small value 5.0
        if "value" in history_df.columns:
            history_df = history_df.copy()
            history_df["value"] = history_df["value"].fillna(5.0)

        day_slice = history_df[history_df["obs_date"] == obs_date]
        if day_slice.empty:
            return []

        unique_geos = day_slice["geo_id"].unique().tolist()

        # Run L3 space-time cluster scanner for candidate signals
        l3_clusters: List[L3ClusterResult] = []
        try:
            for s_type in ["clinical_resp", "absence_heat", "clinical_gi"]:
                cl_list = self.l3_scanner.scan(
                    observations_df=history_df,
                    current_date_str=obs_date,
                    study_window_days=min(30, lookback_days),
                    signal_type=s_type,
                )
                l3_clusters.extend(cl_list)
        except Exception as e:
            logger.warning(f"L3 scan encountered error on {obs_date}: {e}")

        alerts: List[PrahariAlert] = []

        for geo_id in unique_geos:
            # Extract features across L1, L2, L3, environment, DQ
            feats = self.extract_features_for_location_date(
                obs_date=obs_date,
                geo_id=geo_id,
                history_df=history_df,
                l3_clusters=l3_clusters,
            )

            # L4 Fusion Model Inference
            try:
                pred: FusionPrediction = self.fusion_model.predict(feats)
            except Exception as e:
                logger.error(f"L4 inference error for {geo_id} on {obs_date}: {e}")
                continue

            # L5 Anti-Alert-Fatigue Policy Engine
            alert = self.policy_engine.evaluate(
                prediction=pred,
                geo_id=geo_id,
                obs_date=obs_date,
                l3_clusters=l3_clusters,
            )

            if alert.severity != AlertSeverity.NONE:
                alerts.append(alert)

        return alerts

    def run_detection(
        self,
        start_date: str,
        end_date: str,
        lookback_days: int = 45,
        save_alerts: bool = True,
    ) -> List[PrahariAlert]:
        """
        Runs the full detection pipeline across a date range.
        Maintains sliding window for efficient data retrieval.
        """
        start_dt = datetime.strptime(start_date, "%Y-%m-%d")
        end_dt = datetime.strptime(end_date, "%Y-%m-%d")

        # Load bulk data with lookback padding
        earliest_dt = start_dt - timedelta(days=lookback_days)
        earliest_str = earliest_dt.strftime("%Y-%m-%d")

        logger.info(f"Loading silver observations from {earliest_str} to {end_date}...")
        full_history = self.silver_store.read_observations(
            start_date=earliest_str, end_date=end_date
        )
        if not full_history.empty and "value" in full_history.columns:
            full_history = full_history.copy()
            full_history["value"] = full_history["value"].fillna(5.0)
        if not full_history.empty and "value" in full_history.columns:
            full_history = full_history.copy()
            full_history["value"] = full_history["value"].fillna(5.0)

        all_alerts: List[PrahariAlert] = []
        curr_dt = start_dt
        while curr_dt <= end_dt:
            curr_str = curr_dt.strftime("%Y-%m-%d")
            window_start = (curr_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            window_df = full_history[
                (full_history["obs_date"] >= window_start)
                & (full_history["obs_date"] <= curr_str)
            ]

            day_alerts = self.run_date(curr_str, history_df=window_df)
            all_alerts.extend(day_alerts)
            curr_dt += timedelta(days=1)

        if save_alerts and all_alerts:
            self.save_alerts(all_alerts, start_date, end_date)

        return all_alerts

    def save_alerts(
        self,
        alerts: List[PrahariAlert],
        start_date: str,
        end_date: str,
    ) -> Path:
        """
        Saves alerts into gold storage partitioned parquet and JSON summary.
        """
        records = []
        for a in alerts:
            d = asdict(a)
            d["severity"] = a.severity.value
            d["geo_ids_str"] = ",".join(a.geo_ids)
            d["signal_contributions_json"] = json.dumps(a.signal_contributions)
            records.append(d)

        df = pd.DataFrame(records)
        out_parquet = self.gold_alerts_dir / f"alerts_{start_date}_{end_date}.parquet"
        table = pa.Table.from_pandas(df, preserve_index=False)
        pq.write_table(table, out_parquet, compression="snappy")

        # Write latest JSON for rapid UI/API retrieval
        latest_json = self.gold_alerts_dir / "alerts_latest.json"
        with open(latest_json, "w") as f:
            json.dump([asdict(a) for a in alerts], f, default=str, indent=2)

        return out_parquet

    def load_alerts(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[PrahariAlert]:
        """
        Loads persisted alerts from gold storage (JSON or Parquet).
        """
        latest_json = self.gold_alerts_dir / "alerts_latest.json"
        if latest_json.exists():
            try:
                with open(latest_json, "r") as f:
                    data = json.load(f)
                loaded = []
                for item in data:
                    item_copy = dict(item)
                    if isinstance(item_copy.get("severity"), str):
                        item_copy["severity"] = AlertSeverity(item_copy["severity"])
                    # Filter dates if specified
                    obs_d = item_copy.get("obs_date")
                    if start_date and obs_d and obs_d < start_date:
                        continue
                    if end_date and obs_d and obs_d > end_date:
                        continue
                    # Remove extra keys not in PrahariAlert dataclass
                    valid_keys = {
                        "alert_id", "incident_id", "alert_type", "severity",
                        "probability", "ci_low", "ci_high", "geo_ids", "obs_date",
                        "signal_contributions", "dq_status", "owner_role",
                        "recommended_action", "is_suppressed_decoy"
                    }
                    cleaned = {k: v for k, v in item_copy.items() if k in valid_keys}
                    loaded.append(PrahariAlert(**cleaned))
                if loaded:
                    return loaded
            except Exception:
                pass
        return []

    def build_training_dataset(
        self,
        start_date: str = "2024-01-01",
        end_date: str = "2026-12-31",
        step_days: int = 1,
        lookback_days: int = 40,
    ) -> Tuple[pd.DataFrame, pd.Series, pd.Series]:
        """
        Constructs (X_df, y_series, dates_series) for training L4 LightGBM fusion model.
        Labels:
          y = 1 if an active outbreak event (non-decoy) is present at geo_id within [date - 1, date + 3].
          y = 0 otherwise.
        """
        ground_truth_df = self.bronze_store.read_ground_truth()
        if ground_truth_df.empty:
            raise RuntimeError("Ground truth catalog not found! Run 'make backfill' first.")

        earliest_dt = datetime.strptime(start_date, "%Y-%m-%d") - timedelta(days=lookback_days)
        earliest_str = earliest_dt.strftime("%Y-%m-%d")

        full_history = self.silver_store.read_observations(
            start_date=earliest_str, end_date=end_date
        )
        if not full_history.empty and "value" in full_history.columns:
            full_history = full_history.copy()
            full_history["value"] = full_history["value"].fillna(5.0)

        all_dates = sorted(full_history["obs_date"].unique().tolist())
        target_dates = [d for d in all_dates if d >= start_date and d <= end_date][::step_days]

        feature_rows: List[Dict[str, float]] = []
        labels: List[int] = []
        dates: List[str] = []

        # Pre-process ground truth active intervals
        active_intervals = []
        for _, row in ground_truth_df.iterrows():
            if not row.get("is_decoy", False):
                active_intervals.append({
                    "geo_id": row["target_geo_id"],
                    "start": row["start_date"],
                    "peak": row["peak_date"],
                    "end": row["end_date"],
                })

        unique_geos = full_history["geo_id"].unique().tolist()

        for obs_date in target_dates:
            curr_dt = datetime.strptime(obs_date, "%Y-%m-%d")
            window_start = (curr_dt - timedelta(days=lookback_days)).strftime("%Y-%m-%d")
            window_df = full_history[
                (full_history["obs_date"] >= window_start)
                & (full_history["obs_date"] <= obs_date)
            ]

            for geo_id in unique_geos:
                feats = self.extract_features_for_location_date(
                    obs_date=obs_date,
                    geo_id=geo_id,
                    history_df=window_df,
                    l3_clusters=None,
                )

                # Determine label: y=1 if geo_id in active outbreak window
                is_positive = False
                for event in active_intervals:
                    if event["geo_id"] == geo_id:
                        # Positive from 2 days before start through end of outbreak
                        early_start = (datetime.strptime(event["start"], "%Y-%m-%d") - timedelta(days=2)).strftime("%Y-%m-%d")
                        if early_start <= obs_date <= event["end"]:
                            is_positive = True
                            break

                feature_rows.append(feats)
                labels.append(1 if is_positive else 0)
                dates.append(obs_date)

        X_df = pd.DataFrame(feature_rows)[FEATURE_NAMES]
        y_series = pd.Series(labels, name="label")
        dates_series = pd.Series(dates, name="obs_date")

        return X_df, y_series, dates_series

    def train_fusion(
        self,
        start_date: str = "2024-01-01",
        end_date: str = "2026-12-31",
        split_date: str = "2026-01-01",
        step_days: int = 2,
    ) -> Dict[str, Any]:
        """
        Builds dataset, fits LightGBM fusion model, and calibrates via Isotonic Regression.
        """
        logger.info(f"Building fusion training dataset ({start_date} to {end_date}, step={step_days}d)...")
        X_df, y_series, dates_series = self.build_training_dataset(
            start_date=start_date, end_date=end_date, step_days=step_days
        )
        logger.info(f"Dataset generated: {len(X_df)} samples, {y_series.sum()} positive outbreak points.")

        metrics = self.fusion_model.train(
            X_df=X_df,
            y_series=y_series,
            dates_series=dates_series,
            split_date=split_date,
        )
        logger.info(f"Fusion model trained: Brier={metrics['brier_score']}, AUC={metrics['auc_roc']}")
        return metrics

    def evaluate(
        self,
        alerts: List[PrahariAlert],
    ) -> Dict[str, Any]:
        """
        Evaluates detection performance against ground truth events:
        - Lead time per flagship scenario
        - Sensitivity
        - Decoy suppression rate
        """
        gt_df = self.bronze_store.read_ground_truth()
        if gt_df.empty:
            return {"status": "error", "message": "No ground truth catalog"}

        eval_results: Dict[str, Any] = {
            "total_alerts": len(alerts),
            "flagship_scenarios": {},
            "decoys": {},
            "sensitivity": 0.0,
            "decoy_suppression_rate": 0.0,
        }

        alerts_by_geo: Dict[str, List[PrahariAlert]] = {}
        for a in alerts:
            for g in a.geo_ids:
                alerts_by_geo.setdefault(g, []).append(a)

        detected_count = 0
        real_events = gt_df[gt_df["is_decoy"] == False]
        total_real = len(real_events)

        for _, ev in real_events.iterrows():
            ev_id = ev["event_id"]
            geo = ev["target_geo_id"]
            start_d = ev["start_date"]
            peak_d = ev["peak_date"]
            end_d = ev["end_date"]
            sc_type = ev["scenario_type"]

            geo_alerts = alerts_by_geo.get(geo, [])
            # Search for Warning or Alert during event window (or up to 2 days prior)
            early_d = (datetime.strptime(start_d, "%Y-%m-%d") - timedelta(days=2)).strftime("%Y-%m-%d")
            matching_alerts = [
                a for a in geo_alerts
                if early_d <= a.obs_date <= end_d
                and a.severity in [AlertSeverity.WARNING, AlertSeverity.ALERT]
            ]

            if matching_alerts:
                first_alert = min(matching_alerts, key=lambda a: a.obs_date)
                first_dt = datetime.strptime(first_alert.obs_date, "%Y-%m-%d")
                peak_dt = datetime.strptime(peak_d, "%Y-%m-%d")
                lead_time_days = (peak_dt - first_dt).days

                detected_count += 1
                eval_results["flagship_scenarios"][f"{sc_type}_{geo}"] = {
                    "detected": True,
                    "first_alert_date": first_alert.obs_date,
                    "peak_date": peak_d,
                    "lead_time_days": lead_time_days,
                    "severity": first_alert.severity.value,
                    "probability": first_alert.probability,
                }
            else:
                eval_results["flagship_scenarios"][f"{sc_type}_{geo}"] = {
                    "detected": False,
                    "peak_date": peak_d,
                    "lead_time_days": None,
                }

        # Check decoys
        decoy_events = gt_df[gt_df["is_decoy"] == True]
        total_decoys = len(decoy_events)
        suppressed_decoys = 0

        for _, dec in decoy_events.iterrows():
            geo = dec["target_geo_id"]
            start_d = dec["start_date"]
            end_d = dec["end_date"]
            sc_type = dec["scenario_type"]

            geo_alerts = alerts_by_geo.get(geo, [])
            high_alerts = [
                a for a in geo_alerts
                if start_d <= a.obs_date <= end_d
                and a.severity in [AlertSeverity.WARNING, AlertSeverity.ALERT]
            ]

            if not high_alerts:
                suppressed_decoys += 1
                eval_results["decoys"][f"{sc_type}_{geo}"] = {
                    "suppressed_from_warning": True,
                    "max_severity_fired": max([a.severity.value for a in geo_alerts if start_d <= a.obs_date <= end_d], default="none"),
                }
            else:
                eval_results["decoys"][f"{sc_type}_{geo}"] = {
                    "suppressed_from_warning": False,
                    "max_severity_fired": high_alerts[0].severity.value,
                }

        eval_results["sensitivity"] = round(detected_count / max(total_real, 1), 3)
        eval_results["decoy_suppression_rate"] = round(suppressed_decoys / max(total_decoys, 1), 3)

        return eval_results

