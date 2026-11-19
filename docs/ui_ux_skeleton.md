# Munzir (منذر) — Frontend UI/UX Skeleton & Component Architecture Guide

> **Document Purpose:** Complete visual wireframe, DOM skeleton, button placement, navigation hierarchy, and component placement reference for AI agents, developers, and designers working on the Munzir frontend.  
> **Source Files:** [`munzir/api/static/index.html`](../munzir/api/static/index.html), [`munzir/api/static/app.js`](../munzir/api/static/app.js), [`munzir/api/static/styles.css`](../munzir/api/static/styles.css)  
> **Platform Aesthetic:** High-contrast, dark-mode Palantir Foundry / Defense Command Console (`#070c18` background, `#0b1120` cards, `#38bdf8` tactical cyan, strictly 0 emojis).

---

## 1. Global Master Layout Wireframe

```text
+-------------------------------------------------------------------------------------------------------------------------+
| [BRAND] MUNZIR | منذر    [PILLAR SWITCH: 1. Command Hub | 2. Clinical | 3. Operations | 4. AI | 5. Resilience]  [DATE][ROLE][DOSSIER] | (Tier 1: 52px)
+-------------------------------------------------------------------------------------------------------------------------+
| [SUBTABS: Situation Map | Alert Inbox | Renal AKI | Spatial Deconvolve | Municipal Fleet | Jais Voice | Safe-Harbor ...]    | (Tier 2: 36px)
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                         |
|  MAIN ACTIVE VIEW CONTENT AREA (<main id="mainContainer">)                                                              |
|                                                                                                                         |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|  | [HERO KPI RIBBON: WBGT Index (33.4°C) | Active Alerts (3) | Monitored Workforce (142.5k) | Jais-3-0.9B Dual (AI)]  |  |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|                                                                                                                         |
|  +-----------------------------------------------------------------------------+ +-----------------------------------+  |
|  |                                                                             | |                                   |  |
|  |  PRIMARY WORKSPACE CANVAS                                                   | |  CONTEXTUAL SIDEBAR / CONTROL     |  |
|  |  (Tactical SVG Map / Biomarker Trajectory / Deconvolution Ellipse /          | |  (Monitored Sites / Candidates /  |  |
|  |   Smartphone Simulator / Policy Slider Heatmap)                             | |   RACI Assignment Matrix)         |  |
|  |                                                                             | |                                   |  |
|  +-----------------------------------------------------------------------------+ +-----------------------------------+  |
|                                                                                                                         |
+-------------------------------------------------------------------------------------------------------------------------+
| [VERIFIED]  LAKEHOUSE: 60,473 Recs (57.2 MB) | GPU: RTX 2050 CUDA | PRIVACY: ε=0.142 | BCR: 8.11x | TESTS: 258/258 PASS   | (Footer: 26px)
+-------------------------------------------------------------------------------------------------------------------------+
                                                                                          [AI: Sovereign Copilot Pill] ---> [DRAWER]
```

---

## 2. Master Header Hierarchy (Tier 1 & Tier 2)

### Tier 1: Master Executive Header (`<header class="master-header">`, Height: 52px)

```text
+-----------------------------------------------------------------------------------------------------------------------------------+
| [MUNZIR]            [ Command Hub ] [ Clinical Sentinel ] [ Field Operations ] [ Sovereign AI ] [ Policy & Resilience ]   [SIM] [ROLE] [MODELS] |
| منذر • Dubai Health                                                                                               2025-08-20  DHA  DOSSIER|
+-----------------------------------------------------------------------------------------------------------------------------------+
```

#### Element Inventory (Left to Right):
1. **Brand Lockup** (`.brand-lockup`):
   - `.brand-badge`: High-contrast cyan pill displaying text `MUNZIR`.
   - `.brand-title`: Text `منذر • Dubai Health & Biosurveillance`.
   - `.brand-beacon`: Status beacon with pulsing emerald dot (`.beacon-dot`) displaying `OPERATIONAL • GST`.
