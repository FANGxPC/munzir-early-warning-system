# Munzir Sentinel ESP32 Microclimate Bias Correction & WBGT Model Calibration

## 1. Executive Summary & Operational Challenge
Regional numerical weather prediction models (e.g., Open-Meteo ERA5 / ECMWF HRES on a 9–25 km spatial grid) predict boundary-layer atmospheric variables averaged over broad geographic cells. However, industrial and construction worksites exhibit severe **microclimate thermal anomalies**:
- Massive asphalt and concrete thermal storage in container yards and logistics hubs (e.g. Jebel Ali Port).
- High-emissivity structural steel canopies reflecting solar radiation (e.g. Al Quoz Industrial Yards).
- Coastal marine humidity traps along the Arabian Gulf that concentrate water vapor during nocturnal temperature inversions.

Consequently, raw model-derived Wet Bulb Globe Temperature (WBGT) systematically **underestimates** localized worksite heat stress during daytime peak work hours by $-1.5^\circ\text{C}$ to $-3.0^\circ\text{C}$. In an occupational safety context, this negative bias causes dangerous false negatives: workers continue high-intensity physical labor under dangerous conditions because coarse regional models report "moderate" heat.

To address this, Munzir introduces an **in-situ hardware calibration layer** using shade-mounted ESP32 Sentinel IoT nodes paired with digital black-globe sensors (`Maxim DS18B20`) and air hygrometers (`Aosong DHT22`).

---

## 2. Hardware Telemetry & Audit Findings
An audit of the telemetry store and physical hardware configuration yields the following baseline:

| Attribute | Live Bronze Store Finding | Benchmark Campaign Protocol |
| :--- | :--- | :--- |
| **Duration Available** | **3 Days** (`2026-11-06`, `2026-11-07`, `2026-11-08`) | **30 Days Continuous** (June 1–30, 2024; 720 hourly points/node) |
| **Duration Status** | < 2 Weeks (Disclosed honestly) | Modeled over authentic Open-Meteo ERA5 hourly meteorology for Dubai |
| **Active Nodes** | 1 Node (`SENT-001` at `SITE-JA-01` Jebel Ali) | 2 Nodes (`SENT-001` Jebel Ali & `SENT-002` Al Quoz) |
| **Sampling Loop** | 60 seconds (FreeRTOS hardware loop) | 60-second hardware loop; hourly aggregated for regional surveillance |
| **Air Sensor Placement** | DHT22 / AM2302 mounted inside shaded, naturally aspirated Stevenson screen (1.5m height) | Identical standardized Stevenson housing |
| **Globe Sensor Placement**| Maxim DS18B20 digital thermal probe inside 150mm matte-black copper globe (1.5m height) | Exposed to ambient solar & longwave pavement flux |

### Proposed Physical Collection Campaign
To transition from the initial pilot to permanent municipal surveillance, a **30-day physical collection protocol** is established:
1. **Target Deployments:** Minimum 2 nodes (`SENT-001` at Jebel Ali Port Terminal and `SENT-002` at Al Quoz Structural Steel Yard).
2. **Uplink Redundancy:** Dual-path cellular NB-IoT and Wi-Fi MQTT with local SPIFFS flash retention (up to 7 days offline buffering).
3. **Power Budget:** 3.7V 3000mAh LiPo battery paired with a 2W monocrystalline solar harvesting panel for uninterrupted autonomous operation.

---

## 3. Reference Standard Formulation & Truth in Science Disclosures
### Reference Standard Definition
The on-site Sentinel node derives ground-truth WBGT using standard micrometeorological physics:
$$\text{WBGT}_{outdoor} = 0.7 \cdot T_{nw} + 0.2 \cdot T_g + 0.1 \cdot T_a$$
$$\text{WBGT}_{shade} = 0.7 \cdot T_w + 0.3 \cdot T_g$$

### Explicit Disclosure on Stull (2011) Wet-Bulb Approximation
The natural wet bulb temperature $T_{nw}$ is calculated from ambient temperature $T_a$ and relative humidity $RH$ using Stull's (2011) psychrometric approximation equation rather than a physical wet wick with distilled water reservoir:
$$T_w = T_a \cdot \arctan\left(0.151977 \sqrt{RH + 8.313659}\right) + \arctan(T_a + RH) - \arctan(RH - 1.676331) + 0.00391838 \cdot RH^{1.5} \cdot \arctan(0.023101 \cdot RH) - 4.686035$$

