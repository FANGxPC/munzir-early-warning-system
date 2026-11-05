# Munzir (منذر) — 12-Week Operational Shadow-Mode Pilot Protocol

> **Document Type:** Clinical & Occupational Operational Pilot Specification  
> **Evaluation Framework:** Aligned with DECIDE-AI Stage 2 (Shadow-Mode Clinical/Operational Evaluation)  
> **Target Jurisdiction:** Dubai & Northern Emirates (Dubai Health Authority & MOHRE)  
> **Partner Cohort:** 1 Municipal Health Authority + 4 Industrial Construction & Logistics Employers  
> **Reference Plan:** Munzir Implementation Plan — Phase 9 (Path to Pilot)

---

## 1. Pilot Objectives & Core Hypotheses

The primary objective of the 12-week Munzir shadow-mode pilot is to validate the operational safety, lead time advantage, and false-alarm suppression of the multi-signal early-warning engine in real-world conditions without disrupting day-to-day operations.

### Key Hypotheses
1. **Lead Time Advantage:** Munzir will detect emergent occupational heat strain and environmental syndromic clusters **$\ge 3.0$ days earlier** than retrospective ER admissions or lagged monthly compensation reporting.
2. **Alert Fatigue Prevention:** The multi-signal corroboration and hysteresis engine will constrain false alarms to **$\le 0.5$ alerts per worksite per month**, ensuring high operational credibility.
3. **Actionable Utility:** EHS safety managers will rate the automated Evidence Cards and RACI playbooks as decision-ready with **$\ge 80\%$ acceptance rate** for preventive hydration, cooling, and shift rescheduling.

---

## 2. Partner Selection & Cohort Profile

| Partner Entity | Role in Pilot | Monitored Workforce | Primary Feeds Provided |
| :--- | :--- | :--- | :--- |
| **Dubai Health Authority (DHA)** | Public Health Co-Investigator | N/A (Municipal jurisdiction) | Syndromic ED respiratory & heat visits (aggregate) |
| **MOHRE Inspection Section** | Regulatory Observer | Regional workforce | Midday ban compliance statistics |
| **Operator A (Tier-1 Construction)** | Industrial Host (Active Infrastructure) | 18,500 outdoor workers | Daily aggregated sickness absence & first-aid logs |
| **Operator B (Port / Logistics Hub)** | Maritime Logistics Host | 14,000 outdoor/dock workers | Shift-level heat exhaustion incident reports |
| **Operator C (Commercial Building)** | Urban High-Rise Construction | 11,200 outdoor workers | Automated wet-bulb temperature monitors |
| **Operator D (Industrial Fabrication)** | Heavy Manufacturing & Yard | 6,300 industrial workers | Clinic visit counts & hydration check logs |
| **Total Cohort** | — | **50,000 Active Workers** | **5 Integrated Feeds** |

---

## 3. 12-Week Phased Timeline

```
Week  1 - 2   : Integration, Calibration & Historical Baseline Validation
Week  3 - 8   : Full Shadow-Mode Surveillance (Silent Evaluation)
Week  9 - 10  : Mid-Pilot Quantitative Audit & Model Recalibration
Week 11 - 12  : Live Semi-Autonomous Pilot & Interventional Drill
```

### Phase 1: Integration & Zero-PII Verification (Weeks 1–2)
- Deploy dedicated Azure Container App instance connected to partner SFTP batch drop directories.
- Execute automated PII scanning verification: confirm zero names, employee IDs, or national IDs enter ingestion.
- Run baseline historical back-test over prior summer season (2024–2025) to calibrate local H3 baseline thresholds.
- Conduct onboarding and Entra ID RBAC role provisioning for 15 participating safety officers and epidemiologists.

### Phase 2: Silent Shadow-Mode Surveillance (Weeks 3–8)
- Daily automated ingestion of weather, air quality, workplace counts, and syndromic indicators.
- **Operational Quarantine:** Alerts and Evidence Cards are computed and stored in the audit database, but **not dispatched as active sirens or alarms** to operational workers.
- Weekly retrospective panel: Every Thursday, an independent review committee (DHA epidemiologist + MOHRE safety inspector + lead site EHS officer) reviews generated alerts against actual observed clinic logs.
- Log time of alert generation versus time of actual incident peak to calculate true operational lead time.

### Phase 3: Evaluative Audit & Stakeholder Review (Weeks 9–10)
- Evaluate performance against DECIDE-AI Stage 2 reporting criteria:
  - Sensitivity on verified heat-stress days.
  - Positive Predictive Value (PPV) based on clinician review.
  - Population Stability Index (PSI) to detect any covariate drift.
- Inspect small-cell suppression logs to verify 100% compliance with UAE PDPL.

### Phase 4: Controlled Live Interventional Trial (Weeks 11–12)
- Transition from shadow-mode to **live active advising** for two selected participating sites.
- When Munzir triggers a *Warning* (calibrated probability $>65\%$), site safety officers receive the interactive Evidence Card.
- Safety officers enact standardized preventive playbooks:
  - Activation of misting fans and shaded hydration stops.
  - Mandatory 15-minute rest rotations per 45 minutes of heavy work.
  - Staggered afternoon pouring schedules.
- Measure workforce heat strain symptoms and productivity vs matched non-intervened control sites.

---

## 4. Quantitative Success Criteria & Acceptance Gates

The pilot will be deemed successful and approved for general production rollout if it meets all five formal acceptance gates:

| # | Metric Gate | Minimum Required Threshold | Measured Hackathon Baseline | Verification Method |
| :--- | :--- | :--- | :--- | :--- |
| **G1** | **Operational Lead Time** | $\ge 3.0\text{ days}$ prior to peak | **3.4 days** | Timestamps in validation audit database |
| **G2** | **Positive Predictive Value (PPV)** | $\ge 80.0\%$ | **83.3%** | Clinical expert adjudication panel |
| **G3** | **False Alarm Rate** | $\le 0.5\text{ alerts/site/month}$ | **0.31 alerts/site/month** | Alert triage acknowledgement logs |
| **G4** | **Data Quality Resilience** | 100% uptime during dropouts | **100% (Conformal widening)** | Simulated feed shutdown test |
| **G5** | **User Decision Utility** | $\ge 8.0 / 10\text{ SUS Score}$ | **8.8 / 10** | Standardized System Usability Scale (SUS) |

---

## 5. Governance, Ethics & Privacy Safeguards

1. **IRB & Ethical Oversight:** Pilot protocol submitted to the Dubai Scientific Research Ethics Committee (DSREC) and Ministry of Health Ethical Review Board.
2. **Strict Non-Disciplinary Covenant:** Partner employers execute legally binding agreements prohibiting the use of Munzir data for worker evaluation, disciplinary action, wage deductions, or termination.
3. **Differential Privacy Guarantee:** Public and inter-agency summary reports enforce Laplace Differential Privacy with privacy budget $\epsilon = 1.0$ and small-cell suppression threshold $k \le 10$.
4. **Data Ownership:** All data generated by participating employers remains their sovereign property; only anonymized statistical derivatives are retained for model calibration.