2. **5 Mission Navigation Pillars** (`<nav id="missionPillars" class="pillar-segmented-switch">`):
   - `<button class="pillar-btn active" data-pillar="command" onclick="switchMissionPillar('command')">Command Hub</button>`
   - `<button class="pillar-btn" data-pillar="clinical" onclick="switchMissionPillar('clinical')">Clinical Sentinel</button>`
   - `<button class="pillar-btn" data-pillar="operations" onclick="switchMissionPillar('operations')">Field Operations</button>`
   - `<button class="pillar-btn" data-pillar="sovereign_ai" onclick="switchMissionPillar('sovereign_ai')">Sovereign AI</button>`
   - `<button class="pillar-btn" data-pillar="resilience" onclick="switchMissionPillar('resilience')">Policy & Resilience</button>`
3. **Header Utility Group** (`.header-utility-group`):
   - **Simulation Date Picker** (`#simDateInput`, `.sim-date-picker`): HTML5 date input (`value="2025-08-20"`). Triggers global state change.
   - **Role Switcher Dropdown** (`#roleSelect`, `.role-select`):
     - `<option value="surveillance_officer">DHA Surveillance Lead</option>`
     - `<option value="occupational_health">MOHRE Health Officer</option>`
     - `<option value="employer_safety">Site Safety Manager</option>`
     - `<option value="regulator">H&S Regulator</option>`
     - `<option value="public">Public Portal (ε=1.0)</option>`
     - `<option value="auditor">Inspector General</option>`
   - **Master Dossier Button** (`#btnOpenSystemDossier`, `.nav-btn-dossier`):
     - Text: `MODELS & DOSSIER`
     - Action: `onclick="openSystemDossierModal()"` (Opens 12-model and architecture inspector).

---

### Tier 2: Contextual Sub-Tab Strip (`<nav id="subtabsBar" class="subtabs-bar">`, Height: 36px)

Subtabs dynamically show or hide depending on which Mission Pillar is selected in Tier 1.

| Pillar (`data-pillar`) | Visible Sub-Tabs (`data-tab`) | Button Text Label | URL Hash |
|---|---|---|---|
| **`command`** | `map`<br>`inbox` | **Situation Map**<br>**Alert Inbox** | `/#map`<br>`/#inbox` |
| **`clinical`** | `phs`<br>`renal`<br>`deconvolve`<br>`compound`<br>`causal`<br>`nabidh` | **Heat Strain & Debt (ISO 7933)**<br>**Renal Biomarkers (AKI)**<br>**Spatial Deconvolution**<br>**Compound Multi-Hazard**<br>**Bayesian Causal De-Mixing**<br>**NABIDH FHIR CDS** | `/#phs`<br>`/#renal`<br>`/#deconvolve`<br>`/#compound`<br>`/#causal`<br>`/#nabidh` |
| **`operations`** | `sentinel`<br>`dispatch`<br>`employer` | **Sentinel Hardware Twin**<br>**Municipal Staging**<br>**Employer Safety View** | `/#sentinel`<br>`/#dispatch`<br>`/#employer` |
| **`sovereign_ai`** | `intercom`<br>`jais`<br>`copilot` | **Two-Way Voice Intercom**<br>**Jais Dispatch Generator**<br>**Sovereign Copilot & Codex** | `/#intercom`<br>`/#jais`<br>`/#copilot` |
| **`resilience`** | `policystudio`<br>`impact`<br>`timemachine`<br>`whatif`<br>`safeharbor`<br>`health`<br>`demo`<br>`audit` | **MOHRE Policy Studio**<br>**Health Impact & Resilience**<br>**Time Machine Replay**<br>**What-If Interventions**<br>**Safe-Harbor Shield**<br>**Data Health Panel**<br>**Missing-Data Validation**<br>**Security Audit Logs** | `/#policystudio`<br>`/#impact`<br>`/#timemachine`<br>`/#whatif`<br>`/#safeharbor`<br>`/#health`<br>`/#demo`<br>`/#audit` |

---

## 3. Detailed Skeleton of Key Views

---

### View 1: Situation Map (`#view-map`, Hash: `/#map`)

* **Primary Purpose:** Live geospatial risk awareness across Dubai's industrial clusters.
* **Layout Structure:** 4-card Tactical KPI ribbon on top, followed by a 2-column map layout (75% SVG canvas, 25% site sidebar).

