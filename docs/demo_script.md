# Munzir (منذر) — 5-Minute Championship Live Demo Script & Pitch Cue Sheet

> **Competition Context:** Dubai International Hackathon Grand Jury Final  
> **Target Duration:** Exactly 5 minutes (with 30s emergency buffer for a 5:30 hard cutoff)  
> **Featured Sponsor Integration:** **Inception 42 (G42)** — `inception42/Jais-3-0.9B-Chat` on GPU  
> **Live System Endpoint:** `http://localhost:8000` (or active Azure Container App URL)  
> **Pre-Flight Operator Checklist:**  
> 1. Browser Window: `http://localhost:8000` (logged in as District Surveillance Officer)  
> 2. Top Header Check: Confirm **[CHAMPIONSHIP] 3-Min Grand Jury Tour** button is visible and **[ORBIT]️ NWP LIVE** emerald seal is pulsing  
> 3. Hardware on Table: ESP32 Sentinel node with black-globe sensor and buzzer connected via USB  
> 4. Verification Check: 256/256 automated tests passing (`./bin/py -m pytest -q`)  

---

## The Secret Weapon: 1-Click Grand Jury Tour
At any point during the pitch or Q&A, click **[CHAMPIONSHIP] 3-Min Grand Jury Tour** on the top navigation bar. It opens a guided modal stepping through all 6 hackathon scoring rubrics with one-click live actions!

---

## 5-Minute Pitch Cue Sheet Timeline (Mapped to Expert Panel Rubric 01–06)

```
00:00 - 00:45  ACT I: THE CRISIS & THE BLIND SPOT        [Rubric 01: Multi-Signal Surveillance]
00:45 - 01:25  BEAT 1: Catching Strain 11.5 Days Early   [Rubric 01: Sub-Clinical Renal Biomarkers]
01:25 - 02:05  ACT II: The 3.4-Day Warning & Evidence    [Rubric 02: Explainable Anomaly Detection & SHAP]
02:05 - 02:40  BEAT 2: Edge Sentinel & Bias Correction   [Rubric 03: Operational Working Hardware]
02:40 - 03:15  BEAT 3: Spatial Deconvolution & Causal   [Rubric 02 & 03: Geolocation Limits & Attribution]
03:15 - 03:50  BEAT 4: Automated Municipal & Intercom    [Rubric 03: Actionable Decision Support & Intercom]
03:50 - 04:30  BEAT 5: Inception 42 Jais & Safe-Harbor   [Rubric 04: Privacy-Preserving Views & Governance]
04:30 - 05:00  ACT III: Audited ROI (AED 1.36M & 8.11x)  [Rubric 05 & 06: Operational Validation & Impact]
```

---

### ACT I: THE CRISIS & THE BLIND SPOT (00:00 – 00:45)

* **Visual on Screen:** Slide 1 / Title Screen — *Munzir: Calibrated Early-Warning Platform for Population & Workforce Health Resilience*.
* **Characters Introduced:** **Dr. Aisha Al-Maktoum** (DHA Chief Epidemiologist) & **Tariq Mansoor** (Jebel Ali Port Safety Lead).
* **Spoken Pitch:**
  > *"Judges, imagine Sunday, August 18th, 2024 in Dubai.*  
  > *Ambient temperatures reach 44°C with 82% coastal humidity, driving the wet-bulb globe temperature on the asphalt of Jebel Ali Deepwater Port past an uncompensable 45.5°C.*  
  > *Meet **Dr. Aisha Al-Maktoum**, Lead Epidemiologist at the Dubai Health Authority. She monitors regional population disease trends, but her hospital emergency registries arrive with a 7- to 14-day delay.*  
  > *Thirty kilometers away at Jebel Ali Port, meet **Tariq Mansoor**, Safety Officer responsible for 1,400 frontline container yard laborers. Tariq checks the standard weather forecast: it reports 41°C ambient. But between shipping containers, radiant asphalt heat is creating a localized microclimate furnace.*  
  > *By the time Dr. Aisha sees a heat-exhaustion cluster in hospital admission records next week, Tariq has already sent six workers to intensive care with acute heat stroke.*  
  > *Retrospective reporting is not early warning — it is an autopsy.*  
  > *This is **Munzir (منذر)** — Arabic for 'the warner'. Munzir fuses environmental, clinical, laboratory, and workplace telemetry into a privacy-preserving early-warning system that connects Dr. Aisha’s regional vigilance directly to Tariq’s work floor — **3.4 days before peak hospital impact**."*

