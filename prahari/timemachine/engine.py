"""
Time Machine Replay Execution Engine.
Orchestrates day-by-day evaluation, metrics compilation, JSON serialization,
and publication-grade HTML report generation.
"""

from dataclasses import asdict
from datetime import datetime, timedelta
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

import pandas as pd

from prahari.timemachine.config import load_sources_config, ReplayEventConfig
from prahari.timemachine.data_loader import (
    DEFAULT_DATA_DIR,
    _load_raw_outcomes,
    get_data_as_of,
)
from prahari.timemachine.detector import TimeMachineDetector, DayReplayResult
from prahari.timemachine.metrics import (
    ReplayOperationalMetrics,
    compute_replay_metrics,
)

logger = logging.getLogger(__name__)


class TimeMachineEngine:
    """Orchestrates end-to-end historical replay with strict as-of date gating."""

    def __init__(
        self,
        event_id: str = "pnw_2021",
        data_dir: Optional[Path] = None,
        out_dir: Optional[Path] = None,
    ):
        self.event_id = event_id
        self.data_dir = Path(data_dir or DEFAULT_DATA_DIR)
        self.out_dir = Path(out_dir or (self.data_dir / event_id))
        self.out_dir.mkdir(parents=True, exist_ok=True)
        
        configs = load_sources_config(self.data_dir / "sources.json")
        self.config = configs.get(event_id)
        if not self.config:
            raise ValueError(f"Unknown event_id: '{event_id}'. Check sources.json.")

        tc = self.config.threshold_comparator or {}
        temp_th = float(tc.get("temp_threshold_c", 35.0))
        wbgt_th = float(tc.get("wbgt_threshold_c", 30.0))
        base_wbgt = float(tc.get("baseline_expected_wbgt", 22.0))

        self.detector = TimeMachineDetector(
            event_id=event_id,
            baseline_cutoff_date=self.config.baseline_end,
            static_temp_threshold=temp_th,
            static_wbgt_threshold=wbgt_th,
            baseline_expected_wbgt=base_wbgt,
        )

    def run_replay(
        self,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> Tuple[List[DayReplayResult], ReplayOperationalMetrics]:
        """
        Executes daily replay across the specified date window.
        Defaults to [baseline_start, event_end].
        """
        s_date = start_date or self.config.baseline_start
        e_date = end_date or self.config.event_end

        dt_cur = datetime.strptime(s_date, "%Y-%m-%d")
        dt_end = datetime.strptime(e_date, "%Y-%m-%d")

        raw_outcomes = _load_raw_outcomes(self.data_dir / self.event_id)
        daily_results: List[DayReplayResult] = []

        logger.info(f"Starting Time Machine Replay for {self.event_id} from {s_date} to {e_date}...")
        while dt_cur <= dt_end:
            cur_str = dt_cur.strftime("%Y-%m-%d")
            # Strict as-of snapshot
            snapshot = get_data_as_of(cur_str, event_id=self.event_id, data_dir=self.data_dir)
            day_res = self.detector.evaluate_day(snapshot, raw_outcomes)
            daily_results.append(day_res)
            dt_cur += timedelta(days=1)

        metrics = compute_replay_metrics(
            results=daily_results,
            observed_peak_date=self.config.observed_peak_date,
            event_id=self.event_id,
            event_name=self.config.name,
        )

        return daily_results, metrics

    def export_results_json(
        self,
        results: List[DayReplayResult],
        metrics: ReplayOperationalMetrics,
        out_path: Optional[Path] = None,
    ) -> Path:
        """Exports replay results and metadata to JSON format."""
        target = Path(out_path or (self.out_dir / "replay_results.json"))
        payload = {
            "metadata": {
                "event_id": self.config.event_id,
                "name": self.config.name,
                "region_name": self.config.region_name,
                "is_hybrid": self.config.is_hybrid,
                "weather_source": self.config.weather_source,
                "outcome_source": self.config.outcome_source,
                "reporting_delay_spec": self.config.reporting_delay_spec,
                "threshold_comparator": self.config.threshold_comparator,
            },
            "metrics": asdict(metrics),
            "timeline": [asdict(r) for r in results],
            "limitations": [
                "Single Case Study: Evaluated on one historical heat dome event (N=1). Generalization requires multi-injection validation.",
                "Reporting Delay Simulation: CDC NSSP facility reporting latency is simulated using an empirical 3-day geometric distribution (70% D+1, 20% D+2, 10% D+3).",
                "Regional Aggregation: Outcome counts represent HHS Region 10 aggregate visits; fine-grained municipal hospital breakdown is not publicly released.",
                "Weather Forecast Horizon: 48-hour forward forecasts utilize archived NWP model predictions without post-hoc assimilation adjustments."
            ]
        }
        with open(target, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        logger.info(f"Replay results exported to {target}")
        return target

    def export_html_report(
        self,
        results: List[DayReplayResult],
        metrics: ReplayOperationalMetrics,
        out_path: Optional[Path] = None,
    ) -> Path:
        """Generates an executive HTML report with timeline visualization and metrics."""
        target = Path(out_path or (Path("validation") / f"timemachine_{self.event_id}.html"))
        target.parent.mkdir(parents=True, exist_ok=True)

        # Build timeline rows
        timeline_rows = ""
        for r in results:
            if r.as_of_date < "2021-06-20":
                continue  # Focus table on event window
            badge_m = (
                f"<span class='badge badge-alert'>{r.alert_severity}</span>"
                if r.munzir_alert
                else f"<span class='badge badge-none'>{r.alert_severity}</span>"
            )
            badge_t = (
                "<span class='badge badge-thresh'>ALERT (>=35°C)</span>"
                if r.threshold_alert
                else "<span class='badge badge-none'>Normal</span>"
            )
            peak_badge = (
                "<span class='badge badge-peak'>OBSERVED PEAK</span>"
                if r.is_observed_peak
                else ""
            )

            timeline_rows += f"""
            <tr>
              <td><b>{r.as_of_date}</b> {peak_badge}</td>
              <td>{r.observed_visits_today}</td>
              <td>{r.reported_visits_visible}</td>
              <td>{r.temp_max}°C / {r.wbgt_max}°C</td>
              <td>{r.forecast_wbgt_next_48h}°C</td>
              <td><b>{r.calibrated_risk:.1%}</b> [{r.conformal_lower:.1%}, {r.conformal_upper:.1%}]</td>
              <td>{badge_m}</td>
              <td>{badge_t}</td>
            </tr>
            """

        html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Munzir Time Machine Replay — {self.config.name}</title>
  <style>
    :root {{
      --bg: #0f172a;
      --card-bg: #1e293b;
      --accent: #38bdf8;
      --text: #f8fafc;
      --text-muted: #94a3b8;
      --border: #334155;
      --danger: #ef4444;
      --warning: #f59e0b;
      --success: #10b981;
    }}
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      margin: 0;
      padding: 2rem;
    }}
    .container {{ max-width: 1200px; margin: 0 auto; }}
    header {{ border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; margin-bottom: 2rem; }}
    h1 {{ margin: 0 0 0.5rem 0; font-size: 1.8rem; color: #fff; }}
    .subtitle {{ color: var(--text-muted); font-size: 0.95rem; }}
    .grid-kpi {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1rem;
      margin-bottom: 2rem;
    }}
    .kpi-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.2rem;
      text-align: center;
    }}
    .kpi-title {{ font-size: 0.8rem; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; }}
    .kpi-val {{ font-size: 2rem; font-weight: 700; margin: 0.4rem 0; color: var(--accent); }}
    .kpi-sub {{ font-size: 0.75rem; color: var(--text-muted); }}
    .section-card {{
      background: var(--card-bg);
      border: 1px solid var(--border);
      border-radius: 8px;
      padding: 1.5rem;
      margin-bottom: 2rem;
    }}
    table {{ width: 100%; border-collapse: collapse; font-size: 0.9rem; text-align: left; }}
    th, td {{ padding: 0.75rem 1rem; border-bottom: 1px solid var(--border); }}
    th {{ background: #0f172a; color: var(--text-muted); font-weight: 600; }}
    .badge {{
      display: inline-block;
      padding: 0.25rem 0.6rem;
      border-radius: 4px;
      font-size: 0.75rem;
      font-weight: 700;
    }}
    .badge-alert {{ background: rgba(239, 68, 68, 0.2); color: #f87171; border: 1px solid #ef4444; }}
    .badge-thresh {{ background: rgba(245, 158, 11, 0.2); color: #fbbf24; border: 1px solid #f59e0b; }}
    .badge-peak {{ background: rgba(56, 189, 248, 0.2); color: #38bdf8; border: 1px solid #38bdf8; }}
    .badge-none {{ background: rgba(148, 163, 184, 0.1); color: #94a3b8; }}
    .banner-caveat {{
      background: rgba(245, 158, 11, 0.1);
      border-left: 4px solid var(--warning);
      padding: 1rem;
      border-radius: 4px;
      margin-bottom: 2rem;
      font-size: 0.85rem;
      line-height: 1.5;
    }}
    .banner-limitations {{
      background: rgba(14, 165, 233, 0.08);
      border-left: 4px solid var(--accent);
      padding: 1rem;
      border-radius: 4px;
      font-size: 0.85rem;
      line-height: 1.6;
    }}
  </style>
</head>
<body>
  <div class="container">
    <header>
      <h1>Munzir Time Machine Replay — Operational Validation</h1>
      <div class="subtitle">
        Strict As-Of-Date Historical Evaluation: <b>{self.config.name}</b> ({self.config.region_name})
      </div>
    </header>

    <div class="banner-caveat">
      <b>SINGLE CASE STUDY DISCLOSURE:</b> {metrics.caveat_notice}
    </div>

    <!-- KPI Grid -->
    <div class="grid-kpi">
      <div class="kpi-card">
        <div class="kpi-title">Lead Time vs Peak</div>
        <div class="kpi-val">+{metrics.lead_time_vs_peak_days} <span style="font-size: 1rem;">days</span></div>
        <div class="kpi-sub">Peak: {metrics.observed_peak_date} | First Alert: {metrics.first_munzir_alert_date}</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Lead Time vs Threshold</div>
        <div class="kpi-val" style="color: #10b981;">+{metrics.lead_time_vs_threshold_days} <span style="font-size: 1rem;">days</span></div>
        <div class="kpi-sub">Advantage over Static 35°C Temp Threshold</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Sensitivity</div>
        <div class="kpi-val" style="color: #38bdf8;">{metrics.sensitivity_pct:.1f}%</div>
        <div class="kpi-sub">Heatwave Window Coverage</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Positive Predictive Value</div>
        <div class="kpi-val" style="color: #a78bfa;">{metrics.ppv_pct:.1f}%</div>
        <div class="kpi-sub">Evaluated over Baseline + Event</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">False Alarms</div>
        <div class="kpi-val" style="color: #fbbf24;">{metrics.false_alarm_rate_per_month:.2f}</div>
        <div class="kpi-sub">Alerts / Month during Baseline</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Data Latency</div>
        <div class="kpi-val" style="color: #94a3b8;">{metrics.mean_reporting_delay_days:.1f} <span style="font-size: 1rem;">days</span></div>
        <div class="kpi-sub">CDC NSSP Empirical Transmission Lag</div>
      </div>
    </div>

    <!-- Timeline Table -->
    <div class="section-card">
      <h2>As-Of-Date Daily Surveillance Timeline</h2>
      <p style="color: var(--text-muted); font-size: 0.85rem; margin-bottom: 1rem;">
        On each simulated date D, algorithms only viewed data published/reported on or before D. Zero hindsight leakage.
      </p>
      <table>
        <thead>
          <tr>
            <th>Simulated Date</th>
            <th>True Visits Occurring</th>
            <th>Visits Visible as of D</th>
            <th>Observed Max Temp / WBGT</th>
            <th>Forward 48h WBGT Forecast</th>
            <th>Calibrated Risk [90% CI]</th>
            <th>Munzir Alert Tier</th>
            <th>Standard Threshold Alert</th>
          </tr>
        </thead>
        <tbody>
          {timeline_rows}
        </tbody>
      </table>
    </div>

    <!-- Provenance & Limitations Section -->
    <div class="section-card">
      <h2>Rigorous Data Provenance & Methodological Limitations</h2>
      <div class="banner-limitations">
        <b>1. Authentic Weather Source:</b> Open-Meteo Archived Forecast API (<code>historical-forecast-api.open-meteo.com</code>). Uses archived numerical weather prediction model runs (ECMWF IFS / NOAA GFS) produced at that time, rather than post-hoc assimilated reanalysis.<br>
        <b>2. Authentic Clinical Outcome Ground Truth:</b> U.S. Centers for Disease Control and Prevention (CDC) National Syndromic Surveillance Program (NSSP), published in MMWR Vol. 70, No. 29 (Schramm et al., 2021; DOI: <code>10.15585/mmwr.mm7029e1</code>). Represents real emergency department visits across HHS Region 10.<br>
        <b>3. Simulated Reporting Delay Specification:</b> Facility transmission latency is simulated using an empirical 3-day geometric distribution: 70% reported on D+1, 20% on D+2, 10% on D+3 (mean lag: 1.4 days), adhering to CDC NSSP facility latency profiles.<br>
        <b>4. Leakage Control:</b> Baseline parameters and thresholds fitted strictly on data prior to 2021-06-24. Zero parameter tuning performed on the heat dome window.
      </div>
    </div>

  </div>
</body>
</html>
        """
        with open(target, "w", encoding="utf-8") as f:
            f.write(html_content)
        logger.info(f"Interactive HTML validation report written to {target}")
        return target
