# Munzir Sentinel — Hardware Integration & Technical Specification

> **Component:** Munzir Sentinel On-Site Microclimate Hardware Node (Phase 11)  
> **Hardware:** ESP32 DevKit, DHT22 (Air Temp & RH), DS18B20 (Matte-Black Globe Temp), Multi-Pattern RGB LED, Piezo Buzzer (GPIO 21), BOOT Button (GPIO 0)  
> **Firmware:** `firmware/sentinel_node/sentinel_buzzer_node.ino` (Piezo Buzzer + RGB LED Edition)  
> **Security Clearance:** Operational EHS & Field Surveillance  
> **Reference Plan:** `new-PRAHARI_Sentinel_Hardware_Plan.md` & `Munzir_Sentinel_Hardware_Integration_Plan.md`

---

## 1. Architectural Overview

The **Munzir Sentinel** is a shade-mounted IoT microclimate monitoring device engineered to capture true worksite heat strain at the frontline of industrial operations. While satellite reanalysis and regional weather APIs provide macro-scale regional forecasts, worksite ground surfaces (asphalt, concrete, structural steel, marine berths) generate localized microclimate heat islands that coarse models underestimate by **1.5°C to 3.5°C WBGT**.

The Sentinel node bridges this gap by continuously streaming ground-truth environmental observations into Munzir's Bronze lakehouse, receiving back calibrated alert classifications in real-time, and driving on-board visual LED alert states for immediate worker safety awareness.

