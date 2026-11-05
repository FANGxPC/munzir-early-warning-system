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
- **Mitigation:** Actions playbooks instruct worksite safety officers to treat Munzir alerts as triggers for on-site calibrated handheld heat bulb verification.

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