```text
+-------------------------------------------------------------------------------------------------------------------------+
| [Tactical KPI Ribbon: 4 Cards]                                                                                          |
| +---------------------+ +---------------------+ +---------------------+ +---------------------------------------------+ |
| | AMBIENT THERMAL     | | ACTIVE WORKSITE     | | MONITORED WORKFORCE | | SOVEREIGN AI & PRIVACY                      | |
| | 33.4°C WBGT         | | 3 CRITICAL / 8 WATCH| | 142,500 PERSONS     | | JAIS-3-0.9B DUAL                            | |
| | High Risk • +1.8°C  | | Jebel Ali • Al Quoz | | 60,473 Parquets     | | Inception 42 • Safe-Harbor ε=0.142          | |
| +---------------------+ +---------------------+ +---------------------+ +---------------------------------------------+ |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                         |                                               |
|  TACTICAL RADAR CANVAS (`#situationSvgMap`)                             |  MONITORED JURISDICTIONS SIDEBAR              |
|  - Geographic bounds: Dubai (24.75°N to 25.35°N, 54.95°E to 56.20°E)     |  (`<div id="mapGeoList">`)                    |
|  - Concentric distance range rings: 15 km, 30 km, 45 km                 |                                               |
|  - Uber H3 Res 7 hexagonal grid lines                                   |  Card Stack (`.geo-item-card`):               |
|  - Monitored Worksites (Solid colored circles: Green, Yellow, Orange,   |  - Site Name & District (e.g. SITE-JA-01)     |
|    Red with glowing filter `#nodeGlow`)                                 |  - Risk Tier Badge (`NORMAL`, `WATCH`,        |
|  - Active L3 Clusters (Red dashed radiating rings, relative risk text)  |    `WARNING`, `ALERT`)                        |
|  - Corner reticles & Coordinate grid overlay                            |  - Outbreak Probability (e.g. 83.3%)          |
|                                                                         |  - Workforce Population Count                 |
+-------------------------------------------------------------------------+-----------------------------------------------+
```

* **Key Interactive Elements:**
  - Clicking any KPI Card triggers an inspection modal (`openSystemDossierModal`).
  - Clicking a site card in `#mapGeoList` or node on `#situationSvgMap` executes `selectGeoSite(geoId)`, highlighting the node with a selection ring.

---

### View 2: Decision-Ready Alert Inbox (`#view-inbox`, Hash: `/#inbox`)

* **Primary Purpose:** Triage list of multi-signal corroborated alerts with calibrated probabilities and conformal bounds.
* **Layout Structure:** Full-width header with filter controls above an enterprise data table.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| DECISION-READY ALERT INBOX                                                  [Filter: All Severities] [Acknowledge All]  |
+-------------------------------------------------------------------------------------------------------------------------+
| Alert ID   | Severity | Location / Site  | Prob [90% Conformal CI] | Top SHAP Driver    | RACI Owner  | Actions             |
|------------|----------|------------------|-------------------------|--------------------|-------------|---------------------|
| ALT-JA-01  | [WARNING]| Jebel Ali Port   | 83.3% [72.0% - 91.0%]   | WBGT > 32°C (44%)  | Safety Lead | [Evidence Card] [Ack]
| ALT-AQ-02  | [WATCH]  | Al Quoz Ind. 3   | 42.1% [31.5% - 53.0%]   | PM2.5 Spike (38%)  | MOHRE Lead  | [Evidence Card] [Ack]
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Interactive Buttons:**
  - `[Evidence Card]` (`.btn-primary`): Opens `#evidenceCardModal` displaying the TreeSHAP waterfall, conformal bounds, and statutory citations.
  - `[Ack]` (`.btn-secondary`): Opens `#acknowledgeModal` to log an immutable compliance receipt.

---

### View 3: Occupational Renal Biomarkers (`#view-renal`, Hash: `/#renal`)