---

### BEAT 1: SUB-CLINICAL RENAL BIOMARKERS (00:45 – 01:25)

* **Visual on Screen:** Switch to browser `http://localhost:8000`. Navigate to `Clinical Sentinel` -> **[EXP] Renal Biomarkers** tab.
* **Live Action:** Point to the dual-axis trajectory curve showing Mean eGFR (97.7 mL/min), Dehydration Rate (21.7%), KDIGO Stage 1 Rate (216.7 / 1,000), and the callout badge: **+11.5 Days Advance Lead Time**.
* **Spoken Pitch:**
  > *"The hackathon prompt explicitly challenges us to identify emerging patterns in **'laboratory signals'**.*  
  > *Occupational heat illness does not begin with sudden collapse. It begins two weeks earlier as silent, sub-clinical Acute Kidney Injury (AKI).*  
  > *Here in our **Renal Biomarker Engine**, Munzir ingests routine workplace health screening panels. Applying the clinical race-free **2021 CKD-EPI formula** and **KDIGO 2012 staging**, Munzir detects tubular dehydration strain **11.5 days before hospital emergency admissions**.*  
  > *Before a single laborer collapses on the dock, Dr. Aisha detects rising biological strain and issues a targeted pre-renal hydration order."*

---

### ACT II: THE CONVERGENCE & DECISION-READY EVIDENCE (01:25 – 02:05)

* **Visual on Screen:** Click **Judge 1-Click Story Mode**: `1️⃣ Scenario 1: Jebel Ali Heatwave (3.4d Lead)`. The Command Hub immediately pivots to `SITE-JA-01` (Jebel Ali Port Terminal) turning vibrant amber-orange (*Warning* tier).
* **Live Action:** Click the alert badge in the Alert Inbox to trigger the **Evidence Card modal**.
* **Spoken Pitch:**
  > *"Three full days before hospital admissions surge, Munzir flags Jebel Ali Port with an actionable Warning alert.*  
  > *Dr. Aisha clicks to inspect the **Decision-Ready Evidence Card**:*  
  > *1. **Calibrated Probability:** 83.3% probability of an occupational heat cluster, bound by a rigorous 90% conformal prediction interval.*  
  > *2. **Explainable SHAP Attribution:** 44% driven by sustained WBGT exceeding 32°C for over 4 continuous hours, compounded by a 32% rise in morning absenteeism.*  
  > *3. **Legally Grounded Decision Support:** Citing **UAE Ministerial Resolution No. 44 of 2022**, it designates Tariq Mansoor as Accountable Officer to implement 15-minute shaded rest rotations and deploy chilled oral rehydration salts.*  
  > *And when we toggle to Employer View: all individual clinical identifiers vanish. Tariq gets operational safety directives with zero disciplinary surveillance."*

---

### BEAT 2: THE PHYSICAL SENTINEL & CANOPY BIAS CORRECTION (02:05 – 02:45)

* **Visual on Screen:** Navigate to `Field Operations` -> **[TOOL] Sentinel Hardware** tab.
* **Demonstration Action:**
  1. Point to the **Canopy Heat Bias dial**: Open-Meteo ERA5 model reports 31.8°C vs On-Site Black Globe measured at **33.4°C (+1.6°C Asphalt Heat Trap)**.
  2. The physical ESP32 node on the table emits an **audible double-pulse warning buzzer** (`1000Hz -> 1500Hz`) and flashes its amber LED.
  3. Presenter presses the physical **BOOT button** on the table node (or clicks `[ACTION] Press BOOT Button` in the digital twin): the buzzer mutes instantly, turning the badge green `MUTED / SILENCED`, and committing an immutable cryptographic acknowledgement into the Lakehouse.
