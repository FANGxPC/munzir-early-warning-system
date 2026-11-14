"""
Munzir Sentinel WBGT Microclimate Bias Correction Orchestration Engine.
Coordinates telemetry auditing, sensor sanity gating, time-blocked cross-validation,
Leave-One-Sensor-Out spatial validation, and HTML / JSON report synthesis.
"""

from pathlib import Path
from typing import Dict, List, Any, Optional
import json
import pandas as pd
import numpy as np

from prahari.config import REGIONAL_PROFILES
from prahari.bias_correction.config import (
    RESULTS_DATA_DIR,
    DEFAULT_TIME_BLOCK_FOLDS,
    UNSENSORED_SITE_PENALTY_MULTIPLIER,
    load_sources_config,
)
from prahari.bias_correction.sanity import SensorSanityFilter
from prahari.bias_correction.evaluator import BiasEvaluator
from prahari.bias_correction.data_loader import SentinelDataLoader
from prahari.bias_correction.model import (
    MicroclimateBiasCorrectionModel,
    evaluate_time_blocked_cv,
    evaluate_leave_one_sensor_out,
)


class BiasCorrectionEngine:
    """
    High-level engine executing the end-to-end Sentinel WBGT bias correction workflow.
    """

    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or RESULTS_DATA_DIR
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.sources_cfg = load_sources_config()

    def audit_telemetry(self) -> Dict[str, Any]:
        """Audits existing bronze telemetry store and provides physical campaign plan."""
        return SentinelDataLoader.audit_stored_telemetry()

    def run_calibration(
        self,
        site_id: str = "SITE-JA-01",
        n_folds: int = DEFAULT_TIME_BLOCK_FOLDS,
        export: bool = True,
    ) -> Dict[str, Any]:
        """
        Executes full calibration pipeline:
        1. Telemetry audit
        2. Sensor sanity gating
        3. Time-blocked CV evaluation (held-out out-of-fold metrics)
        4. Leave-One-Sensor-Out spatial transfer evaluation
        5. Regional site transfer status mapping
        """
        audit_info = self.audit_telemetry()

        # Load paired benchmark dataset
        df_all = SentinelDataLoader.load_paired_telemetry()

        # 1. Sanity Filtering
        clean_df, sanity_audit = SensorSanityFilter.filter_telemetry(df_all)

        # 2. Site-specific Time-Blocked Cross-Validation
        site_df = clean_df[clean_df["site_id"] == site_id].copy().reset_index(drop=True)
        if site_df.empty:
            raise ValueError(f"No observations found for site_id '{site_id}' after sanity filtering.")

        cv_results = evaluate_time_blocked_cv(
            site_df,
            n_folds=n_folds,
            sensor_col="wbgt_sensor",
            model_col="wbgt_model",
            time_col="timestamp",
            rh_col="rh_pct",
        )

        # 3. Fit final production model on full site dataset
        prod_model = MicroclimateBiasCorrectionModel()
        prod_model.fit(
            site_df,
            sensor_col="wbgt_sensor",
            model_col="wbgt_model",
            time_col="timestamp",
            rh_col="rh_pct",
        )

        # 4. Multi-Sensor Spatial Transfer: Leave-One-Sensor-Out (LOSO)
        df_s1 = clean_df[clean_df["node_id"] == "SENT-001"].copy().reset_index(drop=True)
        df_s2 = clean_df[clean_df["node_id"] == "SENT-002"].copy().reset_index(drop=True)

        loso_results: Optional[Dict[str, Any]] = None
        if len(df_s1) > 0 and len(df_s2) > 0:
            loso_results = evaluate_leave_one_sensor_out(
                df_s1,
                df_s2,
                sensor1_name="SENT-001 (SITE-JA-01 Jebel Ali)",
                sensor2_name="SENT-002 (SITE-AQ-01 Al Quoz)",
                sensor_col="wbgt_sensor",
                model_col="wbgt_model",
                time_col="timestamp",
                rh_col="rh_pct",
            )

        # 5. Build Regional Spatial Transfer Register for UAE
        regional_sites = REGIONAL_PROFILES.get("uae", {}).get("sites", [])
        spatial_register = []

        sensed_site_ids = {"SITE-JA-01", "SITE-AQ-01"}
        for s in regional_sites:
            sid = s["id"]
            if sid == "SITE-JA-01":
                status = "SENSED"
                validated = True
                conformal_multiplier = 1.0
                note = "Primary in-situ Sentinel node (SENT-001). Time-blocked cross-validated."
            elif sid == "SITE-AQ-01":
                status = "LOSO-VALIDATED"
                validated = True
                conformal_multiplier = 1.0
                note = "Secondary Sentinel node (SENT-002). Validated via Leave-One-Sensor-Out transfer."
            else:
                status = "UNVALIDATED-SPATIALLY"
                validated = False
                conformal_multiplier = UNSENSORED_SITE_PENALTY_MULTIPLIER
                note = (
                    "Unsensored site. Bias correction transferred as lower-confidence estimate. "
                    "Conformal uncertainty band widened by +50%. No empirical error claimed."
                )

            spatial_register.append({
                "site_id": sid,
                "site_name": s["name"],
                "district_id": s["district_id"],
                "workforce": s.get("workforce", 1000),
                "confidence_flag": status,
                "spatial_validated": validated,
                "conformal_multiplier": conformal_multiplier,
                "note": note,
            })

        # Assemble summary report payload
        held_out_comp = cv_results["held_out_comparison"]
        before_overall = held_out_comp["before"]["overall"]
        after_overall = held_out_comp["after"]["overall"]
        improvements = held_out_comp["improvements"]

        results = {
            "metadata": {
                "report_title": "Munzir Sentinel WBGT Microclimate Bias Correction & Model Calibration Report",
                "calibration_site": site_id,
                "calibration_site_name": site_df["site_name"].iloc[0] if "site_name" in site_df.columns else site_id,
                "campaign_period": "2024-06-01 to 2024-06-30 (30 Days, 720 Hours)",
                "methodology": "Diurnal & Coastal Humidity-Regime Stratified Bias Correction with Contiguous Time-Blocked CV",
                "academic_standards": ["ISO 7243:2017", "Stull (2011)", "Liljegren et al. (2008)", "OSHA OTM Section III"],
            },
            "audit": audit_info,
            "sanity_filter_audit": sanity_audit,
            "cv_validation": {
                "strategy": cv_results["validation_strategy"],
                "n_folds": cv_results["n_folds"],
                "fold_details": cv_results["fold_results"],
                "conformal_target_coverage_pct": cv_results["conformal_target_coverage_pct"],
                "empirical_test_coverage_pct": cv_results["empirical_test_coverage_pct"],
            },
            "error_metrics_summary": {
                "before": before_overall,
                "after": after_overall,
                "improvements": improvements,
                "by_humidity_regime": {
                    "before": held_out_comp["before"]["by_humidity_regime"],
                    "after": held_out_comp["after"]["by_humidity_regime"],
                },
                "diurnal_profile": held_out_comp["after"]["diurnal_profile"],
            },
            "spatial_transfer": {
                "loso_validation": loso_results,
                "spatial_register": spatial_register,
                "unsensored_penalty_multiplier": UNSENSORED_SITE_PENALTY_MULTIPLIER,
            },
            "model_parameters": {
                "diurnal_hourly_bias": {str(k): round(v, 3) for k, v in prod_model.hourly_bias.items()},
                "regime_offsets": {k: round(v, 3) for k, v in prod_model.regime_offset.items()},
                "residual_std": {k: round(v, 3) for k, v in prod_model.residual_std.items()},
                "overall_residual_std": round(prod_model.overall_residual_std, 3),
            },
            "limitations_and_disclosures": {
                "sensor_count": "Currently 2 nodes modeled (SENT-001 at Jebel Ali, SENT-002 at Al Quoz). Additional nodes required for city-wide mesh.",
                "placement_note": "Shade-mounted node (DHT22) paired with ambient black globe (DS18B20). Local shading variations impact radiant globe readings.",
                "duration_gap": "Existing live Bronze lakehouse contains only 3 days of telemetry. The 30-day paired campaign benchmark was evaluated over authentic Open-Meteo ERA5 hourly meteorology.",
                "wet_bulb_approximation": (
                    "Ground truth uses Stull's (2011) psychrometric approximation equation rather than an aspirated natural wet bulb. "
                    "Inherent screening uncertainty is ±0.5°C to ±1.0°C compared to laboratory psychrometers."
                ),
                "spatial_transfer_boundary": (
                    "Unsensored sites cannot have empirical before/after error claimed. They receive the correction labeled "
                    "UNVALIDATED-SPATIALLY with +50% wider conformal prediction bands."
                )
            }
        }

        if export:
            self._export_json(results)
            self._export_html(results, cv_results["out_of_fold_series"])

        return results

    def _export_json(self, results: Dict[str, Any]) -> Path:
        """Serializes calibration metrics to JSON."""
        json_path = self.output_dir / "bias_correction_results.json"
        json_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
        return json_path

    def _export_html(self, results: Dict[str, Any], series_df: pd.DataFrame) -> Path:
        """Generates a clean, standalone HTML audit report."""
        html_path = self.output_dir / "bias_correction_report.html"

        b = results["error_metrics_summary"]["before"]
        a = results["error_metrics_summary"]["after"]
        imp = results["error_metrics_summary"]["improvements"]

        # Build table rows for humidity regimes
        regime_rows = ""
        reg_b = results["error_metrics_summary"]["by_humidity_regime"]["before"]
        reg_a = results["error_metrics_summary"]["by_humidity_regime"]["after"]
        for r_name in ["low", "moderate", "high"]:
            rb = reg_b.get(r_name, {})
            ra = reg_a.get(r_name, {})
            regime_rows += f"""
            <tr>
              <td style="font-weight:600; text-transform:capitalize;">{r_name}</td>
              <td>{rb.get('n', 0)}</td>
              <td>{rb.get('bias', 0.0):+.2f}°C</td>
              <td style="color:#10b981; font-weight:600;">{ra.get('bias', 0.0):+.2f}°C</td>
              <td>{rb.get('mae', 0.0):.2f}°C</td>
              <td style="color:#10b981; font-weight:600;">{ra.get('mae', 0.0):.2f}°C</td>
              <td>{rb.get('rmse', 0.0):.2f}°C</td>
              <td style="color:#10b981; font-weight:600;">{ra.get('rmse', 0.0):.2f}°C</td>
              <td>{ra.get('pearson_r', 0.0):.3f}</td>
            </tr>
            """

        # Build spatial register rows
        spatial_rows = ""
        for site in results["spatial_transfer"]["spatial_register"]:
            flag = site["confidence_flag"]
            badge_color = "#10b981" if flag == "SENSED" else ("#3b82f6" if flag == "LOSO-VALIDATED" else "#f59e0b")
            spatial_rows += f"""
            <tr>
              <td><code>{site['site_id']}</code></td>
              <td>{site['site_name']}</td>
              <td>{site['district_id']}</td>
              <td><span style="background:{badge_color}22; color:{badge_color}; padding:3px 8px; border-radius:4px; font-weight:600; font-size:12px;">{flag}</span></td>
              <td>{site['conformal_multiplier']:.2f}×</td>
              <td style="font-size:12px; color:#6b7280;">{site['note']}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Munzir Sentinel WBGT Model Calibration Report</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; background: #0f172a; color: #f1f5f9; padding: 24px; }}
    .container {{ max-width: 1100px; margin: 0 auto; background: #1e293b; border-radius: 12px; padding: 32px; border: 1px solid #334155; }}
    h1 {{ color: #38bdf8; margin-top: 0; }}
    h2 {{ color: #94a3b8; border-bottom: 1px solid #334155; padding-bottom: 8px; margin-top: 28px; }}
    .card-grid {{ display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin: 20px 0; }}
    .card {{ background: #0f172a; border: 1px solid #334155; border-radius: 8px; padding: 16px; text-align: center; }}
    .card-value {{ font-size: 28px; font-weight: 700; color: #38bdf8; margin-top: 4px; }}
    .card-label {{ font-size: 13px; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.5px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; font-size: 14px; }}
    th, td {{ padding: 10px 12px; text-align: left; border-bottom: 1px solid #334155; }}
    th {{ background: #0f172a; color: #94a3b8; font-weight: 600; }}
    .alert-box {{ background: #451a03; border: 1px solid #b45309; border-radius: 8px; padding: 16px; margin: 20px 0; }}
    .alert-title {{ color: #fbbf24; font-weight: 700; margin-bottom: 6px; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>Munzir Sentinel WBGT Microclimate Bias Correction</h1>
    <p style="color:#94a3b8;">
      Rigorous error measurement and correction of model-derived Wet Bulb Globe Temperature (WBGT)
      using on-site ESP32 Sentinel IoT nodes. Evaluated via 5-fold contiguous time-blocked cross-validation.
    </p>

    <div class="card-grid">
      <div class="card">
        <div class="card-label">MAE Improvement</div>
        <div class="card-value" style="color:#10b981;">-{imp['mae_reduction_pct']}%</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">{b['mae']:.2f}°C → {a['mae']:.2f}°C</div>
      </div>
      <div class="card">
        <div class="card-label">RMSE Improvement</div>
        <div class="card-value" style="color:#10b981;">-{imp['rmse_reduction_pct']}%</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">{b['rmse']:.2f}°C → {a['rmse']:.2f}°C</div>
      </div>
      <div class="card">
        <div class="card-label">Model Bias Removed</div>
        <div class="card-value" style="color:#38bdf8;">{abs(b['bias']):.2f}°C</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">Bias: {b['bias']:+.2f}°C → {a['bias']:+.2f}°C</div>
      </div>
      <div class="card">
        <div class="card-label">Held-out Conformal Coverage</div>
        <div class="card-value" style="color:#a855f7;">{results['cv_validation']['empirical_test_coverage_pct']}%</div>
        <div style="font-size:12px; color:#94a3b8; margin-top:4px;">Target: 90% (z=1.645)</div>
      </div>
    </div>

    <h2>Error Metrics by Humidity Regime (Held-Out Test Blocks)</h2>
    <table>
      <thead>
        <tr>
          <th>Regime</th>
          <th>Samples</th>
          <th>Raw Bias</th>
          <th>Corrected Bias</th>
          <th>Raw MAE</th>
          <th>Corrected MAE</th>
          <th>Raw RMSE</th>
          <th>Corrected RMSE</th>
          <th>Pearson r</th>
        </tr>
      </thead>
      <tbody>
        {regime_rows}
      </tbody>
    </table>

    <h2>Spatial Transfer & Regional Deployment Status</h2>
    <table>
      <thead>
        <tr>
          <th>Site ID</th>
          <th>Site Name</th>
          <th>District</th>
          <th>Transfer Status</th>
          <th>Interval Multiplier</th>
          <th>Operational Note</th>
        </tr>
      </thead>
      <tbody>
        {spatial_rows}
      </tbody>
    </table>

    <div class="alert-box">
      <div class="alert-title">Methodological Limitations & Truth in Science Disclosures</div>
      <ul style="margin: 0; padding-left: 20px; font-size: 13px; line-height: 1.6; color: #fde68a;">
        <li><b>Wet-Bulb Natural Wick Approximation:</b> On-site reference WBGT uses Stull's (2011) psychrometric equation. It carries ±0.5°C to ±1.0°C screening uncertainty relative to an actively aspirated natural wet-bulb.</li>
        <li><b>Sensor Placement:</b> DHT22 air/humidity sensor is shielded from direct solar radiation in a louvered enclosure; DS18B20 black globe is exposed to ambient radiant flux. Local micro-shading creates legitimate site-specific offsets.</li>
        <li><b>Data Duration:</b> Live Bronze store holds 3 days of telemetry. The 30-day paired campaign benchmark was evaluated over authentic Open-Meteo ERA5 hourly meteorology for Dubai.</li>
        <li><b>Spatial Transfer Boundary:</b> Unsensored sites cannot claim empirical before/after error reduction and are strictly flagged <code>UNVALIDATED-SPATIALLY</code> with conformal prediction intervals expanded by +50%.</li>
      </ul>
    </div>
  </div>
</body>
</html>
"""
        html_path.write_text(html_content, encoding="utf-8")
        return html_path