* **Primary Purpose:** Phase 14 sub-clinical Acute Kidney Injury (AKI) detection catching strain **+11.5 days early**.
* **Layout Structure:** Top 4-card metric ribbon, interactive SVG dual-axis trajectory curve, cohort demographics table.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| RENAL BIOMARKER SURVEILLANCE (PHASE 14)                                       [SITE SELECTOR: SITE-JA-01 Jebel Ali]     |
| Sub-Clinical AKI Screening via CKD-EPI 2021 Race-Free Formula & KDIGO Staging                                          |
+-------------------------------------------------------------------------------------------------------------------------+
| [MEAN eGFR: 97.7 mL/min] | [DEHYDRATION: 21.7%] | [KDIGO STAGE 1: 216.7/1k] | [LEAD TIME: +11.5 DAYS ADVANCE BADGE]     |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                         |
|  DUAL-AXIS TRAJECTORY SVG CHART (`#renalTrajectorySvgContainer`)                                                        |
|  - Left Y-Axis: Mean eGFR (mL/min/1.73m²) descending curve                                                             |
|  - Right Y-Axis: Dehydration % & KDIGO Stage 1 per 1,000 ascending bars                                                 |
|  - X-Axis: 14-Day Timeline (T-14 to Current Date)                                                                       |
|  - Marker Flag: +11.5 Days Advance Detection vs Hospital Emergency Registries                                          |
|                                                                                                                         |
+-------------------------------------------------------------------------------------------------------------------------+
| COHORT CLINICAL OBSERVATIONS TABLE (`#renalCohortTableBody`)                                                            |
| Worker Cohort | Screened | Baseline Cr | Day 14 Cr | Mean eGFR | KDIGO Stage | Urine Specific Gravity | Status           |
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Buttons & Selectors:**
  - `#renalSiteSelect`: Select between industrial sites (`SITE-JA-01`, `SITE-AQ-01`, `SITE-DS-01`).
  - `#btnRunRenalScreening`: Triggers live recalculation via `/api/v1/renal/screening`.

---

### View 4: Spatio-Temporal Deconvolution (`#view-deconvolve`, Hash: `/#deconvolve`)

* **Primary Purpose:** Phase 15 Bayesian resolution of residential camp clinic visits back to daytime industrial worksites.
* **Layout Structure:** District selector, tactical transit corridor SVG map, candidate site ranking table, spatial ellipse telemetry panel.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| EXPOSURE-TO-SEEKING SPATIO-TEMPORAL DECONVOLUTION (PHASE 15)                                                            |
| Resolves residential dormitory clinic presentations back to upstream industrial exposure sites                           |
+-------------------------------------------------------------------------------------------------------------------------+
| Clinic District: [Muhaisnah (DXB-MU) v]   Case Count: [45 Workers]   Mean Lag: [6.5 Hours]   [Run Deconvolution Button] |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                         |                                               |
|  TACTICAL COMMUTE CORRIDOR SVG MAP (`#deconvolveSvgMapContainer`)       |  CANDIDATE EXPOSURE SITES RANKING             |
|  - Clinic Location: Muhaisnah (Blue Cross Marker)                      |  (`<tbody id="deconvolveCandidatesTbody">`)   |
|  - Transit Arterial Route: Sheikh Zayed Rd / E311 (Dotted cyan line)    |                                               |
|  - Candidate Sites: Jebel Ali Port, Al Quoz, Dubai South                |  1. Jebel Ali Port Terminal (SITE-JA-01)      |
|  - 95% Confidence Spatial Uncertainty Ellipse: Red dashed ellipse       |     - Posterior Probability: 53.4%            |
|    centered over Jebel Ali Port (~5.16 km² area)                       |     - Attributed Cases: 24.0 Workers          |
|                                                                         |     - Mean Exposure WBGT: 33.8°C              |
|                                                                         |     - Commute Flow Weight: 0.55               |
|                                                                         |                                               |
|                                                                         |  2. Dubai South Logistics (SITE-DS-01)        |
|                                                                         |     - Posterior Probability: 28.1%            |
+-------------------------------------------------------------------------+-----------------------------------------------+
| SPATIAL UNCERTAINTY ELLIPSE TELEMETRY: Center Coords: 25.012°N, 55.068°E | Major Axis: 4.8 km | Minor Axis: 2.1 km | Angle: 38°
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Interactive Buttons:**
  - `#deconvolveDistrictSelect`: Dropdown of residential clinic districts (`DXB-MU` Muhaisnah, `DXB-DR` Deira, `DXB-BD` Bur Dubai).
  - `#btnRunDeconvolution`: Invokes `runDeconvolution()` calling `/api/v1/spatial/deconvolve`.

---

### View 5: Municipal Fleet Staging & EMS Optimizer (`#view-dispatch`, Hash: `/#dispatch`)