```
┌────────────────────────────────────────────────────────────────────────┐
│                   ESP32 SENTINEL HARDWARE NODE                        │
│   • DHT22 Air Temp & RH (GPIO 4)                                       │
│   • DS18B20 1-Wire Globe Probe in Matte-Black Ball (GPIO 18)           │
│   • BOOT Button On-Site Acknowledgement (GPIO 0)                       │
│   • Non-Blocking RGB LED (GPIO 25, 26, 27)                             │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP POST (60s cycle)
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│               MUNZIR REST API: /api/v1/sentinel/upload                │
│   1. Verifies node commission & bounds gating                          │
│   2. Re-derives WBGT via Stull (2011) psychrometric formulation        │
│   3. Detects stuck sensors & sequence upload gaps                      │
│   4. Emits 4 SignalObservation rows (wbgt_onsite, air_temp, rh, globe) │
│   5. Resolves site alert tier & valid_until window                     │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ HTTP Response JSON
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│                 ON-BOARD REAL-TIME VISUAL FEEDBACK                     │
│   • Green (Solid): Normal baseline monitoring                          │
│   • Yellow (1 Hz slow blink): Watch tier (hydration reminders)         │
│   • Orange (2 Hz double blink): Warning tier (15m mandatory rest)      │
│   • Red (4 Hz fast blink): Alert tier (immediate work-rest stoppage)   │
│   • Blue Blip: Offline fail-safe pattern                               │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Telemetry Schema & Lakehouse Mapping

### 2.1 Inbound Telemetry Payload (`POST /api/v1/sentinel/upload`)

```json
{
  "node_id": "SENT-001",
  "seq": 18452,
  "ts": "2026-11-06T10:00:00Z",
  "air_temp_c": 34.2,
  "rh_pct": 61.0,
  "globe_temp_c": 41.0,
  "wbgt_est_c": 31.2,
  "ok": {
    "dht": true,
    "globe": true,
    "rssi": -65
  }
}
```

### 2.2 Lakehouse Storage Mapping (`SignalObservation`)

Each valid upload generates four standard `SignalObservation` rows written directly into Bronze Parquet partitions:

| Signal Type | Value Extracted | Measurement Unit | Geo Level | Geo ID | Source Latency |
| :--- | :--- | :--- | :--- | :--- | :--- |
| `wbgt_onsite` | Re-derived WBGT | °C | `site` | Assigned Worksite ID | 0.02 hrs (1 min) |
| `air_temp_onsite` | DHT22 Dry Bulb | °C | `site` | Assigned Worksite ID | 0.02 hrs (1 min) |
| `rh_onsite` | DHT22 Relative Humidity | % | `site` | Assigned Worksite ID | 0.02 hrs (1 min) |
| `globe_temp_onsite`| DS18B20 Black Globe | °C | `site` | Assigned Worksite ID | 0.02 hrs (1 min) |

---

## 3. Server-Side Micrometeorology & Re-Derivation Physics

To maintain scientific integrity, the central Munzir platform **never blindly trusts edge compute values**. The server independently re-derives natural wet-bulb temperature using Stull's (2011) empirical psychrometric formulation:

$$T_w = T_a \cdot \arctan\left(0.151977 \sqrt{RH + 8.313659}\right) + \arctan\left(T_a + RH\right) - \arctan\left(RH - 1.676331\right) + 0.00391838 \cdot RH^{1.5} \cdot \arctan\left(0.023101 \cdot RH\right) - 4.686035$$

### Effective On-Site WBGT Calculation
- **Outdoor Mode (with Solar Globe):**
  $$\text{WBGT}_{\text{onsite}} = 0.7 \cdot T_w + 0.2 \cdot T_g + 0.1 \cdot T_a$$
- **Indoor / Canteen Mode (or Globe Fault Fallback):**
  $$\text{WBGT}_{\text{onsite}} = 0.7 \cdot T_w + 0.3 \cdot T_g \quad (\text{or } T_a \text{ if } T_g \text{ is unavailable})$$

---

## 4. Commissioning & Geolocation Fallback Hierarchy

Nodes carry **zero GPS hardware and zero stored location coordinates**. Location is assigned once at physical deployment via the Munzir web dashboard:

1. Safety officer logs in and opens the **Commission Node** dialog.
2. Selects target worksite (`SITE-JA-01`).
3. Presses **📱 Use This Device's Location** to query the W3C Geolocation API.
4. Server computes the Uber H3 Resolution 7 hexagonal index (`~5.16 km²`) and assigns a location confidence flag:

| Browser Accuracy | Location Confidence Flag | Spatial Resolution | Included in L3 Space-Time Scan? |
| :--- | :--- | :--- | :--- |
| $\text{Accuracy} \le 50\text{ m}$ | `exact` | Site Coordinate + H3 Res-7 | **Yes** |
| $50\text{ m} < \text{Accuracy} \le 1,000\text{ m}$ | `inferred` | H3 Res-7 Centroid | **Yes** |
| $\text{Accuracy} > 1,000\text{ m}$ | `district_only` | District Centroid | **No** (Excluded from micro-scan) |

---

## 5. Visual & Audible Alert States & Fault Handling

The Sentinel node delivers dual-channel sensory alerting (visual RGB LED + audible piezo buzzer) driven directly by the server's calibrated alert classification:

| Operational State | Alert Level | On-Board RGB LED Pattern | Buzzer Audible Pattern (`GPIO 21`) | Required Preventive Action |
| :--- | :--- | :--- | :--- | :--- |
| Normal Baseline | `None` | **Solid Green** | **Silent** | Continuous environmental monitoring |
| Active Watch | `Watch` | **Slow Yellow Blink (1 Hz)** | **Single short chirp** (800 Hz, 80ms / 30s) | Hydration reminders, shade availability check |
| Preventive Warning | `Warning` | **Double Orange Blink (2 Hz)** | **Double pulse** (1000 Hz $\to$ 1500 Hz, 150ms / 5s) | Mandatory 15-min rest cycles per hour, shift rescheduling |
| Severe Hazard | `Alert` | **Fast Red Blink (4 Hz)** | **Staccato alarm** (2200 Hz, 100ms on/off continuous) | Immediate heavy work stoppage, misting fan deployment |
| Node Offline | `Offline` | **Blue Blip (100ms flash / 2s)** | **Silent** | Local fallback mode; dashboard displays offline badge |
| Sensor Fault | `Fault` | **Magenta Blink** | **Low error click** (400 Hz, 50ms) | Gated; valid sensors continue transmission |

### Web UI Manual Telemetry Trigger (`⚡ Sample Telemetry`)
In addition to the autonomous 60-second hardware loop, operators and evaluators can click **`⚡ Sample Telemetry`** directly on the Sentinel dashboard panel. This immediately pushes the latest sensor values to `/api/v1/sentinel/upload` and synchronizes the physical buzzer and LED pattern without waiting for the next cron cycle.

### Heartbeat Watchdog & Stuck Sensor Detection
- **Offline Watchdog:** If a node misses 3 consecutive uploads ($> 180$ seconds), the server marks `is_online = False` and triggers conformal interval widening.
- **Stuck Sensor Filter:** If a sensor returns identical readings for 10 consecutive minutes, the server flags `sensor_health = False` and switches to the single-sensor fallback formula.

---

## 6. On-Site Acknowledgement vs. Clinical Triage

When an on-site operator presses the physical **BOOT button** on the ESP32:
- The node dispatches an asynchronous acknowledgement packet to `/api/v1/sentinel/ack`.
- The event is recorded in the non-repudiation audit log with `source: "sentinel_button"` and `user_role: "on_site_operator"`.
- **Safety Invariant:** A physical button press on a hardware node **cannot dismiss or override** an alert assigned to a designated Clinical Surveillance Officer or MOHRE Inspector. It confirms field awareness without bypassing governance controls.

---

## 7. Known Limitations & Disclosure

1. **Estimated vs. Direct Natural Wet-Bulb:** Stull's equation is a psychrometric approximation. It serves as an on-site screening indicator, not an ISO 7243 calibrated reference standard.
2. **Small-Globe Approximation:** A matte-black ping-pong ball (40mm) responds faster to radiative changes than a standard 150mm Vernon black globe, resulting in minor thermal inertia differences.
3. **Demo-Grade Transport Security:** The prototype utilizes a shared API key (`X-Sentinel-Key`). Enterprise production deployments will utilize Azure IoT Hub with per-device X.509 certificates and TPM 2.0 security.

