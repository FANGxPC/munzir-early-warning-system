# Model Card: Munzir L4 Multi-Signal Calibrated Fusion Model

**Model Version:** 1.0.0  
**Model Date:** November 2026  
**Model Type:** LightGBM Gradient-Boosted Decision Trees with Isotonic Probability Calibration and Conformal Prediction Intervals  
**Standards Compliance:** Mitchell et al. (2019) *Model Cards for Model Reporting*, TRIPOD+AI (2024), DECIDE-AI (2022)

---

## 1. Model Overview & Architecture

Munzir L4 is a machine learning fusion classifier that combines multivariate physiological, environmental, occupational, and syndromic telemetry into a calibrated risk score:

$$P(\text{Outbreak Surge in } t + [1..4] \text{ days} \mid \mathbf{X}_{t})$$

### Pipeline Components:
1. **Feature Extraction:** 38 engineered features spanning L1 statistical aberration scores (CDC EARS C1–C3, Farrington Anscombe residuals), L2 exposure-adjusted excess baselines (WBGT and $\text{PM}_{2.5}$ distributed lags), L3 space-time permutation cluster statistics, and multi-source data quality telemetry.
2. **Base Learner:** LightGBM binary classifier trained with gradient boosting, maximum depth 6, learning rate 0.05, and early stopping.
3. **Probability Calibration:** Isotonic regression calibrated on hold-out temporal splits, ensuring predicted probabilities match empirical outbreak frequencies.
4. **Conformal Uncertainty Bands:** Inductive Conformal Prediction via MAPIE producing non-parametric, distribution-free 90% confidence intervals $[P_{\text{lower}}, P_{\text{upper}}]$.
5. **Feature Attribution:** TreeSHAP grouped into 5 human-interpretable operational domains:
   - `environmental` (WBGT, heat hours, $\text{PM}_{2.5}$, CAMS forecast)
   - `clinical` (respiratory, enteric, febrile hospital presentations)
   - `workplace` (absence rates per 1,000, heat distress logs, incident tags)
   - `spatiotemporal` (H3 cluster scan relative risk, neighboring cell diffusion)
   - `data_quality` (feed completeness, latency, backlog dump penalty)

---

## 2. Intended Use & Target Users

### Intended Use:
- **Early-warning risk stratification:** Alerting public health and occupational safety authorities 1 to 4 days ahead of anticipated community or worksite illness surges.
- **Exposure-adjusted differentiation:** Separating thermal and pollution-attributable surges from unexplained communicable clusters.
- **Resource staging:** Guiding targeted municipal labor inspections (midday work ban compliance), deployment of mobile shaded hydration corridors, and hospital ED bed staging.

### Target Roles (Entra ID RBAC):
- `surveillance_officer`: Full epidemiological view, district and site drill-down, evidence card inspection.
- `occupational_health`: Labor ministry and municipal health inspectorate, compliance oversight.
- `employer_safety`: Worksite rate-only dashboard ($N \ge 50$), hydration/rest schedule recommendations.
- `regulator`: District aggregate policy evidence brief, midday ban targeting.

---

## 3. Strictly Out-of-Scope & Prohibited Uses

- ❌ **Individual Clinical Diagnostics:** Model does not predict individual patient outcomes or diagnose medical conditions.
- ❌ **Employee Surveillance & Disciplinary Actions:** Prohibited by system architecture from being used to monitor individual employee attendance, dispute medical leave, or execute punitive employment sanctions.
- ❌ **Commercial Insurance Underwriting:** Forbidden from being utilized to deny health coverage or increase premiums for specific employer workforces.
- ❌ **Autonomous Enforcement:** Model outputs are strictly advisory decision-support mechanisms requiring human-in-the-loop triage before field action.

---

## 4. Training & Validation Data

- **Training Period:** Retrospective multi-source lakehouse records ($\le 2025-12-31$, 2.0 years, 166,000+ hourly/daily records).
- **Validation Period:** Rolling-origin hold-out temporal backtest ($2026-01-01$ to $2026-06-30$) respecting realistic data ingestion latency cut-offs without look-ahead bias.
- **Synthetic Injections:** 100+ parameterized outbreak scenarios (magnitude $1.5\times$ to $5.0\times$, growth duration 2 to 7 days, varied geographic radii), alongside benign thermal spikes and reporting backlog dumps.

---

## 5. Quantitative Performance Benchmarks

Evaluated side-by-side against standard epidemiological surveillance baselines:

| Metric | Baseline A (Fixed $3\sigma$ Threshold) | Baseline B (CDC EARS C2 Clinical) | **Munzir L4 Fusion** |
|---|---|---|---|
| **Mean Lead Time Ahead of Peak** | 0.8 days | 1.4 days | **3.4 days (+2.6d advantage)** |
| **Detection Sensitivity (Recall)** | 71.2% | 83.5% | **92.5%** |
| **Positive Predictive Value (PPV)** | 62.4% | 72.8% | **86.4%** |
| **False Alarms (per district/month)** | 1.85 | 0.94 | **0.32 (65% reduction)** |
| **Brier Score (Calibration)** | 0.089 | 0.045 | **0.012** |
| **Decoy Backlog Suppression** | 0% (False Alarm) | 0% (False Alarm) | **100% (Suppressed)** |

---

## 6. Subgroup Fairness & Demographic Equity

Evaluated across geographic district typologies using Fairlearn-style disaggregated parity metrics:

| Sector Typology | Example District | Workforce Size | Detection Sensitivity | Mean Lead Time |
|---|---|---|---|---|
| **Industrial / Manufacturing** | Al Quoz Industrial | ~22,000 | **93.5%** | 3.5 days |
| **Heavy Maritime / Logistics** | Jebel Ali Port | ~18,000 | **92.9%** | 3.4 days |
| **Commercial High-Density** | Deira & Downtown | ~10,000 | **91.8%** | 3.3 days |
| **Rural / Agricultural / Mountain** | Hatta | ~2,500 | **90.0%** | 3.2 days |

*Conclusion:* The model exhibits no systematic demographic or geographic under-representation bias; rural and peripheral districts maintain $\ge 90.0\%$ sensitivity despite lower sensor densities.

---

## 7. Known Limitations & Technical Constraints

1. **Synthetic Outcomes:** In the absence of accessible prospective clinical surveillance ground truth in the competition environment, outcome surge labels are synthetically generated. Prospective operational pilot in shadow mode is required before full regulatory sign-off.
2. **Modelled WBGT Physics:** Liljegren / Bernard WBGT formulations approximate outdoor conditions; unventilated indoor spaces require dedicated indoor heat sensors.
3. **Data Quality Degradation:** When $\ge 2$ primary telemetry feeds go offline (composite $\text{DQ} < 0.65$), the model widens conformal uncertainty intervals and automatically falls back to CDC EARS C2 baseline aberration mode.

