# PRAHARI (Munzir) — Population & Workforce Health Early Warning Platform

> **Calibrated, explainable, privacy-preserving early warning system that tells public health and occupational safety officers *what is rising, where, why, how sure we are, and what proportionate action to take*.**

---

## Architecture Overview

```
                               ┌──────────────────────────────────────────────────────────┐
                               │                    1. INGESTION (Phase 1)                │
  Open-Meteo Weather ─────────►│  • open_meteo.py (Hourly weather + CAMS AQ)              │
  Open-Meteo Air Quality ─────►│  • openaq.py (OpenAQ v3 ground sensor stations)          │
  Synthetic Syndromic Feeds ──►│  • wbgt.py (Outdoor heat stress index derivation)        │
  Workplace Absence/Incidents─►│  • simulator/ (Negative binomial baseline + exposures)   │
                               │  • nlp/ (PII redaction + OSHA incident classification)   │
                               │  • data_quality.py (Completeness, latency, staleness)    │
                               │    ▼                                                     │
                               │  Bronze Lakehouse Parquet Storage (Partitioned by date)  │
                               └─────────────────────────────┬────────────────────────────┘
                                                             ▼
                               ┌──────────────────────────────────────────────────────────┐
                               │             2. PRIVACY & HARMONISATION (Phase 2)         │
                               │  • spatial.py (H3 Res 6/7 Indexing & Fallback Hierarchy) │
                               │  • suppression.py (CMS k<=10 + Complementary Masking)    │
                               │  • differential_privacy.py (OpenDP Calibrated Laplace)   │
                               │  • workplace.py (Minimum group N>=50 + Rates only)       │
                               │    ▼                                                     │
                               │  Silver Lakehouse Storage (silver.signal_observation)    │
                               └─────────────────────────────┬────────────────────────────┘
                                                             ▼
                               ┌──────────────────────────────────────────────────────────┐
                               │               3. LAYERED DETECTION (L1-L5) (Phase 3)     │
                               │  • L1 Aberration (CDC EARS C1-C3 / Farrington-flexible)  │
                               │  • L2 Exposure-Adjusted Baselines (WBGT / PM2.5 lags)    │
                               │  • L3 Space-Time Permutation Cluster Scan (Kulldorff)    │
                               │  • L4 Calibrated Fusion Model (LightGBM + SHAP)          │
                               │  • L5 Anti-Fatigue Alert Policy (Multi-signal, DQ gates) │
                               └─────────────────────────────┬────────────────────────────┘
                                                             ▼
                               ┌──────────────────────────────────────────────────────────┐
                               │               4. DECISION SUPPORT & GOVERNANCE           │
                               │  • Action Playbook Engine (YAML with RACI roles)         │
                               │  • Evidence Cards & Fenced LLM / Template Narratives     │
                               └──────────────────────────────────────────────────────────┘
```

---

## Implementation Status

### Phase 1 — Data Ingestion & Synthetic Signal Generation: COMPLETE
- [x] **11 Materially Different Feeds:** `wbgt_max`, `wbgt_hours_danger`, `wbgt_hours_caution`, `pm25`, `pm10`, `openaq_pm25`, `clinical_resp`, `clinical_gi`, `clinical_fever`, `clinical_heat`, `lab_pos`, `absence_heat`.
- [x] **WBGT Heat-Stress Engine:** Standard Liljegren / Bernard / Stull physics formulation ($0.7 T_{nw} + 0.2 T_g + 0.1 T_a$) tracking hours $>28^\circ\text{C}$, $>30^\circ\text{C}$, $>32^\circ\text{C}$.
- [x] **Synthetic Health & Workplace Simulator (`simulator/`):** Negative-binomial baseline counts, lagged exposure-response linkages, 3 flagship outbreak scenarios injected + benign decoys.
- [x] **PII Anonymization & Incident Classifier (`nlp/`):** PII scrubber masking names, IDs, phones, emails, and addresses. TF-IDF + Logistic Regression classifier achieving **85.6% 5-fold CV F1 score**.
- [x] **Data Quality Scoring (`data_quality.py`):** Completeness, source latency, staleness, and backlog dump identification.
- [x] **Bronze Parquet Lakehouse Storage:** 166,961+ rows persisted in partition store.

