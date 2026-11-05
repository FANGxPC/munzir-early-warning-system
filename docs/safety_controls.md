# PRAHARI Operational Safety Controls & Safeguards Register

**Document Version:** 1.0  
**Last Updated:** November 2026  
**Standards Compliance:** IEC 62304 / ISO 14971 Health Software Risk Management, DECIDE-AI Framework

---

## 1. Safety Architecture Overview

PRAHARI operates a multi-layered safety barrier architecture designed to prevent alert fatigue, eliminate hallucinated decision recommendations, guarantee fail-safe continuity during telemetric outages, and preserve civil liberties.

```
Incoming Telemetry
       │
       ▼
[Control 1: Data Quality Gate] ─────────► Degraded? ──► Widen Conformal Band + Cap Alert Tier
       │ Healthy
       ▼
[Control 2: ML Model Health Check] ─────► Failure?  ──► Rollback to CDC EARS-Only Mode
       │ Passed
       ▼
[Control 3: Corroboration Rule] ────────► Single-Signal? ──► Hard Cap at "Watch" Tier
       │ Corroborated
       ▼
[Control 4: Jurisdictional Alert Caps] ─► Quota Exceeded? ─► Suppress / Consolidate into Digest
       │ Approved
       ▼
[Control 5: Fenced LLM Guardrail] ──────► Discrepancy? ────► Revert to Deterministic Template
       │ Verified
       ▼
[Control 6: Human-in-the-Loop Triage] ──► Mandatory Dismissal Reason & Audit Trail
```

---

## 2. Comprehensive Safety Controls Register

### Control 1: Ingestion Data Quality (DQ) Gating
- **Objective:** Prevent false alarms driven by data artifacts, missing feeds, or transmission dropouts.
- **Enforcement Rule:** If composite data quality falls below threshold ($\text{DQ} < 0.65$) or a primary feed is missing for $>24$ hours:
  1. Conformal prediction uncertainty interval $[P_{\text{lower}}, P_{\text{upper}}]$ is automatically widened.
  2. Maximum alert severity is strictly capped at *Watch* (preventing *Alert* or *Warning* triggering).
  3. UI injects a prominent `LOW_DATA_QUALITY` warning badge.
- **Verification:** [`test_missing_data_demo_toggle_resilience`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_api_views.py).

---

### Control 2: Multi-Signal Corroboration Rule
- **Objective:** Eliminate single-sensor noise and sensor-specific false positives.
- **Enforcement Rule:** A single elevated signal (e.g. thermal spike alone without absence surge, or isolated hospital clinical spike without occupational or pharmacy signal) **can never trigger a Warning or Alert**.
- **Severity Cap:** Single-signal aberrations are hard-capped at the *Watch* advisory tier. Upgrades to *Warning* require $\ge 2$ mutually corroborating signals across materially different data sources.
- **Verification:** [`test_detection_l4_l5.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_detection_l4_l5.py).

---

### Control 3: Dynamic Jurisdictional Alert Caps
- **Objective:** Prevent cognitive overload and alert fatigue among surveillance officers.
- **Enforcement Rule:** Maximum alert budget enforced per district jurisdiction:
  - Maximum **1 active Alert** per district at any time (multi-day surges are merged into an active cluster incident).
  - Maximum **3 Warning alerts per week** per district.
  - Excess alerts are consolidated into a daily surveillance digest rather than triggering push notifications.
- **Verification:** [`test_safety_monitor_alert_caps`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_responsible_ai_governance.py).

---

### Control 4: Fail-Safe Rollback to CDC EARS-Only Mode
- **Objective:** Ensure continuous surveillance capability if advanced ML components encounter runtime exceptions, distribution drift, or inference failures.
- **Enforcement Rule:** The runtime engine continuously monitors ML health:
  1. If LightGBM model weights are corrupted or inaccessible,
  2. If runtime feature schema mismatch occurs, or
  3. If inference execution raises an exception:
  The pipeline **automatically rolls back to CDC EARS C2 baseline aberration detection**, sets `is_fallback_mode=True`, logs the incident to the immutable security audit log, and continues generating baseline aberration alerts without service interruption.
- **Verification:** [`test_safety_monitor_ml_health_check_and_ears_rollback`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_responsible_ai_governance.py).

---

### Control 5: Fenced Zero-Hallucination LLM Guardrail
- **Objective:** Guarantee that generative AI narratives never invent clinical statistics, lead times, or worksite identifiers.
- **Enforcement Rule:** All narrative generation runs through a two-stage verification barrier:
  1. **Strict Regex Numerical Extraction:** Extracts all numbers from the LLM narrative and verifies they match the ground-truth values in the structured Evidence Card.
  2. **Deterministic Fallback:** If any discrepancy, phantom number, or LLM hallucination is detected, the LLM output is rejected and replaced with the deterministic string template.
- **Verification:** [`test_narrative.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_narrative.py).

---

### Control 6: Human-in-the-Loop Triage with Non-Repudiation Audit
- **Objective:** Prevent autonomous algorithmic actions and preserve complete operational accountability.
- **Enforcement Rule:**
  - Alerts can only transition from `PENDING` to `ACKNOWLEDGED`, `ACTED`, or `DISMISSED` via an authenticated human officer.
  - If an alert is `DISMISSED`, the officer is legally required to select a structured operational reason (`benign_local_event`, `data_artefact_backlog`, `already_managed_duplicate`, `false_positive_noise`).
  - Every review action is signed with the user ID, timestamp, and client IP into an append-only Gold Parquet log (`data/gold/audit/view_audit_log.parquet`).
- **Verification:** [`test_acknowledgement.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_acknowledgement.py).

---

### Control 7: Privacy-by-Architecture Barrier
- **Objective:** Prevent re-identification of vulnerable individuals and protect worker rights.
- **Enforcement Rule:**
  - Small-cell suppression ($k \le 10$) with complementary suppression.
  - Minimum worksite cohort $N \ge 50$; rate-only views per 1,000 workers.
  - Prohibition of sub-site gang breakdowns or individual worker lists.
  - Entra ID RBAC blocking employers from viewing clinical syndromic data (HTTP 403).
- **Verification:** [`test_api_rbac_privacy.py`](file:///home/fang/Downloads/Dubai-Hackathon/Prahari/tests/test_api_rbac_privacy.py).