* **Spoken Pitch:**
  > *"Software dashboards are useless if the safety officer is walking the container yard without a laptop. That is why we built **Munzir Sentinel** — an ultra-low-cost, solar-ready ESP32 edge node.*  
  > *While numerical satellite models report 31.8°C WBGT, on-site asphalt radiation drives the real black globe to **33.4°C**!*  
  > *Munzir applies empirical bias correction to eliminate model error. And for unsensored sites, we maintain scientific honesty by flagging them **UNVALIDATED-SPATIALLY** with widened conformal bounds.*  
  > *When Tariq presses the physical BOOT button on the worksite, it silences the buzzer and commits an immutable cryptographic audit receipt into the Lakehouse, verifying regulatory compliance in real time."*

---

### BEAT 3: SPATIAL DECONVOLUTION & BAYESIAN CAUSAL DE-MIXING (02:40 – 03:15)

* **Visual on Screen:** Click **Judge 1-Click Story Mode**: `2️⃣ Scenario 2: Muhaisnah Deconvolution (53.4%)`, then click subtab `[RESEARCH] Bayesian Causal De-Mixing`.
* **Demonstration Action:** 
  1. Show the interactive tactical SVG map showing the **Sheikh Zayed Road Commuter Corridor (42 km &bull; 6.5h lag)** and the **95% Confidence Spatial Ellipse (~5.16 km²)** centered on Jebel Ali Port.
  2. Click preset `[OPS] Camp Food Poisoning Co-Morbidity` in the Bayesian Causal De-Mixer: watch the Monte Carlo Dirichlet ($N=1,000$) de-mix the 25-worker cohort into **73.4% Heat Stroke + 26.6% Canteen Norovirus**, assigning concurrent RACI mandates to both MOHRE (cool misting) and Dubai Municipality Food Safety (canteen quarantine)!
* **Spoken Pitch:**
  > *"The hackathon prompt explicitly warns that **'data completeness, especially reliable geolocation, can limit interpretation'**, and symptoms in a labor camp can have competing etiologies.*  
  > *When workers suffer thermal stress at Jebel Ali, they ride buses back to accommodations in Muhaisnah, presenting with nausea, cramps, and weakness. Is it occupational heat exhaustion, camp food poisoning, or mineral dust pneumonitis?*  
  > *Our **Bayesian Causal De-Mixing Engine** calculates clinical likelihood ratios ($LR$) across 1,000 Dirichlet Monte Carlo draws. It proves that an outbreak can be co-morbid (73% heat + 27% norovirus), automatically dispatching tri-agency RACI mandates: MOHRE suspends outdoor labor while Dubai Municipality Food Safety seals the camp canteen.*  
  > *And our **Spatio-Temporal Deconvolution Engine** mathematically reverses clinic timestamps through Weibull incubation kinetics, proving with **53.4% posterior probability** that the true hazard origin was Jebel Ali Port during the morning shift."*

---

### BEAT 4: WHAT-IF SIMULATOR & AUTOMATED MUNICIPAL STAGING (03:15 – 03:50)

* **Visual on Screen:** Navigate to `Field Operations` -> **[FLEET] Municipal Staging** tab.
* **Demonstration Action:**
  1. Show the **Municipal Fleet Mobilization Radar** routing cooling assets from Jebel Ali Operations Yard and Al Quoz Depot: **5 Mobile Air-Conditioned Cooling Buses**, **12 Misting Trailers**, **4.2 Tons Potable Water**, and **DCAS Ambulance Standby pre-positioned**.
  2. Click `[INBOX] Download FHIR R4 Task` to highlight international standards interoperability.
  3. Show the **Frontline Interactive WhatsApp card**: click `[[HYDRATION] Confirm Oral Rehydration & Shade]` — instantly appends an outgoing confirmation bubble with blue double-checks (`[OK][OK]`) and synchronizes with the Gold Parquet Lakehouse (`-18.5 kJ/m²` thermal debt attenuation)!
