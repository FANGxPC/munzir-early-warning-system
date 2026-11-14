# PRAHARI Sentinel: Hardware Plan

A small shade-mounted node that measures heat stress at a site, sends it to PRAHARI, and shows the current alert level on an LED.

**Built for beginners:** no soldering, no GPS, no purchases beyond what you likely already own.
**Assumption (please confirm):** you have an ESP32 DevKit, DHT22, one DS18B20 waterproof probe, an RGB LED, resistors, a breadboard, jumper wires, and a data USB cable. Section 2 covers what to check.

---

## 1. Overview

| The node does | The web app does |
|---|---|
| Reads air temp, humidity and globe temp every minute | Stores the node's location once, at setup |
| Estimates WBGT and uploads it | Decides the alert level and returns it in the upload reply |
| Shows that level on an LED | Shows on-site vs Open-Meteo-derived WBGT side by side |
| Shows a separate "offline" pattern if Wi-Fi or the API fails | Lowers confidence and shows "node offline" when readings stop |

The node carries no location and no person data.

---

## 2. Parts checklist

| Part | Check before you start |
|---|---|
| ESP32 DevKit | Joins **2.4 GHz** Wi-Fi only. Set your phone hotspot to 2.4 GHz (iPhone: "Maximize Compatibility"). |
| DHT22 | **3 pins on a small board** = pull-up included. **4 bare pins** = add a 10 kΩ resistor between data and 3.3 V. |
| DS18B20 waterproof probe | Needs a 4.7 kΩ resistor between data and 3.3 V. |
| Globe | Ping-pong ball painted matt black, probe tip at the centre. Treat it as a small-globe approximation. |
| RGB LED + three 220 Ω resistors | Note whether it is common-cathode or common-anode. |
| Breadboard, jumper wires | |
| USB cable | Must be a **data** cable, not charge-only. |
| Power bank | For running away from the laptop. |

Not needed: GPS, OLED, buzzer, second sensor, extra buttons. Use the **BOOT button already on the board** (GPIO 0 on most DevKits, [Warning] verify on yours). For a sun shield, put the DHT22 under an upturned white plastic cup with a few holes, in shade.

---

## 3. Wiring

Power everything from the **3.3 V** pin and join all grounds.

| Device | ESP32 pin |
|---|---|
| DHT22 data | GPIO 4 |
| DS18B20 data (+ 4.7 kΩ to 3.3 V) | GPIO 18 |
| LED red / green / blue (each through 220 Ω) | GPIO 25 / 26 / 27 |
| Button | Onboard BOOT (GPIO 0) |

These pins are suggestions. Confirm them against your board's pinout.

---

## 4. Location (no GPS)

Done once per node in the web app:

1. Open **Commission node** and choose the node ID (e.g. `SENT-001`).
2. Press **Use this device's location** and allow location access. This works only on HTTPS or localhost.
3. A pin and accuracy circle appear. Drag the pin to correct it if needed.
4. The server saves latitude, longitude, accuracy, method, H3 res-7 cell and a confidence flag.

| Result | `location_confidence` | In cluster scan? |
|---|---|---|
| Phone fix, accuracy ≤ 50 m | `exact` | Yes |
| Browser fix, accuracy ≤ 1000 m | `inferred` | Yes |
| Accuracy > 1000 m | `district_only` | No |

The thresholds are suggested defaults: make them configurable and call them assumptions.

**Know the limits.** A laptop has no GPS, so its fix comes from Wi-Fi or IP and can be off by a lot. It is also the laptop's position, not the node's. Always store and display the accuracy the browser reports. Opening the same page on a **phone** usually gives a better fix, at no cost. Do not commission from your home.

---

## 5. Data and logic

**Upload (once a minute):**

```json
{
  "node_id": "SENT-001",
  "seq": 18452,
  "ts": "2026-11-05T09:30:00Z",
  "air_temp_c": 34.2,
  "rh_pct": 61,
  "globe_temp_c": 41.0,
  "wbgt_est_c": 31.2,
  "ok": {"dht": true, "globe": true, "rssi": -67}
}
```

Example values only. If a sensor fails, send `null` for it and set its `ok` flag to false, never silence. This lets PRAHARI tell "sensor broken" from "node dead".

**Reply from the API:**

```json
{"level": "Watch", "valid_until": "2026-11-05T09:36:00Z"}
```

The LED follows `level`. If there are 3 failed uploads in a row, or `valid_until` has passed, the node switches to offline mode.

**WBGT**

- Outdoors with sun: `0.7 × Tnw + 0.2 × Tg + 0.1 × Ta`
- Indoors, no sun (a room demo): `0.7 × Tnw + 0.3 × Tg`
- `Tnw` is estimated from air temp and humidity with Stull's approximation, a rough stand-in for natural wet-bulb ([Warning] check its valid range in the paper).
- Put the mode (`indoor` / `outdoor`) in config and in the data. Label the result **"estimated WBGT"** everywhere.
- If you cannot build the globe: use the indoor formula with `Tg = Ta` and label it "estimated WBGT (no radiant term)". It is honest but makes the demo weaker.

**Checks:** reject impossible values (e.g. humidity above 100%) and flag a sensor that returns identical values for too long.