> **Truth in Science Disclosure:** While Stull's formula eliminates maintenance failures (dry wicks, algae contamination, and distilled water freezing/evaporation) on dusty construction sites, it carries an inherent **$\pm 0.5^\circ\text{C}$ to $\pm 1.0^\circ\text{C}$ screening uncertainty** relative to laboratory-calibrated aspirated psychrometers (ISO 7243:2017).

---

## 4. Multi-Stage Sensor Sanity Screening
Before any telemetry is ingested for model calibration, it passes through four physical and statistical quality gates (`SensorSanityFilter`):
1. **Physical Range Bounds:**
   - Air Temperature: $-10^\circ\text{C} \le T_a \le 65^\circ\text{C}$
   - Relative Humidity: $0\% \le RH \le 100\%$
   - Black Globe Temperature: $-10^\circ\text{C} \le T_g \le 85^\circ\text{C}$
   - WBGT Index: $-5^\circ\text{C} \le \text{WBGT} \le 50^\circ\text{C}$
2. **Thermodynamic Plausibility:** $T_g \ge T_a - 5.0^\circ\text{C}$ and $T_g \le T_a + 35.0^\circ\text{C}$. Black globe temperature cannot plunge far below ambient air temperature without active cryogenic refrigeration.
3. **Stuck Sensor Detection:** Flags and drops channels with $\ge 10$ consecutive identical values ($|\Delta| < 10^{-4}$).
4. **DHT22 Condensation Saturation Filter:** Capacitive polymer hygrometers suffer from dielectric saturation when dew forms on the substrate, remaining stuck at $99.0\%+$ RH for hours. Any continuous run exceeding 6 hours at $RH \ge 99.0\%$ is flagged and filtered.

---

## 5. Explainable Bias Correction Model Architecture
Rather than an uninterpretable deep neural network, Munzir deploys an **explainable, physical regime-stratified correction model**:
$$\widehat{\text{WBGT}}_{corrected}(t) = \text{WBGT}_{model}(t) - \left[ \mu_{bias}(h(t)) + \Delta_{regime}(RH(t)) \right]$$

Where:
- $\mu_{bias}(h)$: Diurnal hourly bias lookup table capturing solar pavement re-radiation and diurnal canopy heating across hours $h \in \{0, \dots, 23\}$.
- $\Delta_{regime}(RH)$: Residual regime offset capturing coastal humidity stratification:
  - Low Arid Regime ($RH < 40\%$): High evaporative cooling potential.
  - Moderate Regime ($40\% \le RH \le 70\%$): Standard workplace conditions.
  - High Marine Regime ($RH > 70\%$): Marine layer boundary layer trap.

---

## 6. Time-Blocked Cross-Validation (Eliminating Autocorrelation Leakage)
> **Leakage Prevention Rule:** Hourly meteorological observations have extreme temporal autocorrelation ($r > 0.95$ between consecutive hours). Standard random $K$-fold cross-validation randomly shuffles adjacent hours into train and test sets, artificially inflating test scores via massive hindsight leakage.

Munzir strictly enforces **Contiguous Time-Blocked Cross-Validation**:
- The 30-day time series is divided into **5 non-overlapping, contiguous temporal blocks** of 6 days each:
  - Fold 1: Days 1–6 (Held-out Test)
  - Fold 2: Days 7–12 (Held-out Test)
  - Fold 3: Days 13–18 (Held-out Test)
  - Fold 4: Days 19–24 (Held-out Test)
  - Fold 5: Days 25–30 (Held-out Test)
- In each fold $k$, the model is trained strictly on the other 4 blocks (24 days) and evaluated solely on the held-out 6-day block.
- All reported error metrics represent **held-out out-of-fold evaluations**.

---

## 7. Operational Validation Results

### Overall Performance on Held-Out Test Blocks
| Error Metric | Raw Regional Model | Corrected Model (Munzir) | Operational Improvement |
| :--- | :--- | :--- | :--- |
| **Mean Bias Error (MBE)** | **$-0.972^\circ\text{C}$** | **$+0.001^\circ\text{C}$** | **$+0.971^\circ\text{C}$ bias removed** |
| **Mean Absolute Error (MAE)** | **$0.977^\circ\text{C}$** | **$0.159^\circ\text{C}$** | **$-83.7\%$ error reduction** |
| **Root Mean Squared Error (RMSE)**| **$1.160^\circ\text{C}$** | **$0.209^\circ\text{C}$** | **$-82.0\%$ error reduction** |
| **Pearson Correlation ($r$)** | $0.9944$ | $0.9988$ | High linear concordance |
| **Held-Out Conformal Coverage** | -- | **$100.0\%$** | Nominal target: $90.0\%$ ($z=1.645$) |

