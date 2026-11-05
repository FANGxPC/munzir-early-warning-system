# Munzir (منذر) — 5–7 Minute Live Demo Script & Pitch Cue Sheet

> **Presenter Cue Sheet:** Championship Hackathon Pitch  
> **Target Duration:** 6 minutes 30 seconds (leaving 30s buffer for 7-minute hard stop)  
> **Live URL:** `http://localhost:8000` (or live Azure Container App endpoint)  
> **Operator Checklist:** Pre-load browser tabs:
> 1. Dashboard (`/`)
> 2. Validation Report (`validation/report.html`)
> 3. Evidence Brief Markdown (`/api/v1/impact/policy-report/markdown`)
> 4. Backup local video in case of network interruption

---

## Chronological Pitch Cue Sheet

```
00:00 - 00:55  Slide 1 & 2: The Problem (Retrospective Silos & Extreme Heat)
00:55 - 01:40  UI: Live Map Baseline (Quiet Day -5) & Fast-Forward Clock
01:40 - 02:50  Scenario 1: Occupational Heat Cluster (3.4-Day Advance Warning & Evidence Card)
02:50 - 03:40  Scenario 3: Unexplained Cluster vs Environmental Excess (The Differentiator)
03:40 - 04:25  Live Fault Injection: Missing Clinical Feed & Conformal Resilience
04:25 - 04:55  Decoy Filtering: Reporting Backlog Suppression
04:55 - 05:40  Validation Harness: Empirical Proof & AMOC Curve (report.html)
05:40 - 06:15  Impact Calculator: $1.86M Net Benefit & Live Sliders
06:15 - 06:40  Responsible AI: 7/7 Passing Guardrails & Zero-PII Guarantee
06:40 - 07:00  The Ask: 12-Week Shadow-Mode Pilot
```

---

### Segment 1 (00:00 – 00:55): The Problem in One Slide
* **Visual:** Slide 1 — Split view: High-noon Dubai construction site vs delayed hospital registry spreadsheet.
* **Spoken Pitch:**
  > *"Every summer across the Gulf, over six million outdoor workers face extreme heat. Today, public health and safety officers operate blind: weather forecasts live in one portal, clinic visits sit locked in hospital systems, and workplace incident reports take days or weeks to compile.*  
  > *By the time an occupational heat-stroke cluster is noticed in hospital statistics, the damage is already done. Retrospective surveillance is not surveillance — it is an autopsy.*  
  > *This is **Munzir (منذر)** — Arabic for 'the warner'. Munzir fuses environmental, syndromic, and workplace telemetry into a privacy-preserving early-warning system that tells a named officer what is rising, where, why, how sure we are, and what proportionate action to take — days before peak impact."*

---

### Segment 2 (00:55 – 01:40): Live Map & The Quiet Baseline
* **Visual:** Switch to live Munzir web dashboard (`http://localhost:8000`). Show clean, calm map with green baseline indicators.
* **Click Action:** Click through the date selector to `2025-08-15` (Quiet Day −5).
* **Spoken Pitch:**
  > *"Here is Munzir running live. We are looking at Dubai and the Northern Emirates. On quiet days, the map is calm. Notice the role switcher in the top right: we support six Entra ID application roles. Currently, we are logged in as the District Surveillance Officer.*  
  > *Now, let’s advance the simulation clock toward August 20th. As extreme temperatures approach 45°C with high coastal humidity, watch the system transition seamlessly."*

---

### Segment 3 (01:40 – 02:50): Scenario 1 — Occupational Heat Cluster & Evidence Card
* **Visual:** Map highlights `SITE-JA-01` (Jebel Ali Industrial) and `DXB-JA` turning orange (*Warning* tier).
* **Click Action:** Click on the alert badge in the Inbox to open the **Evidence Card modal**.
* **Spoken Pitch:**
  > *"Notice what just happened. Three days before peak clinical presentations, Munzir fires an actionable Warning. Look at the Decision-Ready Evidence Card:*  
  > *1. It gives us a calibrated probability: 83.3% risk with a tight 90% conformal prediction interval.*  
  > *2. Look at the SHAP feature breakdown: it explains that 45% of the signal is driven by dangerous wet-bulb globe temperature duration exceeding 32°C, combined with a 35% spike in unexcused morning sickness absences.*  
  > *3. Crucially, look at the Action Playbook below: it is not generic advice. It is a legally grounded RACI matrix citing UAE MOHRE Midday Ban regulations, assigning the Site Safety Officer to enact 15-minute mandatory cooling rotations and hydration replenishment.*  
  > *Let's toggle to the Employer View: instantly, all individual clinical identifiers vanish. The employer sees only rate-based statistics, guaranteeing zero worker surveillance."*

---

### Segment 4 (02:50 – 03:40): Scenario 3 — Unexplained Cluster vs Environmental Excess
* **Visual:** Select `Scenario 3` alert in Al Quoz Industrial canteen (`SITE-AQ-01`).
* **Click Action:** Highlight the difference in the Evidence Card between "Environmental Explanation" and "Unexplained Residual".
* **Spoken Pitch:**
  > *"Now, here is what separates Munzir from simplistic anomaly detection: our Layer 2 exposure-response models.*  
  > *In August, sickness absence always rises with heat. If an algorithm alerts every time it gets hot, safety officers suffer alert fatigue and turn it off.*  
  > *Munzir fits negative binomial exposure baselines. In Scenario 3, ambient WBGT and PM2.5 are completely normal, but gastrointestinal clinic visits spike 4.8x. Munzir immediately flags this as an **'Unexplained Infectious Cluster'**, ruling out heat and directing the Rapid Response Team to investigate food and water contamination at the site canteen."*

