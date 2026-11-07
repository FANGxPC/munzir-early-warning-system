# Munzir (منذر) — 5–6 Minute Championship Demo Script & Pitch Cue Sheet

> **Presenter Cue Sheet:** Dubai International Hackathon Grand Jury Final  
> **Target Duration:** 5 minutes 30 seconds (leaving 30s buffer for a 6-minute hard limit)  
> **Protagonists:**  
> 1. **Dr. Aisha Al-Maktoum** — Lead Epidemiologist, Dubai Health Authority (DHA Public Health Directorate)  
> 2. **Tariq Mansoor** — Senior EHS & Site Safety Officer, Jebel Ali Industrial Port Logistics Yard  
> **Live URL:** `http://localhost:8000` (or live Azure Container App endpoint)  
> **Operator Pre-Flight Checklist:**  
> 1. Dashboard Tab: `http://localhost:8000` (logged into District Surveillance Officer view)  
> 2. Validation Tab: `validation/report.html` (Empirical Back-Test Proof)  
> 3. Sentinel Hardware Node: ESP32 with matte-black globe DHT22 sensor, active buzzer, and RGB LED on the presenter table (or `make sentinel-replay` fallback)  
> 4. Test Suite Verified: 143/143 tests passing  

---

## Pitch Cue Sheet Timeline

```
00:00 - 00:50  ACT I: THE SILO & THE STORM (Dr. Aisha's Blindspot in August)
00:50 - 01:40  SCENE 1: Baseline Calm & The Fast-Forward Clock
01:40 - 02:50  ACT II: THE CONVERGENCE & THE FLOOR (Tariq's 3.4-Day Advance Warning)
02:50 - 03:30  SCENE 2: The Physical Sentinel (Audible Buzzer & Worksite Acknowledgement)
03:30 - 04:10  SCENE 3: The Differentiator — Foodborne Pathogen vs Environmental Heat
04:10 - 04:50  ACT III: RESILIENCE PROOF & REGULATORY CERTAINTY (Live Feed Fault Injection)
04:50 - 05:20  SCENE 4: Empirical Back-Test Proof (92.4% Sensitivity, 88.5% PPV, 143 Tests)
05:20 - 05:50  SCENE 5: Macro Economic ROI (AED 1.86M Net Benefit & 758x BCR)
05:50 - 06:00  THE ASK: 12-Week Operational Shadow-Mode Pilot
```

---

### ACT I: THE SILO & THE STORM (00:00 – 00:50)

* **Visual:** Slide 1 / Title Screen — Munzir: Calibrated Early-Warning Platform for Population & Workforce Health Resilience.
* **Characters Introduced:** Dr. Aisha Al-Maktoum (DHA) and Tariq Mansoor (Jebel Ali Port).
* **Spoken Pitch:**
  > *"Judges, picture August 15th in Dubai. Ambient temperatures hit 46°C with 78% coastal humidity.*  
  > *Meet **Dr. Aisha Al-Maktoum**, Lead Epidemiologist at the Dubai Health Authority. She monitors population disease trends, but her hospital registries arrive with a 7-day reporting lag.*  
  > *Thirty kilometers away at Jebel Ali Port, meet **Tariq Mansoor**, Site Safety Officer responsible for 1,200 container yard workers. Tariq checks the daily national weather forecast: it says 41°C. But down on the asphalt between steel freight containers, radiant heat is pushing wet-bulb globe temperature past 33°C.*  
  > *By the time Dr. Aisha notices a heat-exhaustion cluster in emergency department admissions next week, Tariq has already sent six workers to intensive care with heat stroke.*  
  > *Retrospective reporting is not surveillance — it is an autopsy.*  
  > *This is **Munzir (منذر)** — Arabic for 'the warner'. Munzir fuses environmental, syndromic, and workplace telemetry into a privacy-preserving early-warning system that connects Dr. Aisha's regional vigilance directly to Tariq's work floor — **3.4 days before peak hospital impact**."*

---

### SCENE 1: BASELINE CALM & THE FAST-FORWARD CLOCK (00:50 – 01:40)

* **Visual:** Switch to live dashboard (`http://localhost:8000`). Show clean, calm map of Dubai and Northern Emirates with green baseline indicators.
* **Click Action:** Click the date selector to `2025-08-15` (Baseline Quiet Day −5). Show the Entra ID role selector set to `District Surveillance Officer`.
* **Spoken Pitch:**
  > *"Here is Munzir running live in production. On quiet days, Dr. Aisha sees a serene map. The baseline rate of syndromic presentations is nominal, air quality sensors across OpenAQ report moderate PM2.5, and work absences are steady.*  
  > *Notice the Role Switcher at the top right: Munzir provides 6 distinct Entra ID role-based perspectives. Dr. Aisha sees district epidemiological patterns; employers see aggregated rates with zero PII; frontline supervisors see operational safety cues.*  
  > *Now, let’s advance the simulation clock from August 15th forward to August 18th. A regional high-pressure system descends over the Persian Gulf. Watch how Munzir transforms data into targeted early action."*

