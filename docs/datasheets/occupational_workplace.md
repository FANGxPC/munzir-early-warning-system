# Datasheet for Dataset: Occupational Workplace Health & Absence Surveillance Feed

**Version:** 1.0  
**Last Updated:** November 2026  
**Standards Alignment:** Gebru et al. (2021) *Datasheets for Datasets*

---

## 1. Motivation
- **Purpose:** Ingest daily aggregate sick leaves, unscheduled absences, and free-text safety incident classifications across industrial, maritime, and construction sites to provide the earliest frontline signal of thermal and environmental illness.
- **Created by:** Employer occupational health reporting module conforming to UAE MOHRE statutory reporting standards.
- **Funded by:** Employer health and safety consortium / Munzir platform.

---

## 2. Composition
- **Variables Ingested:**
  - `workforce_size`: Total active workforce at the designated site (must be $\ge 50$ to avoid suppression).
  - `absence_heat`: Count of unscheduled absences categorized under thermal distress or heat exhaustion.
  - `absence_resp`: Count of unscheduled absences attributed to acute cough, asthma, or respiratory symptoms.
  - `absence_general`: Baseline unscheduled sick leave.
  - `incident_narrative`: Free-text safety log entries scrubbed of all PII.
- **Derived Metrics:**
  - `absence_rate_per_1000`: Normalized sick leave rate per 1,000 workers ($(\text{count} / \text{workforce}) \times 1000$).
  - `nlp_incident_tag`: ML-classified category (`heat_exhaustion`, `respiratory_irritation`, `chemical_fume`, `enteric_foodborne`, `unrelated_trauma`).

---

## 3. Privacy Safeguards & Misuse Prevention
- **Workplace Minimum Cohort Policy:** Sites with $N < 50$ workers are completely suppressed from outward rendering to prevent singling out individuals.
- **Rate-Only Views:** Employer dashboards render only rates per 1,000 workers; raw counts and individual worker lists are architecturally prohibited.
- **No Sub-Site Gang / Shift Disaggregation:** Prohibits breakdowns by specific subcontractor, gang roster, or work shift.
- **Mandatory Statutory Banner:** All employer views mandate the banner:  
  *“Aggregate data — not for individual employment or disciplinary decisions.”*
- **Adversarial PII Redaction:** Pre-ingestion scrubbing removes worker names, UAE Civil ID numbers, passport numbers, mobile numbers, and site foreman names.

---

## 4. Collection Process
- **Mechanism:** Daily automated aggregation from enterprise EHS systems and clinic logs at 18:00 GST.
- **Storage:** Persisted to Bronze Parquet partition lakehouse (`data/bronze/workplace/`).

---

## 5. Uses & Out-of-Scope Uses
- **Intended Use:** Proactive worksite hydration staging, work-rest cycle adjustments, ACGIH heat-stress compliance, and early sentinel detection ahead of clinical hospital surges.
- **Out-of-Scope Uses:** Performance management, sick leave validation, employee disciplinary measures, termination, or wage docking.

---

## 6. Known Biases & Limitations
- **Shift Patterns:** Rotating shifts and Friday rest days introduce structural seasonality that requires day-of-week GLM harmonic adjustments.
- **Reporting Quality:** Sites with dedicated full-time occupational nurses report higher initial incidence rates due to greater diagnostic surveillance vigilance.