**Maps to your tables:** `wbgt_onsite`, `air_temp_onsite`, `rh_onsite` in `signal_observation`. Completeness is readings received divided by 1440 per day.

---

## 6. LED and button

| State | LED |
|---|---|
| Green | Solid green |
| Watch | Slow yellow blink |
| Warning | Double orange blink |
| Alert | Fast red blink |
| Offline mode | Blue blip, then the local colour pattern |
| Sensor fault | Magenta blink |
| Not commissioned | Slow cyan pulse |

Colour is always paired with a pattern. The dashboard also shows text labels.

**Button:** a short press sends an `ack` message, logged as an **on-site acknowledgement**. Keep it separate from a decision by a named responsible role.

**Offline thresholds** are local policy and configurable. This plan sets no clinical values, so use the ones in your playbook. For the demo, lower thresholds are fine if the screen labels them **DEMO**.

---

## 7. Build steps (stop at each checkpoint)

Times are my rough guess for beginners, not measured.

| # | Do this | Checkpoint | Guess |
|---|---|---|---|
| 1 | Install Arduino IDE and the ESP32 board package. Upload the blink example. | Onboard LED blinks | 1-2 h |
| 2 | Wire the DHT22. Install the DHT sensor library. | Serial Monitor shows sensible temp and humidity | 1 h |
| 3 | Wire the DS18B20 and resistor. Install OneWire and DallasTemperature. | Reading changes when you hold the probe | 1 h |
| 4 | Compute and print WBGT. | Value is plausible and rises when you warm the globe | 1 h |
| 5 | Join Wi-Fi and POST the JSON to your Azure function (or a local test endpoint). | Message arrives on the server | 2-3 h |
| 6 | Read `level` from the reply and drive the LED. | Change the level on the server and the LED follows | 2 h |
| 7 | Add the offline pattern, button ack, and nulls on sensor failure. | Hotspot off shows the offline pattern | 2 h |
| 8 | Build the commission page (web team). | Pin and accuracy circle appear and the record saves | — |

**Cut line:** if time is short, stop after step 6. That already gives a live on-site reading and a physical alert that matches the dashboard.

---

## 8. Troubleshooting

| Symptom | Likely cause |
|---|---|
| Upload fails or port not found | Charge-only cable. Try another. If it still fails, hold BOOT when the upload starts. |
| DHT22 prints `NaN` | Wrong pin or power, or missing pull-up on a 4-pin sensor. Leave 2 s between reads. |
| DS18B20 shows `-127` | Not connected, or missing the 4.7 kΩ resistor. |
| DS18B20 shows `85.0` | Just powered on. Read again. |
| Cannot join Wi-Fi | Hotspot is 5 GHz only, or wrong password. |
| LED colours look inverted | Common-anode vs common-cathode LED. Swap the logic in code. |
| Board resets or will not boot | A wire on a boot-sensitive pin. Use the pins in section 3. |
| Location button does nothing | Page not on HTTPS or localhost, or permission denied. |

---

## 9. Demo (about 2 minutes)

1. **Commission live:** pin and accuracy circle appear, flagged `inferred`.
2. **Baseline:** node is green, and the dashboard shows the on-site reading beside the Open-Meteo-derived value.
3. **Heat event:** lamp at a distance on the globe, plus brief warm steam near the DHT22. The LED goes yellow, then orange, and the dashboard follows.
4. **Offline:** switch the hotspot off. The LED shows the offline pattern, the dashboard shows "node offline", and confidence drops. Switch it back on.

Humidity moves WBGT more than the globe does, because wet-bulb carries the biggest weight, so a lamp alone gives only a modest change. Use labelled DEMO thresholds so the transitions are visible. Keep heat and steam away from the ESP32, and do not point a hairdryer at the ball.

**Backup:** a recorded video, and a replay script that posts a saved node trace. If you use replay, show a clear **REPLAY** banner.

---

## 10. Numbers to report

1. **Temperature error:** DHT22 vs a trusted thermometer, with the number of samples.
2. **Location error:** commission at a spot with a known coordinate and report the error in metres next to the browser's accuracy.
3. **24-hour run:** count dropouts and failed reads.
4. **Latency:** time from sensor reading to server to LED change, over a handful of runs.

Optional: on-site WBGT vs Open-Meteo-derived WBGT over a few hours, plotted.

---

## 11. Limits to state upfront

- WBGT is **estimated**, not measured with a real wet-bulb sensor, and the globe is a small-globe approximation.
- The DHT22 loses accuracy in very high humidity.
- Laptop location is approximate and is the laptop's position.
- The hardware covers one site. Clusters, absences and clinical signals are **simulated**.
- Security is demo-grade: the node may skip certificate checks and use a shared key. Say so.
- Wi-Fi is needed at the site.

---

## 12. To confirm

1. Your DHT22 type (3-pin or 4-pin) and LED type.
2. Your deadline.
3. That the web team can build the commission page and return `level` in the upload reply.

---

*Optional extras if the basics work early: a buzzer, and a wick natural wet-bulb sensor (second DS18B20 plus a cotton wick) for a measured WBGT next to the estimate.*