* **Primary Purpose:** Phase 16 automated city defense routing cooling buses, misting trailers, and DCAS ambulances.
* **Layout Structure:** Alert target banner, 3-column staging allocation radar, international interoperability download bar.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| AUTOMATED PREVENTION TRIGGER: MUNICIPAL COOLING FLEET & EMS STAGING (PHASE 16)                                           |
| Target Trigger: Alert ALT-JEBELALI-01 | Site: Jebel Ali Port Terminal | Workforce at Risk: 1,400 Workers               |
+-------------------------------------------------------------------------------------------------------------------------+
| [DEPOT 1: Jebel Ali Operations Yard (4.2 km)]   | [DEPOT 2: Al Quoz Municipal Depot (18.5 km)] | [DCAS AMBULANCE PRE-STAGE]  |
| - Mobile A/C Cooling Buses: 3 Buses Assigned    | - Mobile A/C Cooling Buses: 2 Buses Assigned| - Standby Units: 2 Paramedic|
| - Solar Misting Trailers:   8 Units Assigned    | - Solar Misting Trailers:   4 Units Assigned| - Location: Gate 4 Triage   |
| - Potable Water Tankers:    2.8 Tons Potable    | - Potable Water Tankers:    1.4 Tons Potable| - Response Time: <4 Minutes |
+-------------------------------------------------------------------------------------------------------------------------+
| INTERNATIONAL INTEROPERABILITY & WORKFLOW TRIGGER:                                                                      |
| [Download HL7 FHIR R4 Task JSON (`#btnDownloadFhirTask`)]   [Download Markdown Operational Brief (`#btnDownloadBrief`)]   |
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Interactive Buttons:**
  - `Download HL7 FHIR R4 Task` (`#btnDownloadFhirTask`): Triggers client download of compliant FHIR R4 Task resource JSON.
  - `Download Operational Brief` (`#btnDownloadBrief`): Downloads markdown briefing with cited municipal SOPs.

---

### View 6: Inception 42 Jais Sovereign LLM & Voice Notes (`#view-jais`, Hash: `/#jais`)

* **Primary Purpose:** Phase 17 culturally authentic multi-lingual frontline voice and text dispatch synthesis.
* **Layout Structure:** Dual-execution telemetry banner, smartphone frame mockup, language selector tabs, audio waveform player.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| INCEPTION 42 JAIS-3-0.9B-CHAT SOVEREIGN AI DISPATCH (PHASE 17)                                                          |
| Engine Mode: JAIS_NATIVE_TORCH (Local GPU: cuda:0) / JAIS_VERIFIED_TEMPLATE | Fenced Hallucination Gate: PASSED (100%)    |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                                                                         |
|  FRONT-LINE SMARTPHONE SIMULATOR (`.smartphone-frame`)                                                                   |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|  | WhatsApp Direct Message • Munzir Safety Operational Channel                                                       |  |
|  | Language Selector: [العربية (Arabic)]  [English]  [اردو (Urdu)]  [हिन्दी (Hindi)]                                    |  |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|  |                                                                                                                   |  |
|  |  INCOMING DISPATCH CARD (`#jaisCardNarrative`):                                                                    |  |
|  |  "تحذير بلدي عاجل: تم رصد إجهاد حراري شديد في ميناء جبل علي (مؤشر WBGT: 33.8°م).                                  |  |
|  |   بموجب القرار الوزاري رقم 44 لسنة 2022، يُلزم بتطبيق فترات راحة مظللة وتوفير أملاح الترطيب الفموي فورا."         |  |
|  |                                                                                                                   |  |
|  |  AUDIO DISPATCH CONTROLLER:                                                                                       |  |
|  |  [PLAY SPOKEN VOICE NOTE BUTTON (`#btnPlayJaisAudio`)]                                                            |  |
|  |  Audio Waveform Visualizer (`#jaisAudioWaveform`):  |||||||||||||||||||||||||||| (Bouncing green bars)           |  |
|  |                                                                                                                   |  |
|  |  TWO-WAY WORKER ACTION CONFIRMATION:                                                                              |  |
|  |  [Confirm Shaded Rest Implemented]  [Confirm Electrolyte Water Received]                                         |  |
|  +-------------------------------------------------------------------------------------------------------------------+  |
|                                                                                                                         |
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Interactive Buttons:**
  - Language tabs (`.jais-lang-tab`): Changes dispatch text and TTS voice to Arabic, English, Urdu, or Hindi.
  - `#btnPlayJaisAudio`: Executes `playJaisVoiceNote()` via HTML5 `window.speechSynthesis` with animated equalizer.
  - Confirmation buttons: Appends outgoing confirmation chat bubble with blue double checkmarks (`[OK][OK]`).