---

### ACT II: THE CONVERGENCE & THE FLOOR (01:40 – 02:50)

* **Visual:** Map highlights `SITE-JA-01` (Jebel Ali Port Logistics) and `DXB-JA` turning amber-orange (*Warning* tier).
* **Click Action:** Click on the alert badge in the Alert Inbox to trigger the **Evidence Card modal**.
* **Spoken Pitch:**
  > *"Look at the map. Three full days before any hospital ICU admission, Munzir flags Jebel Ali Port with an actionable Warning alert.*  
  > *Dr. Aisha clicks to open the **Decision-Ready Evidence Card**:*  
  > *1. **Calibrated Probability:** 83.3% risk of an occupational heat cluster, bound by a rigorous 90% conformal prediction interval.*  
  > *2. **Explainable SHAP Attribution:** It's not a black box. The model reveals that 44% of the signal is driven by extreme wet-bulb globe temperature exposure exceeding 32°C for over 4 continuous hours, compounded by a 32% sudden rise in unexcused morning absenteeism.*  
  > *3. **Legally Grounded RACI Action:** Look at the playbook below. This is not generic advice. It cites **UAE Ministerial Resolution No. 44 of 2022** on Occupational Safety, assigning Tariq Mansoor as the Accountable Officer to implement mandatory 15-minute shaded rest rotations, deploy electrolyte hydration stations, and pause crane operations during peak solar exposure.*  
  > *Now, watch what happens when we switch to the Employer View: instantly, all individual clinical identifiers vanish. Tariq gets operational safety directives without infringing on worker privacy."*

---

### SCENE 2: THE PHYSICAL SENTINEL — AUDIBLE BUZZER & WORKSITE ACKNOWLEDGEMENT (02:50 – 03:30)

* **Visual:** Switch to the **🔧 Sentinel Hardware** tab on the dashboard, drawing jury attention to the physical ESP32 node on the table.
* **Demonstration Action:**
  1. Click `⚡ Sample Telemetry` to push the current Jebel Ali microclimate reading.
  2. The physical ESP32 on the table emits an **audible double-pulse warning buzz** (`1000Hz -> 1500Hz`) and pulses its amber LED.
  3. Presenter physically presses the **BOOT button** on the ESP32: the buzzer immediately silences, the LED flashes cyan, and a live non-repudiation log entry appears in the web UI: `ACKNOWLEDGED by On-Site Supervisor Tariq Mansoor`.
* **Spoken Pitch:**
  > *"Software dashboards are useless if the safety officer is walking the container yard without a laptop. That is why we built **Munzir Sentinel** — an ultra-low-cost, solar-ready ESP32 edge node.*  
  > *While regional Open-Meteo weather models report 31.8°C WBGT, our on-site Sentinel measures the true steel-deck microclimate: **33.4°C WBGT**!*  
  > *The moment Munzir calculates a Warning tier, the Sentinel node triggers this audible alert and amber LED right on the work floor.*  
  > *When Tariq presses this physical button on the node, it instantly silences the buzzer and transmits an immutable cryptographic acknowledgement back to DHA and MOHRE, proving regulatory compliance in real time."*

---

### SCENE 3: THE DIFFERENTIATOR — FOODBORNE PATHOGEN VS ENVIRONMENTAL HEAT (03:30 – 04:10)

* **Visual:** Select the alert for `SITE-AQ-01` (Al Quoz Industrial Canteen) on the dashboard map.
* **Click Action:** Show the Evidence Card highlighting "Zero Environmental Contribution".
* **Spoken Pitch:**
  > *"Here is what proves Munzir is not just another threshold alarm: our Layer 2 exposure-response engine.*  
  > *In August, sickness absence always rises when temperature rises. If an alarm sounds every hot day, officers get alert fatigue and turn it off.*  
  > *Look at Scenario 3 in Al Quoz: ambient temperature is normal, PM2.5 is normal, yet gastrointestinal clinic visits spike 4.8x.*  
  > *Munzir isolates the residual from the environmental baseline and classifies this not as heat stress, but as an **'Unexplained Infectious Cluster'**. Instead of ordering water misting, it directs Dr. Aisha's Rapid Response Team to inspect the worker canteen for contaminated water. That is true clinical differentiation."*

---

### ACT III: RESILIENCE PROOF & REGULATORY CERTAINTY (04:10 – 04:50)

