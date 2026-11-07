# Datasheet for Dataset: OpenAQ Global Ground-Level Air Quality Platform

**Version:** 1.0  
**Last Updated:** November 2026  
**Standards Alignment:** Gebru et al. (2021) *Datasheets for Datasets*

---

## 1. Motivation
- **Purpose:** Ingest ground-truth, sensor-level ambient particulate matter ($\text{PM}_{2.5}$, $\text{PM}_{10}$) observations to corroborate atmospheric CAMS forecasts and identify localized air quality hazards (dust storms, construction particulate plumes).
- **Created by:** OpenAQ, Inc. (non-profit open air quality data clearinghouse).
- **Funded by:** Grants, philanthropic contributions, and sponsor organizations; used under OpenAQ open data terms.

---

## 2. Composition
- **Variables Ingested:**
  - `pm25` (µg/m³): Fine particulate matter concentration.
  - `pm10` (µg/m³): Coarse particulate matter concentration.
  - `sensor_id`, `station_name`, `coordinates`: Geolocation of physical ground monitoring station.
- **Derived Metrics:**
  - `pm25_exceedance_hours`: Hours exceeding WHO 24-hour interim guidance target (37.5 µg/m³).
  - `pm_ratio`: $\text{PM}_{2.5} / \text{PM}_{10}$ ratio indicating particulate provenance (combustion vs mineral dust).
- **Geographic Coverage:** Reference monitors and verified ground sensors across Dubai and Northern Emirates, including physical OpenAQ v3 stations:
  - US Consulate / Business Bay (`Location ID: 14384841`)
  - The Views Community Station (`Location ID: 10071461`)
  - Motor City Station (`Location ID: 10877520`)
  - Al Barari Station (`Location ID: 17486266`)
- **PII / Confidential Data:** Contains **no personal data**.

---

## 3. Collection Process
- **Mechanism:** OpenAQ REST API v3 (`https://api.openaq.org/v3/locations/` and `/measurements/`).
- **Data Latency:** Typically available within 1–4 hours of physical measurement.
- **Storage:** Persisted to Bronze Parquet partition lakehouse (`data/bronze/air_quality/`).

---

## 4. Preprocessing & Cleaning
- **Physical Plausibility Bounds:** Filters raw values outside $[0.0, 1500.0]$ µg/m³.
- **Sensor Drift & Outlier Flagging:** Baseline subtraction and spike detection against neighborhood rolling medians.

---

## 5. Uses & Out-of-Scope Uses
- **Intended Use:** Detection of acute particulate surges, calibration of L2 exposure-response baselines for respiratory syndromes, and triggering air quality alert playbooks.
- **Out-of-Scope Uses:** Enforcement of statutory emissions fines against individual vehicle exhaust pipes (requires stationary source certification).

---

## 6. Known Biases & Limitations
- **Sensor Density Disparity:** Industrial corridors (e.g. Jebel Ali, Al Quoz) have higher sensor coverage than remote desert areas (e.g. Hatta).
- **Dust Storm Artifacts:** High mineral dust concentrations can cause optical particle counter sensor saturation.
- **Licence:** Open Data Commons Attribution License (ODC-By) / OpenAQ Data Terms.

