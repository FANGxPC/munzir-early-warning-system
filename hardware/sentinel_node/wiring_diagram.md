# Munzir Sentinel — Hardware Wiring Diagram & Pinout

> **Device:** ESP32 DevKit (30-pin or 38-pin standard)  
> **Sensors:** DHT22 (Air Temp + Humidity) & DS18B20 (Waterproof Black Globe Temp)  
> **Indicator:** Common-Cathode RGB LED  
> **Controls:** On-board BOOT Button (GPIO 0)  
> **Power:** 3.3V Rail (Power Bank or USB 5V stepped down by onboard AMS1117 LDO)

---

## 1. Pin Connection Table

| Device | Device Pin | ESP32 GPIO | Resistor Needed | Function |
| :--- | :--- | :--- | :--- | :--- |
| **DHT22 Sensor** | Pin 1 (VCC) | **3.3V** | None | Power (3.3V regulated) |
| | Pin 2 (DATA) | **GPIO 4** | 10 kΩ pull-up to 3.3V *(if bare 4-pin)* | Digital bus |
| | Pin 3 (NC) | Not connected | None | None |
| | Pin 4 (GND) | **GND** | None | Ground rail |
| **DS18B20 Probe** | Red wire (VCC) | **3.3V** | None | Power |
| | Yellow/White (DATA)| **GPIO 18** | **4.7 kΩ pull-up to 3.3V** *(Mandatory)* | Dallas 1-Wire Bus |
| | Black wire (GND) | **GND** | None | Ground |
| **RGB LED** | Anode/Cathode | **GND** *(if cathode)* | None | Common pin |
| | Red leg | **GPIO 25** | **220 Ω** in series | Alert & Warning visual |
| | Green leg | **GPIO 26** | **220 Ω** in series | Normal baseline visual |
| | Blue leg | **GPIO 27** | **220 Ω** in series | Offline blip indicator |
| **BOOT Button** | On-board | **GPIO 0** | Internal pull-up | On-site operator acknowledgement |

---

## 2. ASCII Breadboard Wiring Diagram

```
                    ESP32 DevKit (30-pin)
                  ┌──────────────────────┐
            3.3V ─┤ [3V3]          [GND] ├─ Common Ground Rail
                  │                      │
                  │                      │
  DHT22 DATA ────►┤ [GPIO 4]             │
                  │                      │
DS18B20 DATA ────►┤ [GPIO 18]   [GPIO 25]├─► [220Ω] ──► RGB LED (Red)
                  │             [GPIO 26]├─► [220Ω] ──► RGB LED (Green)
                  │             [GPIO 27]├─► [220Ω] ──► RGB LED (Blue)
                  │                      │
      BOOT SW ───►│ [GPIO 0]             │
                  └──────────────────────┘

          ┌──────────────────────────────────────────────┐
          │ PULL-UP RESISTOR DETAILS:                    │
          │ 1. DS18B20: Connect 4.7kΩ between DATA and   │
          │    3.3V rail. Without this, sensor reads -127│
          │ 2. DHT22: If on a 3-pin breakout board,     │
          │    resistor is already built-in.             │
          │ 3. Black Globe: Insert waterproof DS18B20   │
          │    probe into centre of matte-black ball.   │
          └──────────────────────────────────────────────┘
```

---

## 3. Pre-Flight Verification Checklist

1. **Verify 2.4 GHz Wi-Fi:** ESP32 does not support 5 GHz Wi-Fi. Ensure mobile hotspot is in 2.4 GHz mode ("Maximize Compatibility" on iOS).
2. **Resistor check:** Ensure a 4.7 kΩ resistor bridges DS18B20 Data (GPIO 18) and 3.3V.
3. **Data USB Cable:** Ensure your micro-USB cable carries data lines (D+/D-) rather than power-only charging.
4. **Matte-Black Globe:** Spray ping-pong ball with flat/matte black paint to approximate standard black globe radiative absorption ($0.95$ emissivity).
