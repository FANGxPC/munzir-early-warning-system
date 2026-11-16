/**
 * Munzir Sentinel — On-Site WBGT Microclimate Hardware Node (RGB LED Edition)
 * Firmware for ESP32 DevKit + DHT22 + DS18B20 (Black Box) + 3 Separate LEDs (Red, Blue, Green)
 * 
 * ==============================================================================
 * HARDWARE CONNECTIONS & PINOUT (ESP32 DevKit)
 * ==============================================================================
 * 
 * 1. DHT22 (Ambient Air Temperature & Humidity - Keep OUTSIDE in shade):
 *    - VCC  (+)    -> ESP32 3V3
 *    - GND  (-)    -> ESP32 GND
 *    - DATA (Out)  -> ESP32 GPIO 4
 * 
 * 2. DS18B20 (Radiant Heat Sensor - Suspend inside sealed matte-black box):
 *    - VCC  (Red)    -> ESP32 3V3
 *    - GND  (Black)  -> ESP32 GND
 *    - DATA (Yellow) -> ESP32 GPIO 18
 *    ** REQUIRED: 4.7kΩ pull-up resistor connected between GPIO 18 and 3V3 **
 * 
 * 3. THREE INDIVIDUAL ALERT LEDs (RGB Traffic-Light Heat Status):
 *    - RED LED   (Alert / Hazard)    -> Anode (+) to ESP32 GPIO 25 (via 220Ω resistor) | Cathode (-) to GND
 *    - BLUE LED  (Warning / Caution) -> Anode (+) to ESP32 GPIO 26 (via 220Ω resistor) | Cathode (-) to GND
 *    - GREEN LED (Normal / Safe)     -> Anode (+) to ESP32 GPIO 27 (via 220Ω resistor) | Cathode (-) to GND
 * 
 * 4. BOOT Button (Operator Acknowledgement):
 *    - Built-in GPIO 0 on standard ESP32 DevKit
 * ==============================================================================
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h> // Library: ArduinoJson by Benoit Blanchon (v6 or v7)
#include <math.h>

// =============================================================
// 1. NETWORK & BACKEND CONFIGURATION (EDIT THESE 3 LINES)
// =============================================================
#define WIFI_SSID         "OPPO A77"                      // 2.4 GHz Wi-Fi or Phone Hotspot
#define WIFI_PASSWORD     "1234567890"                  // Wi-Fi password
#define MUNZIR_API_BASE   "http://10.46.55.27:8000"     // Laptop IP running Munzir backend (OPPO A77 subnet)

// Node Parameters
#define NODE_ID           "SENT-001"
#define SENTINEL_API_KEY  "munzir_sentinel_secret_2026"
#define UPLOAD_INTERVAL_MS 5000                         // Telemetry sample rate: 5s (responsive live demo)

// =============================================================
// 2. PIN ASSIGNMENTS
// =============================================================
#define PIN_DHT22         4       // DHT22 data pin
#define PIN_DS18B20       18      // DS18B20 1-Wire data pin
#define PIN_LED_RED       25      // Red LED (Alert tier)
#define PIN_LED_BLUE      26      // Blue LED (Warning/Watch tier)
#define PIN_LED_YELLOW    PIN_LED_BLUE // Compatibility alias
#define PIN_LED_GREEN     27      // Green LED (Normal/Safe tier)
#define PIN_BOOT_BUTTON   0       // Built-in ESP32 BOOT button

// =============================================================
// 3. HARDWARE INSTANCES & STATE
// =============================================================
DHT dht(PIN_DHT22, DHT22);
OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);

unsigned long lastUploadTime = 0;
int seqNumber = 0;
int failedUploadsInRow = 0;
bool isOfflineMode = false;
volatile bool buttonPressedFlag = false;
unsigned long lastButtonInterrupt = 0;

String currentAlertLevel = "Normal";

// =============================================================
// 4. RGB/RBG LED CONTROLLER (NON-BLOCKING)
// =============================================================
void setLeds(bool red, bool blue, bool green) {
  digitalWrite(PIN_LED_RED, red ? HIGH : LOW);
  digitalWrite(PIN_LED_BLUE, blue ? HIGH : LOW);
  digitalWrite(PIN_LED_GREEN, green ? HIGH : LOW);
}

void turnAllLedsOff() {
  setLeds(false, false, false);
}

// Drive RGB LED patterns smoothly based on alert level
// Normal condition is strictly Solid Green (no red, no blue)
void updateLedPattern() {
  unsigned long now = millis();

  if (currentAlertLevel == "Alert") {
    // ALERT TIER (WBGT >= 32.2°C): Emergency Fast Red Flash (200ms ON / 200ms OFF)
    bool redState = (now % 400) < 200;
    setLeds(redState, false, false);
  }
  else if (currentAlertLevel == "Warning") {
    // WARNING TIER (WBGT 30.0°C - 32.2°C): Double Blue Blink
    unsigned long cycle = now % 1000;
    bool blueState = (cycle < 150) || (cycle >= 250 && cycle < 400);
    setLeds(false, blueState, false);
  }
  else if (currentAlertLevel == "Watch") {
    // WATCH TIER (WBGT 28.0°C - 30.0°C): Solid Blue Caution
    setLeds(false, true, false);
  }
  else {
    // NORMAL TIER (WBGT < 28.0°C): Solid Green Safe
    setLeds(false, false, true);
  }
}
void updateRgyLedPattern() { updateLedPattern(); } // Compatibility alias

// Self-Test Sweep on Boot: Green -> Blue -> Red -> All On -> Green
void runLedSelfTest() {
  Serial.println("[LEDs] Running power-on self-test...");
  setLeds(false, false, true); delay(350); // Green
  setLeds(false, true, false); delay(350); // Blue
  setLeds(true, false, false); delay(350); // Red
  setLeds(true, true, true);   delay(300); // All on
  turnAllLedsOff();            delay(200); // All off
  setLeds(false, false, true);             // Ready (Green)
}

// =============================================================
// 5. BOOT BUTTON ISR (OPERATOR ACKNOWLEDGEMENT)
// =============================================================
void IRAM_ATTR handleButtonInterrupt() {
  unsigned long now = millis();
  if (now - lastButtonInterrupt > 300) { // 300ms software debounce
    buttonPressedFlag = true;
    lastButtonInterrupt = now;
  }
}

// =============================================================
// 6. STULL PSYCHROMETRICS & WBGT FORMULATION
// =============================================================
float computeStullWetBulb(float T, float RH) {
  if (RH < 1.0) RH = 1.0;
  if (RH > 100.0) RH = 100.0;
  float Tw = T * atan(0.151977 * sqrt(RH + 8.313659))
           + atan(T + RH)
           - atan(RH - 1.676331)
           + 0.00391838 * pow(RH, 1.5) * atan(0.023101 * RH)
           - 4.686035;
  return Tw;
}

float computeEstimatedWbgt(float T_air, float RH, float T_globe) {
  float T_wb = computeStullWetBulb(T_air, RH);
  // Outdoor formula (ISO 7243): 70% natural wet-bulb + 20% radiant globe + 10% dry-bulb
  float wbgt = (0.70 * T_wb) + (0.20 * T_globe) + (0.10 * T_air);
  return wbgt;
}

// =============================================================
// 7. SETUP
// =============================================================
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==================================================");
  Serial.println("  Munzir Sentinel — RGY LED Heat Node Initializing");
  Serial.println("==================================================");

  // Initialize LED Pins
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_YELLOW, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  runLedSelfTest();

  // Initialize BOOT Button
  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_BOOT_BUTTON), handleButtonInterrupt, FALLING);

  // Initialize Sensors
  dht.begin();
  ds18b20.begin();
  ds18b20.setResolution(11); // 11-bit resolution: 0.125°C precision, 375ms conversion
  ds18b20.setWaitForConversion(false); // Non-blocking

  // Connect to Wi-Fi
  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);
  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    // Blink Blue during connection attempt
    digitalWrite(PIN_LED_BLUE, !digitalRead(PIN_LED_BLUE));
    attempts++;
  }

  // Clean LED states after connection phase
  turnAllLedsOff();

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    isOfflineMode = false;
  } else {
    Serial.println("\n[WiFi] Connection timeout. Operating in autonomous OFFLINE edge mode.");
    isOfflineMode = true;
  }

  // Ensure initial normal state is Solid Green (Safe)
  currentAlertLevel = "Normal";
  setLeds(false, false, true);
}

// =============================================================
// 8. TELEMETRY TRANSMISSION & SERVER SYNC
// =============================================================
void uploadTelemetry() {
  // Read Sensors
  float airTemp = dht.readTemperature();
  float humidity = dht.readHumidity();

  ds18b20.requestTemperatures();
  float globeTemp = ds18b20.getTempCByIndex(0);

  bool dhtOk = (!isnan(airTemp) && !isnan(humidity) && airTemp > -10.0 && airTemp < 65.0 && humidity >= 0 && humidity <= 100);
  bool globeOk = (!isnan(globeTemp) && globeTemp > -10.0 && globeTemp < 85.0 && globeTemp != -127.0 && globeTemp != 85.0);

  float wbgtEst = 0.0;
  if (dhtOk) {
    wbgtEst = computeEstimatedWbgt(airTemp, humidity, globeOk ? globeTemp : airTemp);
  }

  Serial.println("--------------------------------------------------");
  Serial.printf("[Sensors] Air: %.1f °C | RH: %.1f %% | Globe: %.1f °C | Est WBGT: %.1f °C\n",
                airTemp, humidity, globeTemp, wbgtEst);

  // If offline fallback mode: determine alert tier locally from WBGT thresholds
  if (WiFi.status() != WL_CONNECTED) {
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) isOfflineMode = true;

    if (wbgtEst >= 32.2) currentAlertLevel = "Alert";
    else if (wbgtEst >= 30.0) currentAlertLevel = "Warning";
    else if (wbgtEst >= 28.0) currentAlertLevel = "Watch";
    else currentAlertLevel = "Normal";

    Serial.println("[Local Fallback] Tier: " + currentAlertLevel);
    return;
  }

  // Build JSON Payload
#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<512> doc;
#endif

  doc["node_id"] = NODE_ID;
  doc["seq"] = ++seqNumber;

  char tsBuffer[32];
  snprintf(tsBuffer, sizeof(tsBuffer), "2026-11-16T%02d:%02d:%02dZ",
           (int)((millis() / 3600000) % 24), (int)((millis() / 60000) % 60), (int)((millis() / 1000) % 60));
  doc["ts"] = tsBuffer;

  if (dhtOk) {
    doc["air_temp_c"] = round(airTemp * 10.0) / 10.0;
    doc["rh_pct"] = round(humidity * 10.0) / 10.0;
  } else {
    doc["air_temp_c"] = (char*)NULL;
    doc["rh_pct"] = (char*)NULL;
  }

  if (globeOk) {
    doc["globe_temp_c"] = round(globeTemp * 10.0) / 10.0;
  } else {
    doc["globe_temp_c"] = (char*)NULL;
  }

  if (dhtOk) {
    doc["wbgt_est_c"] = round(wbgtEst * 10.0) / 10.0;
  } else {
    doc["wbgt_est_c"] = (char*)NULL;
  }

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonObject ok = doc["ok"].to<JsonObject>();
#else
  JsonObject ok = doc.createNestedObject("ok");
#endif
  ok["dht"] = dhtOk;
  ok["globe"] = globeOk;
  ok["rssi"] = WiFi.RSSI();

  String jsonString;
  serializeJson(doc, jsonString);

  // Send HTTP POST to Munzir Backend
  HTTPClient http;
  String uploadUrl = String(MUNZIR_API_BASE) + "/api/v1/sentinel/upload";
  http.begin(uploadUrl);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Sentinel-Key", SENTINEL_API_KEY);
  http.setTimeout(4000);

  int httpCode = http.POST(jsonString);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("[HTTP 200] Server Response: " + response);

#if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument respDoc;
#else
    StaticJsonDocument<256> respDoc;
#endif
    DeserializationError error = deserializeJson(respDoc, response);

    if (!error) {
      if (respDoc.containsKey("level")) {
        currentAlertLevel = respDoc["level"].as<String>();
      }
      failedUploadsInRow = 0;
      isOfflineMode = false;
      Serial.println("[Sentinel] Active Tier from Munzir Server: " + currentAlertLevel);
    }
  } else {
    Serial.printf("[HTTP Error] Code: %d - Evaluating tier locally on edge node\n", httpCode);
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) {
      isOfflineMode = true;
    }
    // Autonomous Edge Fallback: calculate tier directly from physical sensors
    if (wbgtEst >= 32.2) currentAlertLevel = "Alert";
    else if (wbgtEst >= 30.0) currentAlertLevel = "Warning";
    else if (wbgtEst >= 28.0) currentAlertLevel = "Watch";
    else currentAlertLevel = "Normal";
    Serial.println("[Local Fallback] Active Tier: " + currentAlertLevel);
  }
  http.end();
}

// Send Manual Operator Acknowledgement (BOOT Button Pressed)
void sendButtonAck() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Ack] Button pressed while offline.");
    return;
  }

  HTTPClient http;
  String ackUrl = String(MUNZIR_API_BASE) + "/api/v1/sentinel/ack";
  http.begin(ackUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);

  String ackPayload = "{\"node_id\":\"" + String(NODE_ID) + "\",\"action\":\"BUTTON_ACK\"}";
  int code = http.POST(ackPayload);
  Serial.printf("[Ack] Operator ACK dispatched, response code: %d\n", code);
  http.end();
}

// =============================================================
// 9. MAIN LOOP
// =============================================================
void loop() {
  unsigned long now = millis();

  // 1. Maintain RGY LED Pattern (runs continuously without delay)
  updateRgyLedPattern();

  // 2. Handle Operator BOOT Button Press
  if (buttonPressedFlag) {
    buttonPressedFlag = false;
    Serial.println("[Event] BOOT Button pressed! Dispatching supervisor ACK...");
    // Visual confirmation: Quick triple blink of Blue LED
    for (int i = 0; i < 3; i++) {
      setLeds(false, true, false); delay(80);
      turnAllLedsOff(); delay(80);
    }
    sendButtonAck();
  }

  // 3. Periodic Telemetry Upload (Every 5 seconds)
  if (now - lastUploadTime >= UPLOAD_INTERVAL_MS) {
    lastUploadTime = now;
    uploadTelemetry();
  }

  delay(20); // Yield to background Wi-Fi and RTOS tasks
}