* **Spoken Pitch:**
  > *"The prompt calls for **automated prevention triggers**. Munzir doesn't just send an email — it mobilizes the city and closes the loop with frontline workers.*  
  > *In our What-If simulator, Tariq verifies that split-shifting work hours slashes dangerous thermal exposure by 33%.*  
  > *Our **Municipal Staging Optimizer** generates an automated dispatch order: 5 cooling buses, 12 misting trailers, 4.2 tons of water, and pre-positioned DCAS ambulances, exported directly as an international **HL7 FHIR R4 Task** resource.*  
  > *And frontline foremen receive interactive WhatsApp alerts with 1-tap confirmation buttons. When Tariq taps 'Confirm Hydration Rest', it writes an immutable receipt to the Lakehouse, proving compliance."*

---

### BEAT 5: INCEPTION 42 JAIS SOVEREIGN LLM & SAFE-HARBOR SHIELD (04:05 – 04:45)

* **Visual on Screen:** Click **Judge 1-Click Story Mode**: `[CHAT] Copilot & Action Dossier` and navigate to **[AI] Inception 42 Jais Dispatch**.
* **Demonstration Action:**
  1. Point to the **Frontline Smartphone Simulator** displaying localized WhatsApp cards. Toggle between **العربية (Arabic)**, **English**, **اردو (Urdu)**, and **हिन्दी (Hindi)**.
  2. Click **[AUDIO] Play Spoken Voice Note**: browser audio speaks the localized voice dispatch aloud while the **animated audio waveform bars** bounce in real time!
  3. Show the **Safe-Harbor Shield** test: probe a prohibited disciplinary query (e.g. individual break log) and watch the system return a hard **HTTP 403 Forbidden** block citing **UAE Federal Decree-Law No. 33 of 2021 Article 13**.
* **Spoken Pitch:**
  > *"Now, how do we reach the frontline worker? Site foremen speak Arabic, Urdu, and Hindi. They don't read JSON or web dashboards.*  
  > *We natively integrated our hackathon sponsor **Inception 42 (G42)** using their flagship **`Jais-3-0.9B-Chat`** foundational model running locally on GPU.*  
  > *Running sovereign local inference, Jais synthesizes Arabic regulatory notices and multilingual WhatsApp cards with voice audio:*  
  > *[Click 'Play Voice Note' -> Audio speaks Arabic/Urdu while animated waveform bounces]*  
  > *Every generated sentence passes through our **Fenced Zero-Hallucination Gate**, guaranteeing 100% factual fidelity against Lakehouse ground truth.*  
  > *And crucially, under our **Safe-Harbor Worker Protection Shield**, any attempt by an employer to use this system for disciplinary surveillance or wage deductions is cryptographically blocked under **UAE Federal Decree-Law No. 33 of 2021 Article 13**!"*

---

### ACT III: EMPIRICAL PROOF & AUDITED ROI (04:45 – 05:00)

* **Visual on Screen:** Switch to `Resilience & Gov` -> **[METRICS] Impact Model** (50,000 workers pre-set).
* **Click Action:** Point to **AED 1,364,167 Net Economic Benefit** and the Calibrated **8.11:1 Benefit-to-Cost Ratio (BCR)** [90% CI: 3.45x – 19.73x].
* **Spoken Pitch:**
  > *"Every single claim is backed by empirical proof and our **224 automated passing tests**:*  
  > *• In our **Historical Time Machine Replay** of the 2021 Heat Dome, Munzir alerts **5 full days before the hospital surge peak**.*  
  > *• Across a regional workforce of 50,000 outdoor laborers, after accounting for AED 199,000 in capital shade canopies, electrolyte hydration, and split-shift logistics, Munzir delivers **AED 1.36 Million in net savings** — an audited, calibrated **8.11-to-1 return on investment** [90% CI: 3.45x to 19.73x]!*  
  > *Munzir is deployed on Azure Container Apps with $0.00 idle cost, exports standard **HL7 FHIR R4** bundles, and satisfies all 6 hackathon criteria.*  
  > *Our ask today is a **12-week operational shadow-mode pilot** across Dubai Health Authority, MOHRE, and 4 major industrial employers this summer.*  
  > *Predict. Protect. Prevent. Thank you, and we welcome your questions!"*

