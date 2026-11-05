# Data Protection Impact Assessment (DPIA) & Privacy Architecture

**Document Version:** 2.0  
**Last Updated:** November 2026  
**Regulatory Alignment:** UAE Federal Decree-Law No. 45 of 2021 regarding Personal Data Protection (PDPL), India DPDP Act 2023, GDPR (Articles 25, 35, 89)

---

## 1. Executive Summary & Processing Context

PRAHARI is a multi-signal population and occupational health surveillance engine designed to detect emergent environmental illness surges, localized communicable clusters, and hazardous occupational exposure spikes with advance lead time.

The system processes **zero direct personal identifiable information (PII)** and operates under a strict **privacy-by-design** and **privacy-by-default** mandate.

---

## 2. Data Flow Architecture & Privacy Boundaries

```
[External Sources]
  ├── Open-Meteo & OpenAQ ──► [Zero Personal Data] ───────────────────┐
  ├── Emergency Dept Feeds ─► [District Aggregations Only] ───────────┼──► [Bronze Lakehouse]
  ├── Community Pharmacy ───► [District Retail Totals] ───────────────┤    (No PII Retained)
  └── Workplace EHS Logs ───► [Adversarial PII Scrubber] ─────────────┘
                                     │
                                     ▼
                      [Phase 2: Privacy Transformation]
                        ├── Small-Cell Suppression (k <= 10)
                        ├── Complementary Suppression
                        ├── OpenDP Calibrated Laplace Mechanism (ε = 1.0)
                        └── Minimum Group Size (N >= 50) + Rates Only
                                     │
                                     ▼
                         [Silver Harmonised Store]
                                     │
                                     ▼
                        [Phase 5: Role-Gated API]
       ┌─────────────────────────────┼─────────────────────────────┐
       ▼                             ▼                             ▼
[Surveillance Officer]     [Occupational Employer]          [Public Portal]
Full District Epidemiological   Rate-Only Per 1,000       Differentially Private
Evidence & Cluster Outlines    (Clinical Access 403)     District-Level Aggregates
```

---

## 3. Detailed Privacy Risk Assessment & Technical Controls

| # | Identified Privacy Risk | Likelihood | Impact | Technical & Organizational Safeguard | Verification Test |
|---|---|---|---|---|---|
| **R1** | **Re-identification via small cell counts** in low-density districts | Medium | High | **Small-Cell Suppression ($k \le 10$):** Suppresses any count between 1 and 10 in outward views. **Complementary Suppression:** Prevents mathematical derivation from marginal sums. | [`test_suppression.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_suppression.py) |
| **R2** | **Singling out vulnerable workers** in small worksite cohorts | High | High | **Minimum Workforce Threshold ($N \ge 50$):** Worksites with $<50$ workers are entirely masked. Only rates per 1,000 are rendered; raw headcounts prohibited. | [`test_api_rbac_privacy.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_api_rbac_privacy.py) |
| **R3** | **Inadvertent PII in safety incident narratives** | Medium | Medium | **Automated PII Scrubber:** Regex patterns and entity recognition mask worker names, UAE Civil IDs, passport numbers, phones, and emails before NLP ingestion. | [`test_nlp_classifier.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_nlp_classifier.py) |
| **R4** | **Employer micro-surveillance & disciplinary misuse** | High | Critical | **Architectural RBAC Lockout:** Employer roles attempting to query clinical syndromic data, other employer sites, or sub-site gangs receive immediate **HTTP 403 Forbidden**. Mandatory statutory banner enforced on all views. | [`test_api_rbac_privacy.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_api_rbac_privacy.py) |
| **R5** | **Public stigmatization of industrial zones** | Medium | Medium | **OpenDP Laplace Differential Privacy ($\epsilon = 1.0$):** Public portal injects calibrated Laplacian noise, obscuring exact counts while preserving directional trend utility. | [`test_differential_privacy.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_differential_privacy.py) |
| **R6** | **Unauthorized data access or audit tampering** | Low | High | **Immutable Parquet Audit Trail:** Every view and action query is logged to append-only Gold storage with user identity, role, timestamp, endpoint, and purpose. | [`test_api_views.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_api_views.py) |

---

## 4. Statutory Legal Grounding & Prohibited Uses

### Statutory Basis:
1. **UAE Federal Decree-Law No. 45 of 2021 (PDPL):**
   - *Article 5 (Principles of Personal Data Protection):* Data minimization, purpose limitation, and storage limitation.
   - *Article 6 (Exemptions for Public Health & Scientific Research):* Processing aggregated anonymized data for national health defense and epidemic prevention.
2. **UAE Ministerial Resolution No. 44 of 2022 on Occupational Health and Safety:**
   - Mandating protective work-rest cycles during high thermal stress (midday work ban: 12:30–15:00).
3. **Federal Decree-Law No. 33 of 2021 (Labour Relations):**
   - *Article 13:* Employer obligations to provide occupational health safeguards without using health data punitively.

### Prohibited Uses Statement:
- **Individual Disciplinary Action:** Strictly prohibited from evaluating individual worker attendance or performance.
- **Insurance Underwriting:** Prohibited from commercial premium adjustments or coverage denials.
- **Autonomous Sanctions:** Advisory decision support only; zero automated punitive measures.
