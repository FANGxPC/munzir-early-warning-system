# Munzir Canonical Data Model (Silver/Gold)

The Munzir analytics layer operates exclusively on pre-aggregated, privacy-preserving observation records.

## 1. Signal Observation Table (`signal_observation`)

| Field | Type | Description |
|---|---|---|
| `signal_id` | string (UUID) | Unique surrogate identifier for the observation |
| `signal_type` | string | Signal category (e.g., `wbgt`, `pm25`, `clinical_resp`, `clinical_gi`, `clinical_fever`, `lab_pos`, `absence_heat`, `workplace_incident`) |
| `geo_level` | string | Spatial aggregation tier: `site`, `h3_res7`, `district`, `state` |
| `geo_id` | string | Spatial identifier (e.g. site code, H3 hex id, district name) |
| `location_confidence` | string | `exact` (precise GPS centroid), `inferred`, or `district_only` |
| `obs_date` | string (YYYY-MM-DD) | Date of observation / aggregation |
| `value` | float | Count of events or physical metric value |
| `denominator` | float | Population or workforce size at risk |
| `ingested_at` | string (ISO-8601) | Timestamp when observation was ingested |
| `source_latency_hrs` | float | Lag between event occurrence and system ingestion |
| `completeness_score` | float | Completeness index (0.0 to 1.0) |
| `suppressed_flag` | boolean | True if cell count is non-zero and below suppression threshold $k \le 10$ |

## 2. Injected Event Truth Table (`injected_event_truth`)

Used exclusively in development, validation, and benchmarking to measure early detection lead times and false-positive rates.

| Field | Type | Description |
|---|---|---|
| `event_id` | string | Unique event ID |
| `scenario_type` | string | `heat_cluster`, `respiratory_surge`, `infectious_cluster`, `decoy_backlog`, `decoy_holiday` |
| `target_geo_id` | string | Target district or site ID |
| `start_date` | string (YYYY-MM-DD) | True onset date |
| `peak_date` | string (YYYY-MM-DD) | Date of maximum expected peak impact |
| `end_date` | string (YYYY-MM-DD) | True conclusion date |
| `multiplier` | float | Multiplier applied above baseline |
| `is_decoy` | boolean | True for artefacts that must NOT trigger alarms |

## 3. Incident Reports (`incident_report`)

Sanitized free-text incident records from workplace safety logs.

| Field | Type | Description |
|---|---|---|
| `incident_id` | string | Unique incident identifier |
| `site_id` | string | Worksite identifier |
| `district_id` | string | District identifier |
| `obs_date` | string (YYYY-MM-DD) | Date of incident |
| `narrative_sanitized` | string | Free text narrative with all PII stripped |
| `predicted_category` | string | Tagged category: `heat`, `respiratory_chemical`, `injury`, `other` |
| `confidence` | float | Classifier prediction confidence (0.0 to 1.0) |
| `ingested_at` | string (ISO-8601) | Ingestion timestamp |