---

### Segment 5 (03:40 – 04:25): Live Fault Injection — Missing Data Resilience
* **Visual:** Scroll to the **Data Quality & What-If Sandbox** panel.
* **Click Action:** Click the toggle switch to **Disable Clinical Syndromic Feed**.
* **Spoken Pitch:**
  > *"In real-world public health, systems fail. Clinical feeds drop out, hospitals suffer IT outages. Watch what happens when I cut the live hospital syndromic feed right now.*  
  > *Does Munzir crash? No. Does it fire hallucinated false alarms? No.*  
  > *Look at the confidence band: the conformal prediction interval immediately widens from ±10% to ±25%. The Data Quality score drops to 0.58, and our Layer 5 guardrail hard-caps the maximum alert tier at Warning, displaying a clear yellow badge: 'Clinical feed unavailable — uncertainty expanded'. This is fault-tolerant engineering."*

---

### Segment 6 (04:25 – 04:55): Decoy Filtering — Reporting Backlog Suppression
* **Visual:** Trigger a simulated 50-case reporting backlog dump from a private clinic chain.
* **Click Action:** Point to the audit log showing `DECOY_FILTERED`.
* **Spoken Pitch:**
  > *"What about data artefacts? When a private clinic chain uploads a delayed 5-day backlog of 50 reports all at once, typical AI systems trigger a code-red outbreak panic.*  
  > *Munzir’s data-quality filter checks the reporting delay timestamp distribution. Recognizing the sudden spike as a single-day reporting backlog dump, it tags it as a Data Artefact and suppresses the alarm, saving officers dozens of wasted investigation hours."*

---

### Segment 7 (04:55 – 05:40): Validation Harness — Empirical Proof on Back-Tests
* **Visual:** Switch tab to `validation/report.html`. Show the Activity Monitoring Operating Characteristic (AMOC) curve and metrics table.
* **Spoken Pitch:**
  > *"Every claim we make is backed by reproducible empirical evidence. Here is our automated validation harness, evaluated across 100 synthetic outbreak injections with full hold-out cross-validation:*  
  > *• Operational Lead Time: **3.4 days** advance warning.*  
  > *• Sensitivity: **87.5%**.*  
  > *• Positive Predictive Value: **83.3%**.*  
  > *• False Alarm Rate: Only **0.31 false alarms per month** — cutting alert fatigue by 76% compared to raw statistical baselines.*  
  > *And any judge can run `make validate SEED=42` right from terminal to reproduce every number live."*

---

### Segment 8 (05:40 – 06:15): Health & Resilience Impact Model ($1.86M Net Benefit)
* **Visual:** Switch to the **Impact Model** tab in the dashboard. Adjust the workforce slider from 50,000 to 75,000 workers.
* **Click Action:** Show real-time re-calculation of lost workdays and AED net benefit.
* **Spoken Pitch:**
  > *"What does this mean for health resilience and the economy? Our interactive impact model, grounded in UAE MOHRE and ILO epidemiological tariffs, shows that across a 50,000-worker industrial cohort, Munzir delivers:*  
  > *• **3,480 lost workdays saved** per summer season.*  
  > *• **25 severe heat-stroke ICU hospitalizations avoided**.*  
  > *• **AED 1,861,996 in net economic benefit**, at an incredible **758x Benefit-to-Cost Ratio**.*  
  > *And with our zero-latency sliders, leadership can test Low, Central, and High economic scenarios in real time."*

---

### Segment 9 (06:15 – 06:40): Responsible AI & Safety Guardrails (7/7 Passing)
* **Visual:** Switch to Slide 9 showing the Governance Scorecard and Model Card links.
* **Spoken Pitch:**
  > *"We built Munzir with Responsible AI at its core. Our codebase includes Mitchell-compliant Model Cards, Gebru Datasheets for all 5 feeds, a full UAE PDPL DPIA, and 7 automated runtime safety controls.*  
  > *If any ML component fails, the engine automatically falls back to deterministic CDC EARS C2 algorithms. Our small-cell suppression enforces k ≤ 10, and worker IDs are dropped at the edge — guaranteeing zero PII."*

---

### Segment 10 (06:40 – 07:00): The Ask — 12-Week Shadow-Mode Pilot
* **Visual:** Slide 10: "From Hackathon to Impact" — Pilot timeline and partner logos.
* **Spoken Pitch:**
  > *"Munzir is completely packaged, containerized, and deployed with zero idle cost on Azure for Students. It exports standard HL7 FHIR R4 MeasureReports ready for DHA NABIDH and Malaffi integration.*  
  > *Our ask today is simple: a **12-week operational shadow-mode pilot** across one district health office and 4 infrastructure employers this summer. Let us prove that with Munzir, we can predict, protect, and prevent before the heat strikes.*  
  > *Thank you, and we welcome your questions."*

