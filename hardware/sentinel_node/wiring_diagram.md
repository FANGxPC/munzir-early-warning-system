# Munzir Sentinel — Hardware Wiring Diagram & Pinout (3-LED RGB Edition)

> **Device:** ESP32 DevKit (30-pin or 38-pin standard)  
> **Sensors:** DHT22 (Air Temp + Humidity) & DS18B20 (Waterproof Radiant Probe in Matte-Black Box)  
> **Indicators:** 3 Separate Alert LEDs (Red, Blue, Green) — Traffic-Light Heat Status  
> **Controls:** On-board BOOT Button (GPIO 0)  
> **Power:** 3.3V Rail (Power Bank or USB 5V stepped down by onboard AMS1117 LDO)

---

## 1. Pin Connection Table

| Device | Device Pin / Wire | ESP32 Pin | Resistor Needed | Function / Placement |
| :--- | :--- | :--- | :--- | :--- |
| **DHT22 Sensor** | Pin 1 (VCC) | **3V3** | None | Power (3.3V) |
| | Pin 2 (DATA) | **GPIO 4** | None *(Built-in on 3-pin module)* | Ambient air temp & humidity (**Keep OUTSIDE box**) |
| | Pin 3 (GND) | **GND** | None | Common Ground |
| **DS18B20 Probe** | Red wire (VCC) | **3V3** | None | Power (3.3V) |
| | Yellow/White (DATA)| **GPIO 18** | **4.7 kΩ pull-up to 3V3** *(Mandatory!)* | Radiant globe temp (**Suspend inside sealed matte-black box**) |
| | Black wire (GND) | **GND** | None | Common Ground |
| **RED LED** | Anode (+ long leg) | **GPIO 25** | **220 Ω to 330 Ω** in series | **ALERT Tier** ($> 32.2^\circ\text{C}$ WBGT) — Work Cessation |
| | Cathode (- short leg)| **GND** | None | Common Ground |
| **BLUE LED** | Anode (+ long leg) | **GPIO 26** | **220 Ω to 330 Ω** in series | **WARNING / WATCH Tier** ($28^\circ - 32^\circ\text{C}$ WBGT) — Caution & Rest |
| | Cathode (- short leg)| **GND** | None | Common Ground |
| **GREEN LED** | Anode (+ long leg) | **GPIO 27** | **220 Ω to 330 Ω** in series | **NORMAL Tier** ($< 28^\circ\text{C}$ WBGT) — Safe Conditions |
| | Cathode (- short leg)| **GND** | None | Common Ground |
| **BOOT Button** | On-board | **GPIO 0** | Internal pull-up | Operator acknowledgement / manual test |

---

## 2. ASCII Breadboard Wiring Diagram

```
                              ESP32 DevKit (30-pin)
                             ┌──────────────────────┐
       Power Rail (+3.3V) ───┤ [3V3]          [GND] ├──── Common Ground Rail (GND)
                             │                      │
                             │                      │
   DHT22 DATA (Outside) ────►┤ [GPIO 4]             │
                             │                      │
 DS18B20 DATA (In Box)  ────►┤ [GPIO 18]   [GPIO 25]├─► [220Ω] ──► (Anode +) [ RED LED ]   (Cathode -) ──► GND
                             │             [GPIO 26]├─► [220Ω] ──► (Anode +) [ BLUE LED ]  (Cathode -) ──► GND
                             │             [GPIO 27]├─► [220Ω] ──► (Anode +) [ GREEN LED ] (Cathode -) ──► GND
                             │                      │
     BOOT SW (Built-in) ────►┤ [GPIO 0]             │
                             └──────────────────────┘

  ┌────────────────────────────────────────────────────────────────────────────────────────┐
  │ MANDATORY WIRING DETAILS:                                                              │
  │ 1. DS18B20 PULL-UP: Connect a 4.7kΩ resistor between GPIO 18 and 3V3.                  │
  │    (Without this 4.7kΩ pull-up, Dallas 1-Wire will output error -127°C or 85°C).       │
  │ 2. LED RESISTORS: Place a 220Ω or 330Ω resistor between each GPIO pin and the LED      │
  │    positive (anode) leg to protect the ESP32 pins from over-current.                   │
  │ 3. SENSOR PLACEMENT:                                                                   │
  │    • DS18B20: Suspend probe tip in the center of the sealed matte-black box.          │
  │    • DHT22:   Keep in the open room air (outside the box) to measure ambient climate. │
  └────────────────────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Visual Heat Tier States

| Condition / WBGT Index | Green LED (GPIO 27) | Blue LED (GPIO 26) | Red LED (GPIO 25) | Operational Meaning |
| :--- | :--- | :--- | :--- | :--- |
| **Power-On Test** | On (0.3s) | On (0.3s) | On (0.3s) | Self-test sweep on startup |
| **NORMAL (< 28°C WBGT)** | **SOLID ON** | OFF | OFF | Safe conditions; normal shifts |
| **WATCH (28°C – 30°C)** | OFF | **SOLID ON** | OFF | Monitor hydration; enforce shaded rest |
| **WARNING (30°C – 32.2°C)**| OFF | **DOUBLE BLINK** | OFF | Heavy labor restriction; 15m rest/hr |
| **ALERT (> 32.2°C WBGT)** | OFF | OFF | **FAST FLASH** | Mandatory Midday Work Stoppage (Res 44) |
| **Offline / Standalone Edge Mode** | **Follows Local WBGT** (Solid Green if Safe) | Follows Local WBGT (Solid/Blink if Caution) | Follows Local WBGT (Fast Flash if Danger) | Autonomous Edge Fallback: Computes Stull WBGT locally from physical sensors with zero reliance on cloud/Wi-Fi |
