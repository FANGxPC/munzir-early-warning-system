# Munzir (منذر) — Complete Project Guide & Architectural Explainer

> **Platform Name:** Munzir (منذر) *(Arabic for "The Warner")*  
> **Original Code Name:** PRAHARI  
> **Domain:** Population & Occupational Health Early-Warning & Climate Resilience  
> **Target Region:** Dubai & Northern Emirates (UAE) + Tamil Nadu (India)  
> **Status:** Production-Ready Prototype (11 Phases Complete, 130/130 Passing Tests, Hardware Integrated)

---

## Table of Contents
1. [The Problem: Why Munzir Exists](#1-the-problem-why-munzir-exists)
2. [What Munzir Does (The Executive Summary)](#2-what-munzir-does-the-executive-summary)
3. [The End-to-End System Architecture](#3-the-end-to-end-system-architecture)
4. [How the Hardware Works: Munzir Sentinel (Phase 11)](#4-how-the-hardware-works-munzir-sentinel-phase-11)
5. [The 5-Layer Detection Stack (L1 to L5)](#5-the-5-layer-detection-stack-l1-to-l5)
6. [Decision Support, Playbooks & RACI Matrix](#6-decision-support-playbooks--raci-matrix)
7. [Privacy by Architecture & Responsible AI](#7-privacy-by-architecture--responsible-ai)
8. [The Health & Economic Impact Model](#8-the-health--economic-impact-model)
9. [Enterprise Interoperability (HL7 FHIR & PSI Drift)](#9-enterprise-interoperability-hl7-fhir--psi-drift)
10. [Walkthrough: The Life of a Data Point](#10-walkthrough-the-life-of-a-data-point)
11. [How to Run, Test, and Demonstrate the Platform](#11-how-to-run-test-and-demonstrate-the-platform)
12. [Judge Defense & Frequently Asked Questions (FAQ)](#12-judge-defense--frequently-asked-questions-faq)

---

## 1. The Problem: Why Munzir Exists

Across the Gulf Cooperation Council (GCC) and extreme-heat regions, over **6.5 million outdoor industrial workers** (in construction, maritime ports, logistics, oil & gas, and agriculture) face summer wet-bulb globe temperatures exceeding dangerous thresholds ($>32^\circ\text{C}$).

Today, occupational safety and public health authorities operate in **three disconnected data silos**:

```
┌─────────────────────────────────┐   ┌─────────────────────────────────┐   ┌─────────────────────────────────┐
│     Silo 1: Environmental       │   │    Silo 2: Clinical Registries  │   │  Silo 3: Workplace Safety Logs  │
│  Weather & Air Quality portals   │   │  Hospital ED & clinic visits    │   │  Site sickness absence & first  │
│  Coarse satellite models (10km) │   │  Locked in hospital EHRs with   │   │  aid logs recorded on paper or  │
│  Blind to local asphalt/steel    │   │  7 to 14 days reporting delay   │   │  monthly spreadsheets           │
└────────────────┬────────────────┘   └────────────────┬────────────────┘   └────────────────┬────────────────┘
                 │                                     │                                     │
                 └───────────────────────────────┬─────┴─────────────────────────────────────┘
                                                 ▼
                             THE FATAL FLAW: RETROSPECTIVE DETECTION
                             By the time a heat-stroke cluster is noticed
                             in hospital statistics, workers are in the ICU
                             and productive shifts have already halted.
```

### The Core Solution
**Munzir (منذر)** bridges these silos. It fuses live physical microclimate hardware, regional meteorological forecasts, clinical syndromic trends, and workplace absence signals into a calibrated, explainable, privacy-preserving early-warning engine.

It answers five critical questions for a designated public safety officer:
1. **What is rising?** *(e.g., heat-exhaustion absence, respiratory emergency visits)*
2. **Where is it rising?** *(H3 hexagonal cell resolution ~5.16 km² or specific industrial worksite)*
3. **Why is it rising?** *(Separates expected heatwave/pollution effects from unexplained pathogen outbreaks using SHAP feature attribution)*
4. **How sure are we?** *(Calibrated probability with 90% conformal prediction interval and data quality gating)*
5. **What proportionate action to take?** *(Legally grounded RACI playbooks citing UAE MOHRE Midday Ban regulations)*

---

## 2. What Munzir Does (The Executive Summary)

* **Operational Lead Time:** Delivers **3.4 days advance warning** before peak clinical presentations.
* **Alert Fatigue Defense:** Reduces false alarms by **76%** compared to traditional threshold alerts (achieving only **0.31 false alarms per site/month**).
* **Decoy Filtering:** Automatically detects and filters reporting backlog dumps (bulk hospital uploads) as data artefacts without triggering panic.
* **Measurable Financial ROI:** Saves **3,480+ lost workdays** and avoids **25 severe ICU heat-stroke hospitalizations** per summer season across 50,000 workers, yielding an **AED 1,861,996 net economic benefit** and a **758:1 Benefit-to-Cost Ratio (BCR)**.
* **Physical Hardware Integration:** Deploys **Munzir Sentinel**, an ultra-low-cost ESP32 shade node measuring localized wet-bulb globe temperature (WBGT) and driving multi-pattern on-board LED alert feedback right at the worksite.
* **Zero Cloud Cost:** Fully containerized on Azure Container Apps with `minReplicas: 0` (scale-to-zero), consuming **$0.00/month** when idle.

---

## 3. The End-to-End System Architecture

Munzir follows the modern cloud-native **Medallion Lakehouse Architecture** (Bronze $\to$ Silver $\to$ Gold):

```
                                  ┌────────────────────────────────────────────────────────┐
                                  │                  1. DATA INGESTION                     │
  Open-Meteo Weather (Hourly) ───►│  • open_meteo.py (Temperature, humidity, solar, wind)  │
  Open-Meteo Air Quality (CAMS)──►│  • openaq.py (OpenAQ v3 ground sensor monitor feeds)   │
  ESP32 Sentinel Hardware Nodes──►│  • sentinel_ingest.py (Microclimate on-site WBGT)      │
  Workplace Absence & Incidents──►│  • sftp_csv.py (Zero-PII employer batch drop)          │
  Synthetic Syndromic Feeds ─────►│  • simulator/ (Negative binomial baseline + exposures) │
                                  │  • nlp/ (PII scrubber + OSHA incident text classifier) │
                                  │  • data_quality.py (Completeness, latency, staleness)  │
                                  │    ▼                                                   │
                                  │  Bronze Parquet Storage (data/bronze/)                 │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │        2. PRIVACY & HARMONISATION LAYER                │
                                  │  • spatial.py (Uber H3 Res-6 & Res-7 spatial indexing) │
                                  │  • Geolocation Fallback Hierarchy:                     │
                                  │      GPS (≤50m) -> Inferred (≤1000m) -> District Centroid
                                  │  • suppression.py (CMS-standard k ≤ 10 suppression)    │
                                  │  • differential_privacy.py (OpenDP Laplace noise)      │
                                  │  • workplace.py (N ≥ 50 minimum group size, rates only)│
                                  │    ▼                                                   │
                                  │  Silver Lakehouse Storage (silver.signal_observation)  │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │          3. 5-LAYER DETECTION ENGINE                   │
                                  │  • L1 Aberration (CDC EARS C1-C3 + Farrington GLM)     │
                                  │  • L2 Exposure Baselines (WBGT & PM2.5 lag models)     │
                                  │  • L3 Space-Time Permutation Cluster Scan (Kulldorff)  │
                                  │  • L4 Multi-Signal Fusion (LightGBM + Conformal + SHAP)│
                                  │  • L5 Anti-Fatigue Policy (Corroboration, DQ Gates)    │
                                  │    ▼                                                   │
                                  │  Gold Alerts Lakehouse (data/gold/alerts/)             │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │         4. DECISION SUPPORT & GOVERNANCE               │
                                  │  • playbooks/ (7 YAML action playbooks grounded in law)│
                                  │  • raci.py (Multi-agency stakeholder assignment)       │
                                  │  • evidence_card.py (Sub-2s SLA evidence synthesis)    │
                                  │  • acknowledgement.py (Human-in-the-loop audit trail)  │
                                  │  • narrative.py (Fenced LLM with zero-hallucination)   │
                                  │  • fhir_adapter.py (HL7 FHIR R4 MeasureReport/Risk)    │
                                  │  • drift_monitor.py (Population Stability Index PSI)   │
                                  └───────────────────────────┬────────────────────────────┘
                                                              │
                                                              ▼
                                  ┌────────────────────────────────────────────────────────┐
                                  │              5. PRESENTATION & INTERACTION             │
                                  │  • Responsive Single Page Web Application              │
                                  │  • Role-Based REST API (6 Entra ID roles)              │
                                  │  • On-Site ESP32 Multi-Pattern LED Visual Alert States │
                                  └────────────────────────────────────────────────────────┘
```

---

## 4. How the Hardware Works: Munzir Sentinel (Phase 11)

### 4.1 Physical Construction
The **Munzir Sentinel** is a shade-mounted device built for simplicity, low cost, and field reliability:
* **Microcontroller:** ESP32 DevKit (2.4 GHz Wi-Fi).
* **Sensors:**
  * **DHT22 (GPIO 4):** Measures dry-bulb air temperature ($T_a$) and relative humidity ($RH$).
  * **DS18B20 (GPIO 18):** Waterproof digital temperature probe inserted into the center of a matte-black ping-pong ball (40mm), functioning as a **black-globe thermometer** ($T_g$) to measure radiant solar and surface heat.
* **Visual Indicator (GPIO 25, 26, 27):** Common-cathode RGB LED with 220Ω series resistors.
* **Operator Button (GPIO 0):** Uses the built-in tactile **BOOT button** on the ESP32.

```
       [Sunlight & Radiant Heat]
                  │
                  ▼
         (●) Matte-Black Ping-Pong Ball ──► DS18B20 Probe (GPIO 18)
                  │
         [~] Sun-Shielded Cup ───────────► DHT22 Temp/Humidity (GPIO 4)
                  │
                  ▼
         ┌───────────────────┐
         │   ESP32 DevKit    ├──► RGB LED (Green/Yellow/Orange/Red/Blue)
         │  (WiFi Telemetry) ├──► Physical BOOT Button (Operator Ack)
         └─────────┬─────────┘
                   │
                   ▼ (HTTP POST every 60s)
         Munzir Cloud / Local Server
```

### 4.2 The Software–Hardware Communication Loop

```mermaid
sequenceDiagram
    autonumber
    actor Officer as Safety Officer (Browser)
    participant Cloud as Munzir Server (FastAPI)
    participant Node as ESP32 Sentinel Node
    actor Worker as Field Worker / Operator

    Note over Officer, Cloud: One-Time Commissioning Step
    Officer->>Cloud: POST /api/v1/sentinel/commission (lat, lon, site_id, accuracy)
    Cloud-->>Officer: 200 OK (Binds node, derives H3 Res-7 cell, confidence flag)

    loop Every 60 Seconds
        Node->>Node: Read DHT22 & DS18B20 sensors
        Node->>Node: Estimate WBGT via Stull formula
        Node->>Cloud: POST /api/v1/sentinel/upload (node_id, seq, temps, rh)
        Note over Cloud: Central Server re-derives WBGT,<br/>evaluates bounds & checks site alert tier
        Cloud-->>Node: 200 OK {"level": "Warning", "valid_until": "11:06:00Z"}
        Node->>Node: Drives RGB LED -> Double Orange Blink (Warning)
    end

    opt Physical Operator Acknowledgment
        Worker->>Node: Presses physical BOOT button
        Node->>Cloud: POST /api/v1/sentinel/ack {"node_id": "SENT-001"}
        Cloud-->>Node: 200 OK (Logged to audit trail as on-site acknowledgement)
        Node->>Worker: LED flashes Cyan confirmation
    end

    opt Network Disconnection / Wi-Fi Dropout
        Node->>Node: 3 consecutive upload timeouts
        Node->>Node: Switches to Fail-Safe Mode: Blue Blip pattern
        Cloud->>Cloud: Heartbeat > 180s timeout -> Flags node offline & widens uncertainty
    end
```

### 4.3 Why Server-Side Re-Derivation Matters
The ESP32 sends raw dry-bulb temperature, relative humidity, and globe temperature. The central Munzir server **does not trust the microcontroller's math**. The server independently recalculates natural wet-bulb temperature ($T_w$) and WBGT using Stull's (2011) micrometeorological formulation:

$$T_w = T_a \cdot \arctan\left(0.151977 \sqrt{RH + 8.313659}\right) + \arctan\left(T_a + RH\right) - \arctan\left(RH - 1.676331\right) + 0.00391838 \cdot RH^{1.5} \cdot \arctan\left(0.023101 \cdot RH\right) - 4.686035$$

$$\text{WBGT}_{\text{onsite}} = 0.7 \cdot T_w + 0.2 \cdot T_g + 0.1 \cdot T_a$$

### 4.4 The Microclimate Delta (The Hardware Differentiator)
Coarse atmospheric models (like Open-Meteo or ERA5) have a grid resolution of 10–25 km. They calculate heat assuming open grass or desert sand. But in an industrial steel yard or port terminal, asphalt and structural steel radiate intense heat.
* **Modelled WBGT (Open-Meteo):** $30.2^\circ\text{C}$ (*Normal/Watch boundary*)
* **Measured On-Site WBGT (Sentinel):** $33.4^\circ\text{C}$ (*Severe Warning/Alert!*)
* **Microclimate Delta:** $+3.2^\circ\text{C}$ excess heat that satellite models completely miss.

### 4.5 LED Visual Feedback Code
* **Solid Green:** Baseline Nominal ($<28^\circ\text{C}$).
* **Slow Yellow Blink (1 Hz):** Active Watch ($28^\circ\text{C} - 30^\circ\text{C}$) — hydrate and buddy check.
* **Double Orange Blink (2 Hz):** Preventive Warning ($30^\circ\text{C} - 32^\circ\text{C}$) — 15m mandatory rest/hour.
* **Fast Red Blink (4 Hz):** Hazard Alert ($>32^\circ\text{C}$) — stop heavy work, move to shade.
* **Blue Blip (100ms flash every 2s):** Offline / Fail-Safe Mode (lost connection to server).
* **Magenta Blink:** Sensor Hardware Fault.

---

## 5. The 5-Layer Detection Stack (L1 to L5)

Most early-warning platforms use a single black-box model. Munzir uses a **5-layer epidemiological defense stack**:

```
[Incoming Telemetry Stream: Weather, Air Quality, Sentinel Hardware, Clinical Visits, Absence]
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 1: Per-Signal Aberration Detection (Epidemiological Baselines)                  │
│ • CDC EARS C1, C2 (2-day guard band), and C3 (cumulative excess) for short histories   │
│ • Farrington-Flexible quasi-Poisson GLM with seasonality and Anscombe down-weighting   │
│ • Output: Exceedance ratio (observed / expected) and p-value per signal               │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 2: Exposure-Adjusted Baselines (Distinguishing Explained from Unexplained)       │
│ • Fits distributed-lag non-linear models (DLNM) linking WBGT and PM2.5 to symptoms    │
│ • Splits total excess into:                                                            │
│     1. "Explained by Environment" (e.g. expected heat exhaustion during 45°C peak)    │
│     2. "Unexplained Residual" (e.g. gastrointestinal spike with normal weather)        │
│ • Ground-truth priority: Uses on-site Sentinel WBGT if online, falls back to weather   │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 3: Space-Time Permutation Cluster Scan                                           │
│ • Prospective Kulldorff permutation cylinder scan across H3 hexagonal grid cells       │
│ • Monte Carlo empirical p-values (999 permutations) to identify spatial clusters       │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 4: Multi-Signal Machine Learning Fusion                                          │
│ • LightGBM binary classifier trained with strict time-based splits (prevents leakage)  │
│ • Isotonic probability calibration (Brier score: 0.012)                                │
│ • Conformal prediction intervals (MAPIE) showing calibrated 90% uncertainty bands      │
│ • TreeSHAP feature attribution: groups drivers into Clinical, Workplace, Weather, DQ  │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│ Layer 5: Anti-Alert-Fatigue Policy Engine                                              │
│ • Multi-Signal Corroboration Rule: Single-signal spikes can NEVER exceed "Watch"       │
│ • Severity Tiers: Watch -> Warning -> Alert                                            │
│ • Data Quality Gating: If feed completeness drops, expands confidence band, caps tier  │
│ • Backlog Decoy Suppression: Filters bulk reporting drops as artefacts                 │
└───────────────────────────────────┬────────────────────────────────────────────────────┘
                                    │
                                    ▼
                       [Published Gold Alert Record]
```

---

## 6. Decision Support, Playbooks & RACI Matrix

An alert without an action is noise. Munzir converts every alert into a structured, decision-ready **Evidence Card** in under 2 seconds.

### 6.1 Declarative Action Playbooks
The system stores 7 declarative YAML playbooks grounded in:
* **UAE MOHRE Ministerial Resolution No. 44 of 2022** (Midday Work Ban)
* **OSHA Heat Illness Prevention Guidelines**
* **WHO Public Health Surveillance Guidance**

### 6.2 The RACI Matrix
Every alert type and severity level has an assigned stakeholder matrix:
* **R (Responsible):** Who executes the physical intervention (e.g. *Site Safety Officer* sets 15-minute hydration rotations).
* **A (Accountable):** Who has formal legal sign-off (e.g. *District Health Officer* or *MOHRE Inspector*).
* **C (Consulted):** Technical advisors (e.g. *Lead Epidemiologist*, *Occupational Hygienist*).
* **I (Informed):** Agencies notified via dashboard or FHIR message (e.g. *Ambulance Services*, *National Emergency Authority*).

### 6.3 Proportionality Ladder
Actions are mathematically constrained never to exceed the evidence tier:
* **Watch Tier:** Informational monitoring, feed verification, buddy checks.
* **Warning Tier:** Targeted preventive measures (hydration stations, shift rescheduling, shade breaks).
* **Alert Tier:** Formal field investigation, rapid response team deployment, work stoppage.

### 6.4 Fenced LLM Narrative Generator
Munzir includes an optional LLM narrative assistant that translates alert JSON into clinical briefings. To prevent AI hallucinations:
1. The LLM only receives structured alert JSON.
2. An automated **regular-expression number verification gate** inspects the LLM's response.
3. If the LLM generates any statistic, date, or percentage that does not exist in the source JSON, the text is **immediately discarded**, and the system falls back to a deterministic, vetted template.

---

## 7. Privacy by Architecture & Responsible AI

Munzir is built from the ground up to comply with **UAE Federal Decree-Law No. 45 of 2021 on Personal Data Protection (PDPL)** and **GDPR**.

1. **Zero PII at Ingestion:** All names, national IDs, Emirates IDs, employee badges, phone numbers, and home addresses are scrubbed or rejected at edge ingestion.
2. **Small-Cell Suppression ($k \le 10$):** Any cell count between 1 and 10 is masked as `<10` to prevent micro-targeting or identity triangulation.
3. **Complementary Suppression:** Prevents calculating suppressed cells by subtracting from marginal row/column totals.
4. **Differential Privacy:** Public and inter-agency releases apply calibrated Laplace noise using the **OpenDP** library with tracked privacy budgets ($\epsilon = 1.0$).
5. **Workplace Anti-Surveillance Safeguards:**
   * Minimum group size $N \ge 50$ workers.
   * Employers view **rates per 1,000 workers only**, never counts.
   * Sub-site, team-level, and worker-level breakdowns return **HTTP 403 Forbidden**.
   * Employer access to clinical diagnostic feeds returns **HTTP 403 Forbidden**.
   * Mandatory statutory banner on every employer screen: *"Aggregate data — not for individual employment or disciplinary decisions."*
6. **Automatic CDC EARS C2 Fallback:** If machine learning models experience calibration drift or runtime failure, the platform automatically drops into deterministic, fail-safe CDC EARS C2 mode.

---

## 8. The Health & Economic Impact Model

To demonstrate real-world value, Phase 7 includes an interactive resilience calculator grounded in published epidemiological literature (UAE MOHRE, ILO 2019, OSHA/NIOSH, and Dubai Health Authority DRG hospital inpatient tariffs):

### Baseline Cohort: 50,000 Outdoor Construction & Industrial Workers
* **Lead Time Advantage:** $+3.4$ days earlier than retrospective ED arrivals.
* **Lost Workdays Averted:** **3,480+ productive workdays** saved per season through timely hydration and shift staggering.
* **Severe Hyperthermia / ICU Admissions Avoided:** **25 critical cases** avoided.
* **Gross Economic Benefit:** **AED 1,864,450** per season.
* **False Alarm Triage Overhead:** **AED 2,454** ($<0.15\%$ of gross savings).
* **Net Economic Value Delivered:** **AED 1,861,996**.
* **Benefit-to-Cost Ratio (BCR):** **758:1** (Every AED 1 spent on safety response yields AED 758 in averted downtime and hospital costs).

---

## 9. Enterprise Interoperability (HL7 FHIR & PSI Drift)

### 9.1 HL7 FHIR R4 Integration
Munzir natively exports surveillance observations and alerts into international **HL7 FHIR Release 4** resources for immediate integration with regional health information exchanges:
* **DHA NABIDH** (Dubai)
* **Malaffi** (Abu Dhabi)
* **CDC NSSP & WHO EIOS**
* Resources generated: `RiskAssessment`, `MeasureReport`, and `Bundle`.
* CLI command: `make fhir-export` $\to$ exports `fhir_surveillance_bundle.json`.

### 9.2 Continuous Surveillance Drift Monitoring
To ensure models remain accurate over changing climate seasons, Munzir tracks the **Population Stability Index (PSI)** on all incoming features:
$$\text{PSI} = \sum_{i=1}^k \left(\text{Actual}_i - \text{Expected}_i\right) \times \ln\left(\frac{\text{Actual}_i}{\text{Expected}_i}\right)$$
* $\text{PSI} < 0.10$: Model stable (Nominal operation).
* $0.10 \le \text{PSI} < 0.25$: Moderate covariate shift (triggers calibration warning).
* $\text{PSI} \ge 0.25$: Significant climate drift (triggers automated EARS baseline fallback).
* CLI command: `make drift-check`.

---

## 10. Walkthrough: The Life of a Data Point

Here is what happens from the moment a sensor detects heat to the moment an action is taken:

1. **At the Worksite (09:30:00 UTC):**
   * The shade-mounted ESP32 Sentinel node reads DHT22 (Air Temp: $36.2^\circ\text{C}$, RH: $58\%$) and black-globe probe ($44.0^\circ\text{C}$).
   * The node packages the reading into a JSON payload and transmits it via Wi-Fi to `POST /api/v1/sentinel/upload`.
2. **At Ingestion & Validation (09:30:01 UTC):**
   * Munzir verifies node commissioning and confirms the reading is within physical bounds.
   * Central server re-derives WBGT ($32.4^\circ\text{C}$) using Stull's equation.
   * Generates four `SignalObservation` rows and writes them into Bronze Parquet partitions.
   * Returns `{"level": "Warning", "valid_until": "09:36:00Z"}` to the ESP32.
3. **On-Board the Device (09:30:02 UTC):**
   * The ESP32 parses the response and updates the on-board RGB LED to a **double orange blink** (*Warning*), visually alerting workers and the site supervisor.
4. **In the Detection Engine (09:30:05 UTC):**
   * Layer 2 detects that on-site WBGT exceeds $32^\circ\text{C}$, corroborating a $28\%$ rise in morning sickness absence.
   * Layer 3 detects spatial clustering across the H3 cell covering Jebel Ali.
   * Layer 4 fusion computes an **83.3% calibrated outbreak probability** ($90\%$ conformal CI: $72\% - 94\%$).
   * Layer 5 confirms multi-signal corroboration and publishes a `Warning` alert.
5. **On the Dashboard (09:30:06 UTC):**
   * The District Surveillance Officer and Site Safety Officer see the Jebel Ali cell turn amber on the Situation Map.
   * Opening the Evidence Card displays the WBGT spike, the SHAP attribution breakdown, and the RACI Action Playbook.
6. **Field Intervention (09:31:00 UTC):**
   * The Site Safety Officer enacts the playbook: mandatory 15-minute shaded rest rotations per hour and cold electrolyte replenishment.
   * The officer acknowledges the alert in the web portal, while the on-site operator presses the physical BOOT button on the ESP32 to confirm field action.

---

## 11. How to Run, Test, and Demonstrate the Platform

### 11.1 Quickstart Commands

```bash
# 1. Run all 130 unit and integration tests (clean, 0 warnings)
make test

# 2. Run Responsible AI & Governance Scorecard (7/7 passing guardrails)
make governance

# 3. Run Sentinel Hardware tests
make test-sentinel

# 4. Launch the Web Application & REST API
make serve
# Open browser to: http://localhost:8000
```

### 11.2 Key Makefile Targets

| Command | Action |
| :--- | :--- |
| `make test` | Runs the complete 130-test suite across all 11 phases |
| `make serve` | Launches FastAPI server on `http://0.0.0.0:8000` |
| `make governance` | Evaluates Model Cards, Datasheets, DPIA, and runtime safety guardrails |
| `make test-sentinel` | Runs the 14 Sentinel hardware integration tests |
| `make sentinel-replay`| Streams a pre-recorded 30-minute node trace for pitch backup |
| `make validate SEED=42`| Runs 100-injection operational validation and generates `validation/report.html` |
| `make impact` | Computes economic impact metrics and exports Markdown policy brief |
| `make fhir-export` | Exports active alerts as an HL7 FHIR R4 Bundle |
| `make drift-check` | Computes Population Stability Index (PSI) and feature drift |
| `make backfill` | Ingests 3+ years of historical data into Bronze lakehouse |
| `make harmonise` | Harmonises Bronze data into Silver lakehouse with H3 indices |

---

## 12. Judge Defense & Frequently Asked Questions (FAQ)

### Q1: "Why use synthetic health data instead of real hospital patient records?"
**Answer:** Real-world person-level medical records cannot be publicly distributed or shared during a hackathon without violating UAE PDPL and patient privacy. Munzir uses an honest, defensible approach: **real Open-Meteo weather and OpenAQ air-quality history combined with statistically realistic negative-binomial health simulations and physical hardware telemetry**. Our models are validated on hold-out data with zero look-ahead bias.

### Q2: "How do you prevent alert fatigue so safety officers don't ignore warnings?"
**Answer:** Through our Layer 2 exposure models and Layer 5 policy rules:
1. **Exposure Baselines:** Sickness absence always rises in summer; Munzir subtracts the expected heatwave effect and alerts only when excess is unexplained or exceeds safe physical limits.
2. **Multi-Signal Corroboration:** A single spike (e.g. one clinic reporting high cases) is capped at *Watch* and can never trigger a disruptive *Warning* or *Alert* without corroborating signals.
3. **Decoy Suppression:** Bulk clinic uploads are recognized as reporting backlogs and suppressed.
*Result:* We bounded false alarms to **0.31 per month**, a **76% reduction** over baseline systems.

### Q3: "What happens if a hospital or weather API feed drops offline?"
**Answer:** Munzir is fault-tolerant by construction. Our Data Quality gate continuously monitors source latency and completeness. When a feed drops, the system:
1. Expands its conformal prediction uncertainty intervals (e.g. from $\pm 10\%$ to $\pm 25\%$).
2. Hard-caps the maximum alert level at *Warning*.
3. Displays a prominent Data Quality warning badge explaining exactly which input is missing, rather than crashing or hallucinating false alerts.

### Q4: "How does the physical ESP32 Sentinel node get its location without a GPS module?"
**Answer:** The node carries zero GPS hardware and stores zero location coordinates to maintain simplicity and low cost ($< \$15$). During physical setup, the safety officer opens the **Commission Node** dialog in the Munzir web dashboard and clicks *"Use This Device's Location"* to capture the browser's W3C Geolocation API fix. The server binds the node to the worksite and its H3 Res-7 cell once.

### Q5: "How does Munzir prevent employers from using this data to punish workers?"
**Answer:** Privacy is enforced in the software architecture:
* Minimum cohort size $N \ge 50$ workers.
* Rate-only presentation per 1,000 workers; individual case lists do not exist.
* Sub-site breakdowns (by team, shift, or employee ID) return **HTTP 403 Forbidden**.
* Employer access to clinical diagnostic feeds returns **HTTP 403 Forbidden**.
* Every employer screen displays a mandatory statutory disclaimer stating that data cannot be used for employment or disciplinary decisions.

