# Datasheet for Dataset: Community Pharmacy Sales & Diagnostic Lab Surveillance Feed

**Version:** 1.0  
**Last Updated:** November 2026  
**Standards Alignment:** Gebru et al. (2021) *Datasheets for Datasets*

---

## 1. Motivation
- **Purpose:** Capture pre-clinical self-medication trends (over-the-counter sales of oral rehydration salts, antiemetics, antipyretics, and bronchodilators) alongside confirmatory molecular laboratory test positivity rates.
- **Created by:** Community pharmacy retail networks and licensed private pathology laboratories in Dubai.
- **Funded by:** Commercial surveillance data sharing agreements / Munzir platform.

---

## 2. Composition
- **Variables Ingested:**
  - `otc_rehydration`: Sales volume of oral rehydration solutions (ORS) and electrolyte powders.
  - `otc_antipyretic`: Sales of paracetamol and ibuprofen formulations.
  - `otc_antiemetic`: Sales of antiemetic and anti-diarrheal remedies.
  - `lab_pos_enteric`: Positive diagnostic laboratory confirmations for acute gastrointestinal pathogens (Salmonella, Shigella, Norovirus).
  - `lab_pos_resp`: Confirmatory molecular PCR positivity for respiratory viral panels (Influenza A/B, RSV, SARS-CoV-2).
- **Aggregation Level:** District-level sales and test volume summaries.
- **Privacy Protections:** Small-cell suppression ($k \le 10$) and absolute zero personal identifiers.

---

## 3. Collection Process
- **Mechanism:** Daily midnight batch SFTP export from pharmacy management systems and laboratory information management systems (LIMS).
- **Storage:** Persisted to Bronze lakehouse (`data/bronze/pharmacy_lab/`).

---

## 4. Preprocessing & Cleaning
- **Normalization:** Pharmacy sales are indexed against a 30-day trailing baseline median to prevent weekend restocking distortions.
- **Test Volume Normalization:** Laboratory positivity is calculated as a proportion of total specimens tested ($% \text{ positive}$) to adjust for testing volume fluctuations.

---

## 5. Uses & Out-of-Scope Uses
- **Intended Use:** Multi-signal corroboration in L4 fusion model and differentiation of true biological outbreaks from administrative reporting artifacts.
- **Out-of-Scope Uses:** Commercial retail market share tracking, brand-specific sales analysis, or prescription tracking.

---

## 6. Known Biases & Limitations
- **Promotion & Stockout Artifacts:** Pharmacy retail discounts or supply chain delays can create sudden purchasing surges or dips unrelated to illness incidence.
- **Testing Delays:** Turnaround times for specialized enteric stool cultures (48–72 hours) mean laboratory confirmations serve primarily as confirmatory rather than early warning signals.

