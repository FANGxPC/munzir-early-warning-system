# Datasheet for Dataset: Open-Meteo Weather & Atmospheric Forecast API

**Version:** 1.0  
**Last Updated:** November 2026  
**Standards Alignment:** Gebru et al. (2021) *Datasheets for Datasets*

---

## 1. Motivation
- **Purpose:** Provide hourly, spatially resolved meteorological observations and numerical weather predictions (temperature, relative humidity, wind speed, direct solar radiation) required to calculate the Wet Bulb Globe Temperature (WBGT) and environmental heat-stress indices.
- **Created by:** Open-Meteo GmbH (open-source meteorological platform utilizing ECMWF, DWD ICON, and NOAA GFS models).
- **Funded by:** Open-Meteo community and commercial API subscriptions; utilized in PRAHARI under non-commercial open data terms.

---

## 2. Composition
- **Variables Ingested:**
  - `temperature_2m` (°C): Air temperature at 2 meters above ground.
  - `relative_humidity_2m` (%): Relative humidity at 2 meters.
  - `dew_point_2m` (°C): Surface dew point temperature.
  - `surface_solar_radiation` (W/m²): Direct and diffuse solar irradiance for black globe temperature ($T_g$) derivation.
  - `wind_speed_10m` (km/h): 10-meter wind velocity.
  - `cams_pm25` (µg/m³): Copernicus Atmosphere Monitoring Service (CAMS) particulate forecast.
- **Derived Metrics:**
  - `wbgt_max` (°C): Peak outdoor Wet Bulb Globe Temperature.
  - `wbgt_hours_caution`: Hours with $\text{WBGT} \ge 28^\circ\text{C}$ and $< 32^\circ\text{C}$.
  - `wbgt_hours_danger`: Hours with $\text{WBGT} \ge 32^\circ\text{C}$.
- **Geographic Coverage:** Monitored municipal districts in the UAE (Al Quoz, Jebel Ali, Deira, Downtown, Dubai South, Hatta).
- **Temporal Resolution:** Hourly ingestion aggregated into daily summary features.
- **PII / Confidential Data:** Contains **no personal data** or individual human records.

---

## 3. Collection Process
- **Mechanism:** Automated REST API calls to `https://api.open-meteo.com/v1/forecast` and historical archive endpoints.
- **Sampling Frequency:** Polled daily at 00:00 UTC (04:00 GST) for 7-day retrospective data and 3-day forward forecast.
- **Software Dependencies:** Python `requests`, cached locally in Bronze Parquet partitioned lakehouse (`data/bronze/weather/`).

---

## 4. Preprocessing & Data Hygiene
- **Liljegren / Bernard WBGT Engine:** Computes natural wet-bulb temperature ($T_{nw}$) via iteration over psychrometric equations and black globe temperature ($T_g$) using solar irradiance and air convection.
- **Data Quality Scoring:** Continuous DQ checks for missingness, range bounds ($-10^\circ\text{C} \le T \le 60^\circ\text{C}$), and latency staleness.

---

## 5. Uses & Out-of-Scope Uses
- **Intended Use:** Regional and district-level environmental exposure monitoring, occupational heat-stress risk stratification, and baseline environmental confounding adjustment in L2 GLMs.
- **Out-of-Scope Uses:** Micro-climate modeling inside unventilated enclosed confined spaces without dedicated internal dry-bulb sensors.

---

## 6. Known Biases & Limitations
- **Urban Heat Island (UHI) Effect:** Grid resolution (0.1° ~ 11 km) may slightly underestimate localized radiant heat from concrete pavements or heavy industrial machinery in Al Quoz Industrial.
- **Coastal Humidity Dynamics:** In the Arabian Gulf coastal corridor, sudden onshore sea breezes cause sharp spikes in dew point temperature that model re-analysis may capture with 1–2 hours latency.
- **Licence:** Creative Commons Attribution 4.0 International (CC BY 4.0).

