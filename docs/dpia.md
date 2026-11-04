# PRAHARI Lightweight Data Protection Impact Assessment (DPIA)

## 1. Context & Purpose
PRAHARI is an automated early-warning surveillance engine for public and workforce health. Its objective is to detect population-level health aberrations and workplace safety clusters (heat stress, respiratory pollution surges, point-source contamination) with maximum lead time.

## 2. Data Flow & Boundary
```
[External Sources] -> [Edge Sanitization & Pre-Aggregation] -> [Bronze Parquet Lakehouse] -> [Silver Aggregations]
```
- No patient medical records or identifiable human HR profiles enter the PRAHARI analytics boundary.
- Clinical records are acquired strictly as pre-aggregated syndromic counts (e.g. total acute respiratory distress cases per district hospital per day).
- Workplace sick leaves are pre-aggregated by reason code per site.
- Free-text incident safety logs are scrubbed via PII masking before classification.

## 3. Privacy Risks & Technical Safeguards

| Privacy Risk | Severity | Technical Safeguard |
|---|---|---|
| Re-identification of rare conditions in small communities | High | **Small-Cell Suppression ($k \le 10$):** Cells with 1 to 10 counts are suppressed in outward views; complementary suppression prevents subtraction recovery. |
| Singling out individual workers at small sites | High | **Minimum Workforce Threshold:** Site-level health metrics require a workforce of at least $N \ge 50$. Only aggregate rates (per 1,000 workers) are rendered; individual lists or sub-site teams are prohibited. |
| Inadvertent PII in workplace incident narratives | Medium | **Presidio / Regex Anonymizer:** Automated regex and entity recognizers redact person names, employee IDs, phone numbers, and specific locations before NLP tagging. |
| Scope creep into individual employment decisions | High | **Architectural & Policy Barrier:** RBAC prevents employers from viewing clinical data or sub-site clusters; audit logs capture every access query; prohibited-use policy legally bounds usage. |

## 4. Alignment with Global Privacy Standards
The design aligns with the principles of the **India DPDP Act 2023** (purpose limitation, data minimization) and **GDPR Article 89** (safeguards for processing for public interest / scientific research).