### Phase 2 — Privacy-Preserving Harmonisation Layer: COMPLETE
- [x] **H3 Hexagonal Spatial Indexing (`spatial.py`):** Uber H3 resolution 7 (~5.16 km²) and resolution 6 (~36.1 km²) spatial mapping.
- [x] **Geolocation Fallback Hierarchy:**
  - Exact coordinates $\to$ `site` + `h3_res7` (`location_confidence='exact'`)
  - Address / District only $\to$ `district` centroid (`location_confidence='district_only'`)
  - Unknown $\to$ `state` bucket (`location_confidence='inferred'`, excluded from cluster scan, included in totals)
- [x] **Small-Cell Suppression ($k \le 10$):** CMS-compliant suppression of counts $1 \le count \le 10$ in all external views.
- [x] **Complementary Suppression:** Prevents algebraic recovery of suppressed cells by subtracting from marginal totals.
- [x] **Differential Privacy Engine (`differential_privacy.py`):** Calibrated Laplace mechanism via OpenDP with per-query and aggregate epsilon budget tracking ($\epsilon$).
- [x] **Workplace Minimum-Group Policy (`workplace.py`):** Enforces minimum workforce size $N \ge 50$ for site views; presents rates only; forbids sub-site breakdowns (by shift, team, or employee ID); attaches non-disciplinary legal disclaimers.
- [x] **Silver Harmonised Lakehouse Storage (`silver_store.py`):** Standardized `silver.signal_observation` schema with PostGIS and Parquet support.

### Phase 3 — Layered Detection Engine (L1–L5): COMPLETE
- [x] **L1 Aberration Baselines (`l1_aberration.py`):** CDC EARS C1, C2 (2-day guard band), C3 (cumulative excess), and Farrington-flexible quasi-Poisson GLM with harmonic seasonality and Anscombe residual down-weighting.
- [x] **L2 Exposure-Adjusted Baselines (`l2_exposure.py`):** Distributed-lag exposure GLMs separating Total Excess into "Explained by Environment" and "Unexplained Excess" using lagged WBGT and $\text{PM}_{2.5}$.
- [x] **L3 Prospective Space-Time Cluster Scan (`l3_spacetime.py`):** Prospective permutation cluster scan over H3 cells with Monte Carlo empirical p-values.
- [x] **L4 Multi-Signal Machine Learning Fusion (`l4_fusion.py`):** LightGBM classifier with time-based train/validation split ($\le 2025$ train, $2026$ validation), isotonic probability calibration (Brier score 0.0098), conformal prediction intervals ($\pm 0.116$ at 90%), and 5-group SHAP attribution (`clinical`, `workplace`, `environmental`, `spatiotemporal`, `data_quality`).
- [x] **L5 Anti-Alert-Fatigue Policy Engine (`l5_policy.py`):** Severity tiers (`Watch`, `Warning`, `Alert`), multi-signal corroboration rule (single-signal spikes hard-capped at *Watch*), epidemiological validity gate, backlog dump decoy suppression, and deduplicated multi-day incident tracking.
- [x] **Detection Pipeline Orchestrator (`pipeline.py`):** Connects Silver lakehouse to Gold alerts storage (`data/gold/alerts/`).

