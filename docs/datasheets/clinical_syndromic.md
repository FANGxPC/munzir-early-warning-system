# Datasheet for Dataset: Pre-Aggregated Clinical Syndromic Surveillance Feed

**Version:** 1.0  
**Last Updated:** November 2026  
**Standards Alignment:** Gebru et al. (2021) *Datasheets for Datasets*

---

## 1. Motivation
- **Purpose:** Monitor daily counts of syndromic emergency department and ambulatory health facility presentations (respiratory, gastrointestinal, systemic febrile, acute heat distress) to detect community outbreaks before laboratory confirmation.
- **Created by:** Simulated health authority telemetry (DHA/MoHAP canonical format) calibrated against published epidemiological surveillance distributions.
- **Funded by:** PRAHARI public health surveillance initiative.

---

## 2. Composition
- **Variables Ingested:**
  - `clinical_resp`: Acute upper and lower respiratory presentations (cough, dyspnea, wheezing).
  - `clinical_gi`: Acute gastroenteritis presentations (emesis, diarrhea, abdominal cramps).
  - `clinical_fever`: Febrile illness without localizing symptoms.
  - `clinical_heat`: Acute heat exhaustion, heat syncope, and hyperthermia presentations.
- **Aggregation Level:** District-level aggregates (`district_id`, `date`).
- **Privacy Protections:**
  - **Zero individual patient records:** System never receives patient names, national IDs, medical record numbers, or addresses.
  - **Small-Cell Suppression:** Counts $1 \le count \le 10$ are suppressed ($k \le 10$) in outward and cross-sector views.
  - **Differential Privacy:** OpenDP Laplace mechanism ($\epsilon = 1.0$) applied to public releases.

---

## 3. Collection & Simulation Methodology
- **Statistical Model:** Negative binomial baseline distributions ($Y \sim \text{NB}(\mu, \alpha)$) capturing overdispersion and day-of-week reporting seasonality (weekend dips, Sunday surges).
- **Lagged Exposure Linkage:** Non-linear exposure-response functions linking WBGT to `clinical_heat` (lag 0–1 days) and $\text{PM}_{2.5}$ to `clinical_resp` (lag 1–3 days).
- **Simulated Reporting Latency:** Injected reporting delays reflecting real-world hospital EMR batch transmission (mean delay: 1.2 days).

---

## 4. Uses & Out-of-Scope Uses
- **Intended Use:** L1 temporal aberration detection (CDC EARS C1–C3, Farrington GLM), L3 space-time cluster scanning, and L4 multi-signal machine learning fusion.
- **Out-of-Scope Uses:** Clinical diagnosis of individual patients, tracking patients across hospital networks, or tracing individual contacts.

---

## 5. Known Biases & Limitations
- **Health-Seeking Behavior:** Expatriate outdoor workers may under-report mild heat exhaustion to formal hospitals, presenting instead to on-site employer clinics.
- **Reporting Delays:** Batch uploads from private clinics on weekends cause synthetic spikes on subsequent business days (managed by L5 backlog dump suppression).

