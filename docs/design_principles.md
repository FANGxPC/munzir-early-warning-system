# PRAHARI Design Principles & Architecture Manifesto

PRAHARI (Population & Workforce Health Early Warning System) is built on foundational engineering and epidemiological principles designed to guarantee actionability, fairness, and safety.

## 1. Aggregate-First (Zero Person-Level Identifiers)
- No person-level identifiers (names, patient IDs, national IDs, employee badges, phone numbers, exact residential addresses) are ever collected, stored, or processed in the analytics tier.
- All clinical and workplace observations are pre-aggregated to spatial units (Site, H3 Resolution 6/7 Hexagons, or District) and temporal units (daily counts).
- Any incident narrative text ingested must pass through automated sanitization / PII scrubbing before classification or persistence.

## 2. Layered Epidemiological Detection (Calibrated, Not Black-Box)
- Outbreak and anomaly detection is structured into 5 defensive layers (L1–L5):
  - **L1**: Per-signal public-health aberration algorithms (CDC EARS C1, C2, C3 and Farrington-flexible).
  - **L2**: Exposure-adjusted baselines (isolating weather/pollution-induced changes from unexplained biological clusters).
  - **L3**: Prospective space-time permutation cluster scan (Kulldorff-style).
  - **L4**: Machine learning fusion producing calibrated probabilities ($P \in [0, 1]$) with uncertainty intervals.
  - **L5**: Policy gates (hysteresis, multi-signal corroboration, deduplication, alert budgets).
- Black-box alarms are strictly prohibited. Every alert must provide explicit signal contribution breakdowns and SHAP values.

## 3. Data Quality & Missing-Data Transparency
- Every incoming signal carries explicit data quality metadata:
  - `completeness_score`: Proportion of expected reporting entities active.
  - `source_latency_hrs`: Time elapsed between event date and system ingestion.
- The system must degrade gracefully: when feeds drop out or report incomplete counts, alerts are flagged with "Low Confidence — Missing Feed" and severity is capped, rather than firing false alarms or going completely silent.

## 4. Actionability & Accountability (RACI Framework)
- Alerts are never raw numbers; they are decision triggers mapped to structured playbooks.
- Every alert type and severity level has an explicit RACI (Responsible, Accountable, Consulted, Informed) assignment to a defined human role (e.g., Site Safety Officer, District Surveillance Officer).
- Proportionality is enforced: early weak signals prompt verification and low-cost preventive measures; invasive actions require multi-signal corroboration.

## 5. Misuse Resistance & Responsible AI
- Hard technical boundaries prevent the system from being used for individual employee tracking, disciplinary actions, performance reviews, or discriminatory insurance decisions.
- Site-level views enforce a minimum workforce group size ($N \ge 50$) and render only rates, never sub-site breakdowns or individual lists.
- Generative AI / LLM components are strictly fenced: used exclusively to rephrase structured alert JSON into readable briefings, with deterministic template fallback and automated numerical verification.