### Phase 4 — Decision Support, Evidence Cards & Action Playbooks: COMPLETE
- [x] **Declarative Action Playbooks (`playbooks/`):** 7 YAML playbooks citing WHO, OSHA, ACGIH, and CDC standards across thermal hazard, respiratory surge, infectious enteric clusters, and data artefact reporting dumps.
- [x] **RACI Governance Stakeholder Matrix (`raci.py`):** Structured mapping of Responsible leads, Accountable approving authorities, Consulted technical advisors, and Informed agencies.
- [x] **Proportionality Ladder Enforcement (`playbook_engine.py`):** Guarantees actions never exceed evidence tier (*Watch* $\le$ monitor; *Warning* $\le$ targeted preventive; *Alert* $\le$ field response).
- [x] **Structured Evidence Card API (`evidence_card.py`):** Sub-10ms evidence synthesis (<2s SLA) bundling observed vs. expected series, SHAP driver group, environmental forecast, RACI roles, and explicit assumptions.
- [x] **Human-in-the-Loop Acknowledgement Workflow (`acknowledgement.py`):** Non-repudiation audit trail with mandatory dismissal reasons and real-world Positive Predictive Value (PPV) metrics.
- [x] **Fenced LLM Narrative Generator (`narrative.py`):** Factual clinical summaries with deterministic template fallback and strict number-verification gate.

### Phase 5 — Role-Based, Privacy-Preserving Front-End & REST API: COMPLETE
- [x] **Entra ID App Roles & RBAC (`prahari/api/rbac.py`):** 6 roles (`surveillance_officer`, `occupational_health`, `employer_safety`, `regulator`, `public`, `auditor`) with strict endpoint and field filtering.
- [x] **Situation Map Layer Engine (`prahari/api/map_service.py`):** Multi-layer geospatial map with H3 cells, risk tier colors (Normal green, Watch blue, Warning amber, Alert red), location-confidence diagonal hatching (`district_only`), and L3 space-time cluster outlines.
- [x] **Alert Inbox Service (`prahari/api/alert_service.py`):** Filterable inbox table with calibrated probabilities, 90% conformal bands, DQ badges, owner roles, and triage actions.
- [x] **Privacy-Preserving Employer View (`prahari/api/employer_service.py`):** Restricts employers strictly to their authorized sites, enforces rate-only views per 1,000 workers, suppresses small cohorts ($N < 50$), blocks sub-site/gang breakdowns (HTTP 403), blocks clinical micro-surveillance (HTTP 403), and injects mandatory statutory non-disciplinary banner.
- [x] **Data Health Panel (`prahari/api/health_service.py`):** Ingestion freshness, completeness %, and source latency monitoring across all 5 feeds with composite DQ gating.
- [x] **Missing-Data Interactive Demo Control (`prahari/api/demo_service.py`):** Live toggle controls for evaluators/judges simulating feed dropouts, demonstrating live conformal uncertainty band expansion and anti-fatigue alert downgrading.
- [x] **Non-Repudiation Security Audit Trail (`prahari/api/audit.py`):** Immutable view and action logging in Gold Parquet storage (`data/gold/audit/view_audit_log.parquet`).
- [x] **Single Page Application UI (`prahari/api/static/`):** Accessible, color-blind safe, responsive web application served at `http://localhost:8000/`.

---

## Quickstart Commands

```bash
# 1. Run full test suite (69 passing tests across all 5 phases)
make test

# 2. Launch PRAHARI web application and role-based REST API
make serve

# 3. Run Phase 5 API & RBAC privacy boundary tests
make test-api

# 4. Generate decision-ready Evidence Card (<2s SLA)
make evidence-card

# 5. List operational action playbooks and RACI matrix
make playbooks

# 6. Run Phase 4 decision support unit tests
make test-decision

# 7. Run Phase 3 detection verification tests
make test-detection

# 8. Run Phase 2 privacy verification tests
make test-privacy

# 9. Reproduce 3 years of bronze lakehouse data
make backfill

# 10. Execute Bronze -> Silver Harmonisation pipeline
make harmonise
```

---

## Regional Profiles Supported

- **Dubai & Northern Emirates, UAE (`--region uae`):** 10 districts (Jebel Ali, Al Quoz, Dubai South, Business Bay, Deira, Bur Dubai, Ras Al Khor, Al Barsha, Muhaisnah, Hatta) and 9 industrial/logistics worksites.
- **Tamil Nadu, India (`--region tamilnadu`):** 8 districts (Chennai, Tiruvallur, Kanchipuram, Chengalpattu, Coimbatore, etc.) and 5 manufacturing worksites.
