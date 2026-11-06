# Munzir Sentinel — Firmware Build & Flash Guide

Follow this guide to build, flash, and commission a Munzir Sentinel on-site WBGT hardware node in under 30 minutes.

---

## 1. Required Arduino IDE Libraries

Open **Arduino IDE** $\to$ **Tools** $\to$ **Manage Libraries...** and install:

1. **ESP32 Board Package:** (via Boards Manager: `esp32` by Espressif Systems)
2. **DHT sensor library** by *Adafruit* (version 1.4.4+)
3. **Adafruit Unified Sensor** by *Adafruit*
4. **DallasTemperature** by *Miles Burton* (version 3.9.0+)
5. **OneWire** by *Paul Stoffregen* (version 2.3.7+)
6. **ArduinoJson** by *Benoit Blanchon* (version 6.21+ or 7.x)

---

## 2. Configuration & Flashing

1. Connect your ESP32 DevKit to your laptop via a micro-USB **data** cable.
2. Select your board under **Tools $\to$ Board $\to$ ESP32 Arduino $\to$ DOIT ESP32 DEVKIT V1** (or ESP32 Dev Module).
3. Select your serial port under **Tools $\to$ Port** (e.g. `/dev/ttyUSB0` or `COM3`).
4. Open `hardware/sentinel_node/config.h` and update:
   ```cpp
   #define WIFI_SSID         "Your_WiFi_Name"
   #define WIFI_PASSWORD     "Your_WiFi_Password"
   #define MUNZIR_API_BASE   "http://192.168.1.100:8000" // Your laptop IP running `make serve`
   #define NODE_ID           "SENT-001"
   ```
5. Click **Upload** (Ctrl + U). If upload gets stuck on `Connecting.......`, press and hold the physical **BOOT** button on the ESP32 until the flashing progress bar begins.
6. Open **Tools $\to$ Serial Monitor** set to **115200 baud**. You should see:
   ```
   [WiFi] Connected! IP: 192.168.1.145
   [Sensors] Air: 34.2 °C | RH: 58.0 % | Globe: 41.5 °C | Est WBGT: 31.4 °C
   [HTTP] POST http://192.168.1.100:8000/api/v1/sentinel/upload
   [Sentinel] Updated Alert Level: Warning
   ```

---

## 3. Commissioning the Node in Munzir

1. Open your browser to the Munzir Dashboard: `http://localhost:8000`.
2. Navigate to the **🔧 Sentinel Hardware** tab.
3. Click **➕ Commission New Node**.
4. Enter `SENT-001` (or matching `NODE_ID` in `config.h`).
5. Select your target worksite (e.g. `SITE-JA-01`).
6. Click **📱 Use This Device's Location** to grab browser GPS, or set coordinates.
7. Click **✔ Complete Commissioning**.
8. Within 60 seconds, the node table will update, showing the live measured WBGT, sensors status, and driving the on-board RGB LED to match the platform's alert level!