* **Visual:** Scroll to the **Data Quality & What-If Sandbox** panel.
* **Click Action:** Toggle off the **Hospital Clinical Feed** switch to simulate a catastrophic regional EHR network failure.
* **Spoken Pitch:**
  > *"In a real-world crisis, data feeds fail. Watch what happens when I simulate a complete outage of the regional hospital syndromic feed.*  
  > *Does Munzir crash? No. Does it hallucinate a false alarm? No.*  
  > *Look at the conformal confidence band: it immediately widens from ±10% to ±25%. The Data Quality index drops to 0.58, and our safety guardrail caps the alert tier at Warning, flagging: 'Clinical feed unavailable — uncertainty bounds expanded'.*  
  > *And when private clinics upload a 5-day delayed backlog of 50 visits in a single batch, Munzir’s decoy filter recognizes the timestamp clustering as an administrative backlog and suppresses the false alarm with a 94.0% filter rate."*

---

### SCENE 4: EMPIRICAL BACK-TEST PROOF (04:50 – 05:20)

* **Visual:** Switch tab to `validation/report.html`. Show the multi-year back-test table and Activity Monitoring Operating Characteristic (AMOC) curve.
* **Spoken Pitch:**
  > *"We don't ask the jury to take our word for it. Every performance metric in Munzir is empirically back-tested across 100 hold-out outbreak injections and verified by our **143-test automated test suite**:*  
  > *• **3.40 Days** operational advance lead time.*  
  > *• **92.4% Detection Sensitivity** across industrial and community sectors.*  
  > *• **88.5% Positive Predictive Value** (Precision).*  
  > *• **0.31 False Alarms per site per month** — a 76% reduction in alert fatigue.*  
  > *Any evaluator can clone our repository and run `make validate SEED=42` right from terminal to reproduce every single figure deterministically."*

---

### SCENE 5: MACRO ECONOMIC ROI & THE ASK (05:20 – 06:00)

* **Visual:** Switch to the **Impact Model** tab on the dashboard. Drag the cohort slider to 50,000 workers.
* **Click Action:** Point to the Net Economic Benefit: **AED 1,861,996** and **758:1 Benefit-Cost Ratio**.
* **Spoken Pitch:**
  > *"What is the bottom line for Dubai? Across a cohort of 50,000 industrial workers, calibrated early intervention prevents:*  
  > *• **3,480 lost workdays** saved per summer.*  
  > *• **25 severe ICU heat strokes** prevented.*  
  > *• **AED 1.86 Million in net economic savings**, delivering an extraordinary **758-to-1 return on investment**.*  
  > *Munzir is deployed on Azure Container Apps with $0.00 idle cost, exports standard **HL7 FHIR R4** bundles for DHA NABIDH and Malaffi, and passes all 7 Responsible AI governance guardrails.*  
  > *Our ask today is a **12-week operational shadow-mode pilot** across Dubai Health Authority and 4 major industrial employers this summer. Let us give Dr. Aisha and Tariq the tools to protect Dubai’s workforce before the next heatwave.*  
  > *Predict. Protect. Prevent. Thank you, and we welcome your questions."*

---

## Technical Appendix: Demo Action Cheat-Sheet

| Timestamp | Screen / Interface | Trigger Action | Expected Visual / Physical Output |
| :--- | :--- | :--- | :--- |
| **00:55** | Web Dashboard | Set Date to `2025-08-15` | Clean green map, quiet baseline metrics |
| **01:45** | Web Dashboard | Advance Date to `2025-08-18` | `SITE-JA-01` turns Orange (*Warning*) |
| **02:00** | Alert Inbox | Click Warning Badge | Evidence Card opens with SHAP attribution & RACI Playbook |
| **02:35** | Role Switcher | Toggle `Employer View` | All PII stripped, rate-only metrics displayed |
| **02:55** | Sentinel Tab | Click `⚡ Sample Telemetry` | Physical ESP32 buzzes (double-pulse), amber LED blinks |
| **03:15** | Hardware Node | Press physical **BOOT button** | Buzzer mutes, cyan LED flash, non-repudiation audit logged |
| **03:40** | Web Dashboard | Select `SITE-AQ-01` | Evidence Card highlights "Unexplained Infectious Cluster" |
| **04:15** | Sandbox Panel | Toggle OFF "Clinical Feed" | Conformal interval widens to ±25%, Data Quality drops to 0.58 |
| **04:55** | Validation Tab | Open `validation/report.html` | AMOC curve, 92.4% sensitivity, 88.5% PPV, 143 tests |
| **05:25** | Impact Tab | Workforce Slider = 50,000 | AED 1,861,996 Net Benefit, 758:1 BCR |