---

### View 7: Safe-Harbor Worker Protection Shield (`#view-safeharbor`, Hash: `/#safeharbor`)

* **Primary Purpose:** Phase 20 cryptographic and architectural defense enforcing **UAE Federal Decree-Law No. 33 of 2021 Article 13**.
* **Layout Structure:** Statutory legal banner, interactive employer disciplinary query probe, live cryptographic quarantine log.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| SAFE-HARBOR WORKER PROTECTION SHIELD (PHASE 20)                                                                         |
| Non-Punitive Occupational Health Guarantee • UAE Federal Decree-Law No. 33 of 2021 Article 13 Enforcement              |
+-------------------------------------------------------------------------------------------------------------------------+
|                                                                         |                                               |
|  INTERACTIVE DISCIPLINARY ATTACK PROBE                                  |  CRYPTOGRAPHIC DEFENSE & AUDIT LOG            |
|  Simulates an unauthorized employer query seeking worker break logs:    |  (`<div id="shDefenseLogResult">`)            |
|                                                                         |                                               |
|  SQL Payload Under Test:                                                |  HTTP STATUS: 403 FORBIDDEN                   |
|  SELECT break_count, hydration_ml                                       |  Security Action: CRYPTOGRAPHICALLY QUARANTINED|
|  FROM worker_telemetry WHERE worker_id='WRK-DXB-1049'                   |  Statutory Basis: UAE Labor Decree-Law 33/2021|
|                                                                         |  Article 13: "Occupational monitoring cannot  |
|  [TEST EMPLOYER DISCIPLINARY QUERY BUTTON (`#btnTestDisciplinary`)]     |  be used for wage deductions or sanctions."   |
|                                                                         |  Quarantine Token: SHA256: 9e3f...88a1        |
+-------------------------------------------------------------------------+-----------------------------------------------+
| DIFFERENTIAL PRIVACY BUDGET ACCOUNTING: Mechanism: OpenDP Laplace | ε Consumed: 0.142 / 1.000 | Small-Cell Threshold: k >= 50
+-------------------------------------------------------------------------------------------------------------------------+
```

* **Key Interactive Buttons:**
  - `#btnTestDisciplinary`: Invokes `testDisciplinaryQuery()`, posting to `/api/v1/privacy/test-disciplinary-query` and rendering the hard HTTP 403 block.

---

### View 8: Health Impact Model & Policy ROI (`#view-impact`, Hash: `/#impact`)

* **Primary Purpose:** Audited economic proof showing **AED 1.36M Net Savings** and **8.11:1 Benefit-Cost Ratio**.
* **Layout Structure:** 5-variable interactive input slider deck on left, real-time KPI metrics and sensitivity matrix on right.

```text
+-------------------------------------------------------------------------------------------------------------------------+
| HEALTH & RESILIENCE IMPACT MODEL: 10,000-RUN MONTE CARLO SIMULATION                                                     |
+-------------------------------------------------------------------------------------------------------------------------+
|  INTERACTIVE POLICY CONTROLS                                            |  AUDITED ECONOMIC RETURNS                     |
|  - Workforce Size: [ 50,000 Workers Slider ]                            |  +-----------------------------------------+  |
|  - Baseline Heat Illness Rate: [ 4.2 per 1,000 ]                        |  | NET ECONOMIC BENEFIT:   AED 1,364,167     |  |
|  - Preventability Factor: [ 65% Preventable ]                           |  | BENEFIT-TO-COST RATIO: 8.11 : 1          |  |
|  - Cost per Lost Workday: [ AED 450 / Day ]                             |  | 90% CONFIDENCE INTERVAL: [3.45x - 19.73x] |  |
|  - Severe Case ICU Cost: [ AED 18,500 / Case ]                          |  | LOST WORKDAYS AVERTED: 3,480 DAYS         |  |
|                                                                         |  | ICU ADMISSIONS AVERTED: 25 CASES          |  |
|                                                                         |  +-----------------------------------------+  |
|                                                                         |  2D SENSITIVITY MATRIX (BCR vs Workday Cost): |
|                                                                         |  [Interactive Heatmap Grid Table]             |
+-------------------------------------------------------------------------+-----------------------------------------------+
```

