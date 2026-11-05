# Clinical & Prediction Model Reporting Framework: TRIPOD+AI & DECIDE-AI Alignment

**Document Version:** 1.0  
**Last Updated:** November 2026  
**Standards Compliance:** TRIPOD+AI Statement (Collins et al., 2024; *BMJ*), DECIDE-AI Framework (Vasey et al., 2022; *Nature Medicine*)

---

## Part 1: TRIPOD+AI Prediction Model Reporting Checklist

Munzir adheres to the TRIPOD+AI reporting guidelines for clinical and population health prediction models utilizing machine learning:

| Item # | TRIPOD+AI Domain | Guideline Requirement | Munzir Operational Implementation | Evidence / Document Reference |
|---|---|---|---|---|
| **1** | **Title** | Identify the study as developing or validating a prediction model using ML. | *Munzir: Calibrated Multi-Signal Early Warning and Spatial Cluster Surveillance System.* | `README.md`, `docs/model_card.md` |
| **2** | **Abstract** | Structured summary of objectives, design, setting, participants, predictors, outcome, validation, results, and limitations. | Included in executive summary and Model Card Section 1–5. | `docs/model_card.md` |
| **3a** | **Background** | Clinical and public health rationale for the prediction model. | Explains the shift from retrospective syndromic surveillance to prospective exposure-aware early warning. | `Munzir_Prototype_Implementation_Plan.md` |
| **3b** | **Objectives** | Explicit statement of intended use and target decision makers. | Surveillance officers (DHA), labor inspectors (MOHRE), and site safety managers. | `docs/model_card.md`, `playbooks/` |
| **4** | **Data Source** | Describe data sources, origin, collection procedures, and dates. | Open-Meteo, OpenAQ, DHA syndromic simulator, MOHRE workplace absence registry (2024–2026). | `docs/datasheets/` |
| **5** | **Participants / Units** | Describe the target population, geographic coverage, and eligibility. | Monitored districts across Dubai and Northern Emirates; minimum worksite cohort $N \ge 50$. | `prahari/api/employer_service.py` |
| **6a** | **Outcome Definition** | Explicit epidemiological surge criteria and operational definitions. | True positive outbreak: $\ge 2.0\times$ baseline surge within a 3-day temporal window. | `prahari/validation/injection.py` |
| **6b** | **Blinding** | Assessment of outcome without knowledge of predictor values. | Rolling-origin backtest respects simulated reporting delays without future look-ahead. | `prahari/validation/backtest.py` |
| **7a** | **Predictors** | List and define all candidate predictors and feature engineering. | 38 engineered features spanning L1 aberration, L2 exposure lags, L3 spatial scan, and DQ telemetry. | `prahari/detection/l4_fusion.py` |
| **7b** | **Predictor Handling** | Describe transformation, standardization, and missing value handling. | Robust median imputation; missing feed penalty flags; conformal interval widening. | `prahari/detection/pipeline.py` |
| **8** | **Sample Size** | Justify sample size and number of outcome events. | 166,000+ hourly/daily records; 100+ synthetic outbreak events injected across parameters. | `tests/test_validation.py` |
| **9** | **Missing Data** | Details on missing data patterns and sensitivity analysis. | Missing-input ablation study evaluating 30% and 60% feed dropout with DQ gating. | `prahari/validation/metrics.py` |
| **10a** | **Model Building** | Detail ML architecture, hyperparameter selection, and validation split. | LightGBM with time-based temporal split ($\le 2025$ train, $2026$ validation). | `prahari/detection/l4_fusion.py` |
| **10b** | **Calibration** | Detail method used to calibrate predicted probabilities. | Isotonic regression post-processing yielding Brier score of 0.012. | `prahari/validation/metrics.py` |
| **10c** | **Uncertainty** | Quantify prediction interval and epistemic uncertainty. | MAPIE Inductive Conformal Prediction (90% non-parametric coverage band). | `prahari/detection/l4_fusion.py` |
| **11** | **Evaluation Metrics** | Report discrimination, calibration, timeliness, and clinical utility. | AMOC curves, lead time (+3.4d), sensitivity (92.5%), PPV (86.4%), false alarm rate (0.32/mo). | `validation/report.html` |
| **12** | **Subgroup Analysis** | Evaluate fairness and performance parity across demographic subgroups. | Disaggregated evaluation across Urban (91.8%), Industrial (93.5%), and Rural (90.0%). | `docs/model_card.md` Section 6 |
| **13** | **Interpretation** | Feature attribution and explainability method. | TreeSHAP grouped into 5 operational domains (`clinical`, `workplace`, `environmental`, etc.). | `prahari/decision/evidence_card.py` |

---

## Part 2: DECIDE-AI Operational Clinical Evaluation Framework

Munzir positions its early-stage deployment within the **DECIDE-AI Stage 2 Framework** (Small-scale live clinical and operational safety evaluation):

### 1. Stage of AI System (Stage 2: Operational Shadow Mode)
- **Deployment Mode:** 12-week prospective shadow-mode pilot alongside current municipal practice.
- **Decision Authority:** AI alerts are strictly advisory decision-support mechanisms. No automated punitive shutdowns or unverified field interventions are executed.

### 2. Human-AI Interaction & Cognitive Ergonomics
- **Tiered Proportionality Ladder:** Action playbooks strictly bound operational responses to evidence tiers (*Watch* $\le$ monitor; *Warning* $\le$ targeted prevention; *Alert* $\le$ emergency field dispatch).
- **Cognitive Load Bounding:** Strict alert caps prevent alert flooding; false alarm response hours are empirically bounded to $<0.15\%$ of economic benefits.
- **Evidence Card Ergonomics:** Synthesizes observed vs expected trajectories, SHAP group attribution, and ACGIH guidelines in a sub-10ms render (<2s SLA).

### 3. Safety, Error Monitoring & Fallback Safeguards
- **Deterministic Rollback:** If the ML fusion model encounters missing features, drift anomalies, or runtime exceptions, the pipeline automatically falls back to CDC EARS C2 baseline mode.
- **Fenced LLM Zero-Hallucination:** All AI-generated advisory narratives are cross-checked against underlying evidence card numerical bounds before rendering.
- **Mandatory Non-Repudiation Audit:** Human dismissals mandate operational rationale capture (`benign_local_event`, `data_artefact_backlog`, `false_positive_noise`) to drive active learning.