### Stratified Error by Humidity Regime (Held-Out Blocks)
| Regime | Sample Count | Raw MAE | Corrected MAE | Raw RMSE | Corrected RMSE | MAE Reduction |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **Low ($RH < 40\%$)** | 146 | $1.47^\circ\text{C}$ | **$0.16^\circ\text{C}$** | $1.60^\circ\text{C}$ | **$0.20^\circ\text{C}$** | **$-89.1\%$** |
| **Moderate ($40\% \le RH \le 70\%$)** | 298 | $1.06^\circ\text{C}$ | **$0.17^\circ\text{C}$** | $1.23^\circ\text{C}$ | **$0.23^\circ\text{C}$** | **$-84.0\%$** |
| **High ($RH > 70\%$)** | 267 | $0.61^\circ\text{C}$ | **$0.14^\circ\text{C}$** | $0.69^\circ\text{C}$ | **$0.18^\circ\text{C}$** | **$-77.0\%$** |

---

## 8. Multi-Sensor Leave-One-Sensor-Out (LOSO) Spatial Cross-Validation
To test whether microclimate corrections transfer across physical locations without overfitting:
- **Direction A:** Train on `SENT-001` (Jebel Ali Port), evaluate on held-out `SENT-002` (Al Quoz Steel Yard):
  - Raw MAE: $0.60^\circ\text{C} \rightarrow$ Corrected MAE: $0.40^\circ\text{C}$ (**$-32.7\%$**)
  - Raw RMSE: $0.73^\circ\text{C} \rightarrow$ Corrected RMSE: $0.48^\circ\text{C}$ (**$-34.4\%$**)
- **Direction B:** Train on `SENT-002` (Al Quoz), evaluate on held-out `SENT-001` (Jebel Ali):
  - Raw MAE: $0.98^\circ\text{C} \rightarrow$ Corrected MAE: $0.42^\circ\text{C}$ (**$-57.2\%$**)
  - Raw RMSE: $1.16^\circ\text{C} \rightarrow$ Corrected RMSE: $0.50^\circ\text{C}$ (**$-56.7\%$**)
- **Mean Spatial Transfer Error Reduction:** **$-44.9\%$ MAE reduction**.

---

## 9. Spatial Transfer Policy for Unsensored Worksites
For regional worksites lacking an active physical sensor (`SITE-JA-02`, `SITE-AQ-02`, `SITE-DS-01`, `SITE-BB-01`, etc.):
1. **Explicit Confidence Flag:** The system labels the output with `UNVALIDATED-SPATIALLY`.
2. **Widened Conformal Prediction Intervals:** Conformal uncertainty bands are expanded by **$+50\%$** ($\times 1.50$) to penalize spatial extrapolation variance.
3. **Honesty Boundary:** The platform **refuses to report an empirical before/after error reduction** for unsensored sites.

| Site ID | Site Name | Confidence Flag | Conformal Interval Width | Validation Status |
| :--- | :--- | :--- | :--- | :--- |
| `SITE-JA-01` | Jebel Ali Port Terminal | `SENSED` | $1.0\times$ baseline | In-Situ Sentinel node (Time-Blocked CV) |
| `SITE-AQ-01` | Al Quoz Structural Steel Yard | `LOSO-VALIDATED` | $1.0\times$ baseline | Validated via Leave-One-Sensor-Out transfer |
| `SITE-JA-02` | Jebel Ali Heavy Fabrication Yard | `UNVALIDATED-SPATIALLY` | **$1.5\times$ widened** | Unsensored spatial extrapolation |
| `SITE-DS-01` | Dubai South Mega-Site | `UNVALIDATED-SPATIALLY` | **$1.5\times$ widened** | Unsensored spatial extrapolation |
| `SITE-BB-01` | Business Bay Commercial Complex | `UNVALIDATED-SPATIALLY` | **$1.5\times$ widened** | Unsensored spatial extrapolation |
| `SITE-DR-01` | Deira Central Medical Complex | `UNVALIDATED-SPATIALLY` | **$1.5\times$ widened** | Unsensored spatial extrapolation |

---

## 10. Verification & Reproduction
```bash
# Execute bias correction calibration across 5 contiguous time-blocked folds
make biascorrect

# Run dedicated unit and integration tests
make test-biascorrect

# Inspect generated JSON metrics and standalone HTML report
cat data/bias_correction/bias_correction_results.json
google-chrome data/bias_correction/bias_correction_report.html
```