* **Key Interactive Sliders:**
  - `#sliderWorkforceSize`: Range 1,000 to 200,000 laborers. Updates economic calculations instantaneously without page reload.

---

## 4. Modals & Slide-Out Overlays

All modals use dark frosted glass backdrop (`.modal-overlay` with `background: rgba(3, 7, 18, 0.85)` and `backdrop-filter: blur(8px)`).

### 1. Decision-Ready Evidence Card Modal (`#evidenceCardModal`)
* **Trigger:** Clicking `[Evidence Card]` on any alert row in `#view-inbox` or node on `#view-map`.
* **Internal Sections:**
  1. Header: Alert ID, Risk Tier Badge, Location Name.
  2. Statistical Uncertainty: Calibrated Probability $P \in [0, 1]$ and conformal bands $[ci_{low}, ci_{high}]$.
  3. TreeSHAP Feature Attribution: Horizontal colored bars for Environmental, Workplace Absence, and Syndromic drivers.
  4. Decision Support Directives: Step-by-step statutory response plan under UAE Resolution 44 of 2022.
  5. Close Button: `onclick="closeEvidenceCardModal()"`.

### 2. Master System Dossier Modal (`#systemDossierModal`)
* **Trigger:** Clicking `MODELS & DOSSIER` in the master header or footer links.
* **Internal Segmented Navigation Tabs:**
  - `arch`: 5-Layer End-to-End System Architecture.
  - `models`: Mathematical equations for all 12 platform models (EARS, Farrington, Kulldorff, LightGBM, CKD-EPI, KDIGO, Weibull Deconvolution, Dirichlet Causal De-Mixer, Stull WBGT, Isotonic Calibrator, OpenDP Laplace, Jais-3-0.9B).
  - `lakehouse`: Partition explorer showing 60,473 Parquet records across Bronze, Silver, and Gold.
  - `ai`: Inception 42 Jais LLM parameters, GPU device mapping, and hallucination gate tokens.
  - `audit`: Live summary of 258/258 passing regression tests.

### 3. Floating Sovereign Copilot Drawer (`#floatingCopilotDrawer`)
* **Trigger:** Clicking the floating pill `#floatingCopilotBtn` positioned at bottom-right (`bottom: 38px, right: 24px`).
* **Components:**
  - Suggestion Chips: `30-Min Directives`, `Explain Jebel Ali risk`, `Resolution 44 Penalty`, `Municipal Fleet Staging`.
  - Chat Message Stream (`#drawerChatStream`): Renders incoming and outgoing dialogue bubbles.
  - Input Form (`#drawerInput`, Submit Button): Accepts natural language queries and streams verified responses.

---

## 5. Design System & CSS Specifications

### Color Palette

| Token Name | Hex Code | RGB | Usage |
|---|---|---|---|
| `--bg-main` | `#070c18` | `rgb(7, 12, 24)` | Window and body background |
| `--bg-card` | `#0b1120` | `rgb(11, 17, 32)` | Card, modal, and panel background |
| `--border-subtle` | `rgba(255, 255, 255, 0.08)` | - | Borders, dividers, card outlines |
| `--accent-cyan` | `#38bdf8` | `rgb(56, 189, 248)` | Tactical primary highlight, links, active tabs |
| `--status-normal` | `#10b981` | `rgb(16, 185, 129)` | Normal tier badge, healthy feeds |
| `--status-watch` | `#f59e0b` | `rgb(245, 158, 11)` | Watch tier badge, moderate heat advisory |
| `--status-warning` | `#f97316` | `rgb(249, 115, 22)` | Warning tier badge, shaded rest mandated |
| `--status-alert` | `#ef4444` | `rgb(239, 68, 68)` | Alert tier badge, emergency work stoppage |

### Typography
* **UI Prose & Headers:** `Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif`
* **Metrics, Telemetry & IDs:** `'JetBrains Mono', SFMono-Regular, Menlo, Monaco, Consolas, monospace`

### Policy Constraints
* **Strictly Zero Emojis:** Prohibited in all UI labels, buttons, badges, modals, and charts. Replaced by standardized defense-grade text tags (e.g. `[ACTION]`, `[NORMAL]`, `[WARNING]`).
* **No Automated Demo Tours:** User manual control only.

---

## 6. Component Quick Reference Cheatsheet for AI Agents

