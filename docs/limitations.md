# Munzir Known Limitations & Technical Boundary Statement

**Document Version:** 1.0  
**Last Updated:** November 2026  
**Purpose:** Honest, plain-language disclosure of architectural assumptions, methodological limitations, and operating boundaries to maintain scientific credibility.

---

## 1. Synthetic Outcome Surge Labels
- **Context:** In a competition and pre-pilot prototype environment, prospective real-world clinical hospital records and classified workplace illness episodes are simulated using calibrated negative-binomial models.
- **Limitation:** While baseline overdispersion, day-of-week reporting seasonality, and exposure-response kinetics are calibrated against published epidemiological studies (ILO 2019, Lancet Countdown, CDC guidelines), synthetic data cannot capture all unforeseen idiosyncratic anomalies present in real-world health authority networks.
- **Mitigation & Path Forward:** A 12-week prospective shadow-mode pilot with partner health districts and outdoor worksites is planned to validate performance against true observed hospital and clinic admissions without altering current care practice.

---

## 2. Modelled WBGT Physics Approximations
- **Context:** Outdoor Wet Bulb Globe Temperature (WBGT) is derived from Open-Meteo numerical weather forecasts using the established Liljegren / Bernard / Stull empirical equations.
- **Limitation:** The model calculates ambient outdoor heat stress on a ~11 km spatial grid. It cannot account for:
  - Localized microclimates inside enclosed, unventilated industrial sheds or boiler rooms.
  - Radiant heat amplification from heavy diesel machinery operating in close proximity.
  - Personal protective equipment (PPE) thermal burdens (e.g. non-breathable fire-retardant coveralls or full-body chemical suits).
- **Mitigation:** The deployment of on-site **Munzir Sentinel ESP32 hardware nodes** directly bridges this gap by reading localized dry-bulb, relative humidity, and black-globe radiant temperatures at 60-second intervals right on the work floor, while action playbooks instruct worksite safety officers to treat regional alerts as triggers for on-site verification.

---

## 3. District-Level Geolocation Fallback
- **Context:** To preserve worker privacy and accommodate fragmented reporting systems, health records lacking exact GPS coordinates fall back through a spatial hierarchy:
  - `site` + `h3_res7` (exact GPS available)
  - `district` centroid (district known, specific facility redacted)
  - `state` / regional bucket (unknown specific location)
- **Limitation:** Records mapped to district centroids cannot participate in fine-grained H3 resolution 7 spatial cluster scans ($5.16\text{ km}^2$), potentially reducing spatial localization sensitivity for diffuse community presentations.
- **Mitigation:** The system assigns an explicit `location_confidence` badge (`exact` vs `district_only`) and renders district estimates with visible diagonal hatching on situation maps to prevent misinterpreting district aggregates as point-source hot spots.

---

## 4. Real-World Telemetry Reporting Delays
- **Context:** In real-world health systems, hospital EMR batches, laboratory culture confirmations, and community pharmacy sales do not arrive instantaneously; they exhibit a Poisson-distributed delay of 1 to 3 days.
- **Limitation:** While the rolling-origin backtest strictly respects these latency cut-offs without look-ahead bias, sudden outbreak events with sharp incubation periods (<24 hours) may rely initially on faster frontline signals (ambient WBGT forecasts and employer morning absence logs) before clinical confirmation catches up.
- **Mitigation:** The L4 fusion model dynamically up-weights low-latency environmental and workplace telemetry during the early incubation window, providing advance lead time even before batch hospital data arrives.

---

## 5. Particulate Sensor Drift & Desert Atmospheric Conditions
- **Context:** Ground-level particulate sensors in the Gulf region are subjected to extreme heat ($>45^\circ\text{C}$), high ambient humidity, and periodic coarse mineral dust storms.
- **Limitation:** Low-cost optical particle counters (OPCs) can experience optical chamber dust fouling or hygroscopic particulate swelling during humid marine incursions, leading to transient particulate overestimation.
- **Mitigation:** Munzir computes the $\text{PM}_{2.5} / \text{PM}_{10}$ ratio and corroborates ground sensors against CAMS atmospheric model forecasts to filter out optical sensor saturation.

---

## 6. Spatial Transfer Limits of Single Sentinel Sensor
- **Context:** An on-site ESP32 Sentinel node with DHT22 and DS18B20 matte-black globe measures true localized microclimates and trains an empirical bias correction against numerical weather model forecasts.
- **Limitation:** When only a single physical hardware node is active (e.g., at Jebel Ali Port), spatial transfer across other geographically dispersed industrial sites (e.g., Al Quoz, Ras Al Khor) cannot be empirically cross-validated without multi-node Leave-One-Sensor-Out (LOSO) telemetry. Claiming universal microclimate generalization across an entire emirate from a single point would be scientifically invalid.
- **Mitigation:** Any unsensored site is explicitly tagged with `UNVALIDATED-SPATIALLY` in all API responses and UI panels, its conformal prediction intervals are widened to reflect spatial uncertainty, and before-and-after error reductions are strictly reported only for sensored locations. Multi-sensor LOSO validation is scheduled as part of the Phase 12/13 pilot deployment.

---

## 7. Intervention Cost Parameter Verification in What-If Simulator
- **Context:** The What-If Intervention Simulator combines deterministic schedule recomputations with literature-derived dose-response curves and operational intervention unit costs.
- **Limitation:** While epidemiological effect sizes are cited directly from peer-reviewed literature (*Hall & Horta 2020*, *Wegman et al. 2018*, *MOHRE Ministerial Resolution 44/2022*), local commercial costs (such as modular shade canopy rentals, chilled electrolyte bulk procurement, and split-shift transportation logistics in the UAE) vary by contractor and seasonal supply chain fluctuations.
- **Mitigation:** All cost parameters without a published academic or regulatory index are cataloged in `config/assumptions.yaml` with explicit `UNVERIFIED` tags. The system uses Monte Carlo distributions ($N=1,000$ draws) across wide plausible cost ranges rather than single fixed figures, and users can inspect or override unit cost assumptions in real time.

---

## 8. Health Data Provenance & Prospective Shadow-Mode Path
- **Context:** True patient-level syndromic emergency department records from UAE public health authorities (DHA, MOHRE, SEHA) are confidential under UAE Federal Decree-Law No. 45 of 2021 on Personal Data Protection and cannot be published or distributed in public competition repositories without formal institutional IRB approval.
- **Limitation:** To ensure absolute reproducibility and operational benchmarking under Hackathon Challenge Criterion #5 without violating privacy laws, historical evaluation uses authentic CDC NSSP Pacific Northwest emergency department records and authentic federal US DOL OSHA Severe Injury records alongside authentic Open-Meteo and OpenAQ v3 feeds. Local UAE syndromic trends are modeled using calibrated synthetic epidemiology conforming to DHA/MOHRE demographics.
- **Mitigation:** We have designed an explicit 12-week prospective shadow-mode pilot protocol (aligned with DECIDE-AI Stage 2) to validate Munzir against live, non-public DHA hospital registries in an air-gapped, zero-PII environment prior to active clinical interventional deployment.