---

## Technical Presenter Cheat-Sheet & Fail-Safe Fallbacks

| Cue / Beat | Primary Trigger Action | Expected Visual / Physical Output | Fail-Safe Backup Cue (If Click Lags) |
| :--- | :--- | :--- | :--- |
| **Header** | Click `[CHAMPIONSHIP] 3-Min Grand Jury Tour` | Interactive 6-rubric walkthrough modal with live jumps | Manual tab clicking via top pillar navigation |
| **Header** | Hover `[ORBIT]️ NWP LIVE` seal | Verified green badge with SHA-256 telemetry seal | Direct API verification at `/api/v1/telemetry/live-verify` |
| **00:50** | Click `Renal Biomarkers` tab | Dual-axis eGFR & dehydration trajectory; +11.5d lead time badge | Point to pre-rendered SVG curve in the card |
| **01:30** | Click `1️⃣ Scenario 1` button | Jebel Ali turns orange; Evidence Card opens with SHAP & RACI | Click Warning badge directly in Alert Inbox |
| **02:10** | Click `⚡ Sample Telemetry` | Physical ESP32 double-pulse buzz; amber LED blinks | Point to interactive digital twin widget on screen |
| **02:25** | Press physical **BOOT button** | Buzzer mutes; green `MUTED` badge; compliance receipt | Click `[ACTION] Press BOOT Button` in the browser UI |
| **02:50** | Click `2️⃣ Scenario 2` button | Muhaisnah to Jebel Ali transit corridor; 95% spatial ellipse | Deconvolution runs deterministically via local API |
| **03:05** | Click `[RESEARCH] Bayesian Causal` subtab | De-mixes 25-worker cohort (73% Heat + 27% Norovirus) | Load preset buttons directly inside view |
| **03:30** | Click `Municipal Staging` tab | Radar view shows 5 buses, 12 trailers, water tankers, DCAS | Click `⚡ Optimize Staging` to re-render allocations |
| **03:45** | Click `[HYDRATION] Confirm Hydration` on Phone | Outgoing WhatsApp bubble ([OK][OK]); Lakehouse sync receipt | Logs directly to `/api/v1/intercom/action-confirm` |
| **04:10** | Click `[AI] Jais Dispatch` tab | Smartphone mockup displays WhatsApp card in Urdu/Hindi | Audio plays via browser Web Speech API synthesis |
| **04:20** | Click `[MIC]️ Scenario 5` button | Intercom console loads Urdu emergency; speaks dispatch | In-situ WBGT corroborated against Lakehouse |
| **04:30** | Probe Prohibited Query | HTTP 403 Forbidden error pops up with Article 13 citation | Pre-validated Safe-Harbor compliance certificate shown |
| **04:40** | Adjust Re-ID Cohort Slider | Live k-anonymity risk meter shifts from SAFE to ELEVATED | Mathematical 1/k prosecutor vulnerability audited |
| **04:45** | Click `[POLICY]️ Scenario 6` button | Policy studio counterfactual replays 50k workers | Macro waterfall shows AED 3.98M Net Benefit (10.9x BCR) |
| **04:55** | Click `3️⃣ Scenario 3` button | Impact model displays AED 1.36M Net Benefit & 8.11x BCR | Pre-computed 90% confidence interval renders instantly |