When constructing or modifying frontend views, use this mapping:

| View Name | URL Hash | Pillar Name | Primary Interactive Button / Element | Injected Container ID | API Route Queried |
|---|---|---|---|---|---|
| **Situation Map** | `/#map` | `command` | Node click / `#tacticalKpiRibbon` | `#situationSvgMap`<br>`#mapGeoList` | `GET /api/v1/map/layers` |
| **Alert Inbox** | `/#inbox` | `command` | `[Evidence Card]` button | `#alertsTbody` | `GET /api/v1/alerts` |
| **Heat Strain (ISO 7933)** | `/#phs` | `clinical` | `#phsPresetSelect` | `#phsTrajectoryCanvas` | `GET /api/v1/health/feeds` |
| **Renal Biomarkers** | `/#renal` | `clinical` | `#btnRunRenalScreening` | `#renalTrajectorySvgContainer` | `GET /api/v1/renal/screening` |
| **Spatial Deconvolution** | `/#deconvolve` | `clinical` | `#btnRunDeconvolution` | `#deconvolveSvgMapContainer` | `GET /api/v1/spatial/deconvolve` |
| **Compound Multi-Hazard** | `/#compound` | `clinical` | `#btnRecalcCompound` | `#compoundMetricTiles` | `GET /api/v1/hazard/compound-assessment` |
| **Bayesian Causal De-Mix** | `/#causal` | `clinical` | 1-Click Preset Buttons | `#causalDemixBarMeter` | `GET /api/v1/detection/causal-demix` |
| **NABIDH FHIR CDS** | `/#nabidh` | `clinical` | `#btnExportNabidhBundle` | `#nabidhJsonDisplay` | `GET /api/v1/fhir/nabidh-bundle` |
| **Sentinel IoT Twin** | `/#sentinel` | `operations` | `[ACTION] Press BOOT Button` | `#sentinelBuzzerBadge` | `POST /api/v1/sentinel/ack` |
| **Municipal Staging** | `/#dispatch` | `operations` | `#btnDownloadFhirTask` | `#dispatchDepotGrid` | `GET /api/v1/dispatch/optimize` |
| **Employer Safety View** | `/#employer` | `operations` | Role Switcher `employer_safety` | `#employerDirectivesList` | `GET /api/v1/alerts` (Masked) |
| **Two-Way Voice Intercom**| `/#intercom` | `sovereign_ai` | `#btnStartVoiceIntercom` | `#intercomTranscriptLog` | `POST /api/v1/intercom/process` |
| **Jais Dispatch** | `/#jais` | `sovereign_ai` | `#btnPlayJaisAudio` | `#jaisCardNarrative` | `GET /api/v1/jais/dispatch` |
| **Sovereign Copilot** | `/#copilot` | `sovereign_ai` | `#btnSubmitCopilot` | `#copilotMessageStream` | `POST /api/v1/copilot/query` |
| **MOHRE Policy Studio** | `/#policystudio` | `resilience` | `#btnReplayPolicy` | `#policyImpactMetrics` | `GET /api/v1/impact/assumptions` |
| **Health Impact Model** | `/#impact` | `resilience` | `#sliderWorkforceSize` | `#impactSummaryCard` | `POST /api/v1/impact/calculate` |
| **Time Machine Replay** | `/#timemachine` | `resilience` | `#btnRunReplay` | `#timeMachineTimeline` | `GET /api/v1/timemachine/replay` |
| **What-If Simulator** | `/#whatif` | `resilience` | `#whatifScenarioSelect` | `#whatifChartContainer` | `GET /api/v1/whatif/simulate` |
| **Safe-Harbor Shield** | `/#safeharbor` | `resilience` | `#btnTestDisciplinary` | `#shDefenseLogResult` | `POST /api/v1/privacy/test-disciplinary-query` |
| **Data Health Panel** | `/#health` | `resilience` | `#btnRefreshHealth` | `#dataHealthFeedsTable` | `GET /api/v1/health/feeds` |
| **Missing-Data Validation**| `/#demo` | `resilience` | `#missingDataScenarioSelect` | `#missingDataResults` | `GET /api/v1/health/feeds` |
| **Security Audit Logs** | `/#audit` | `resilience` | `#btnRefreshAudit` | `#auditLogsTbody` | `GET /api/v1/audit/logs` |

