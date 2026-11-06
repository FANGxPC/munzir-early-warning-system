/**
 * Munzir Sentinel — Hardware Node (Buzzer Edition)
 * Complete standalone sketch for ESP32 DevKit + DHT22 + DS18B20 + Buzzer
 * 
 * Hardware Connections:
 * -------------------------------------------------------------
 *  DHT22 VCC      -> ESP32 3V3
 *  DHT22 GND      -> ESP32 GND
 *  DHT22 DATA     -> ESP32 GPIO 4
 * 
 *  DS18B20 VCC    -> ESP32 3V3 (Red wire)
 *  DS18B20 GND    -> ESP32 GND (Black wire)
 *  DS18B20 DATA   -> ESP32 GPIO 18 (Yellow wire)
 *  ** Resistor: 4.7k ohm bridging GPIO 18 and 3V3 **
 * 
 *  Buzzer (+)     -> ESP32 GPIO 25 (Optional 100-220 ohm resistor)
 *  Buzzer (-)     -> ESP32 GND
 * 
 *  BOOT Button    -> ESP32 GPIO 0 (Built-in on ESP32 board)
 * -------------------------------------------------------------
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h>
#include <math.h>

// =============================================================
// 1. NETWORK & BACKEND CONFIGURATION (EDIT THESE 3 LINES)
// =============================================================
#define WIFI_SSID         "Your_WiFi_Name"         // Must be 2.4 GHz Wi-Fi or Phone Hotspot
#define WIFI_PASSWORD     "Your_WiFi_Password"     // Wi-Fi password
#define MUNZIR_API_BASE   "http://192.168.149.27:8000" // Your laptop IP running `make serve`

// Node & Security Parameters
#define NODE_ID           "SENT-001"
#define SENTINEL_API_KEY  "munzir_sentinel_secret_2026"
#define UPLOAD_INTERVAL_MS 6000    // Telemetry sample rate: 5 seconds (responsive live updates)

// =============================================================
// 2. PIN ASSIGNMENTS
// =============================================================
#define PIN_DHT22         4       // DHT22 data pin
#define PIN_DS18B20       18      // DS18B20 1-Wire data pin
#define PIN_BUZZER        25      // Buzzer positive (+) pin
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

String currentAlertLevel = "None"; // None, Watch, Warning, Alert

// --- BOOT Button Interrupt Service Routine ---
void IRAM_ATTR handleButtonInterrupt() {
  unsigned long now = millis();
  if (now - lastButtonInterrupt > 300) { // 300ms debounce
    buttonPressedFlag = true;
    lastButtonInterrupt = now;
  }
}

// --- Micrometeorological Wet-Bulb & WBGT (Stull 2011) ---
float computeStullWetBulb(float t, float rh) {
  if (rh < 1.0) rh = 1.0;
  if (rh > 100.0) rh = 100.0;
  return t * atan(0.151977 * sqrt(rh + 8.313659))
       + atan(t + rh)
       - atan(rh - 1.676331)
       + 0.00391838 * pow(rh, 1.5) * atan(0.023101 * rh)
       - 4.686035;
}

float computeEstimatedWbgt(float tAir, float rh, float tGlobe) {
  float tnw = computeStullWetBulb(tAir, rh);
  if (isnan(tGlobe)) {
    return 0.7 * tnw + 0.3 * tAir;
  }
  return 0.7 * tnw + 0.2 * tGlobe + 0.1 * tAir;
}

// --- Universal Buzzer Driver (Supports both Active & Passive Buzzers) ---
void soundBuzzer(bool on) {
  if (on) {
    tone(PIN_BUZZER, 2000);
  } else {
    noTone(PIN_BUZZER);
    digitalWrite(PIN_BUZZER, LOW);
  }
}

// --- Buzzer Pattern Player (Non-Blocking) ---
void updateBuzzerPattern() {
  unsigned long now = millis();

  if (isOfflineMode) {
    soundBuzzer(false);
    return;
  }

  if (currentAlertLevel == "Alert") {
    // Fast Emergency Alarm: 4 beeps per second (125ms ON / 125ms OFF)
    bool beepState = (now % 250) < 125;
    soundBuzzer(beepState);

  } else if (currentAlertLevel == "Warning") {
    // Preventive Warning: Double chirp every second [100ms ON, 100ms OFF, 100ms ON, 700ms OFF]
    unsigned long cycle = now % 1000;
    bool beepState = (cycle < 100) || (cycle >= 200 && cycle < 300);
    soundBuzzer(beepState);

  } else if (currentAlertLevel == "Watch") {
    // Active Watch: Single soft chirp every 2 seconds (80ms ON)
    unsigned long cycle = now % 2000;
    bool beepState = (cycle < 80);
    soundBuzzer(beepState);

  } else {
    // Normal / Baseline: Completely silent
    soundBuzzer(false);
  }
}

// --- Wi-Fi Connection Manager ---
void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WiFi] Connecting to: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    configTime(0, 0, "pool.ntp.org", "time.google.com");
    isOfflineMode = false;
  } else {
    Serial.println("\n[WiFi] Connection timeout. Operating in offline mode.");
    isOfflineMode = true;
  }
}

// --- Telemetry Upload to Central Munzir Server ---
void uploadTelemetry() {
  ensureWiFiConnected();

  // 1. Read Sensors
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

  if (WiFi.status() != WL_CONNECTED) {
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) isOfflineMode = true;
    return;
  }

  // 2. Build Inbound JSON Payload (Compatible with ArduinoJson v6 and v7)
#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<512> doc;
#endif

  doc["node_id"] = NODE_ID;
  doc["seq"] = ++seqNumber;

  char tsBuffer[32];
  time_t nowSecs = time(nullptr);
  if (nowSecs > 100000000) {
    struct tm *utc = gmtime(&nowSecs);
    strftime(tsBuffer, sizeof(tsBuffer), "%Y-%m-%dT%H:%M:%SZ", utc);
  } else {
    snprintf(tsBuffer, sizeof(tsBuffer), "2026-11-06T%02d:%02d:%02dZ",
             (int)((millis() / 3600000) % 24), (int)((millis() / 60000) % 60), (int)((millis() / 1000) % 60));
  }
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

  // 3. Transmit HTTP POST to Munzir
  HTTPClient http;
  String uploadUrl = String(MUNZIR_API_BASE) + "/api/v1/sentinel/upload";
  http.begin(uploadUrl);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Sentinel-Key", SENTINEL_API_KEY);
  http.setTimeout(5000);

  Serial.print("[HTTP] POST ");
  Serial.println(uploadUrl);

  int httpCode = http.POST(jsonString);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("[HTTP] Response: " + response);

#if ARDUINOJSON_VERSION_MAJOR >= 7
    JsonDocument respDoc;
#else
    StaticJsonDocument<256> respDoc;
#endif
    DeserializationError error = deserializeJson(respDoc, response);

    if (!error) {
      currentAlertLevel = respDoc["level"].as<String>();
      failedUploadsInRow = 0;
      isOfflineMode = false;
      Serial.println("[Sentinel] Active Alert Level: " + currentAlertLevel);
    }
  } else {
    Serial.printf("[HTTP] POST failed, code: %d\n", httpCode);
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) {
      Serial.println("[Sentinel] 3 upload failures. Switching to OFFLINE mode.");
      isOfflineMode = true;
    }
  }
  http.end();
}

// --- Operator Button Acknowledgment Dispatch ---
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

#if ARDUINOJSON_VERSION_MAJOR >= 7
  JsonDocument doc;
#else
  StaticJsonDocument<128> doc;
#endif
  doc["node_id"] = NODE_ID;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.println("[Ack] Sending on-site operator acknowledgement to Munzir...");
  int code = http.POST(jsonPayload);
  if (code == 200) {
    Serial.println("[Ack] Confirmed by central server.");
    // Audio feedback: Two quick chirps
    soundBuzzer(true);  delay(80);
    soundBuzzer(false); delay(60);
    soundBuzzer(true);  delay(80);
    soundBuzzer(false);
  }
  http.end();
}

// --- Arduino Setup ---
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==========================================");
  Serial.println("  Munzir Sentinel — Node (Buzzer Edition) ");
  Serial.println("==========================================");

  // Configure Buzzer Pin
  pinMode(PIN_BUZZER, OUTPUT);
  soundBuzzer(false);

  // Power-on test chirp (confirms buzzer is connected)
  soundBuzzer(true);
  delay(150);
  soundBuzzer(false);

  // Configure on-board BOOT button
  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_BOOT_BUTTON), handleButtonInterrupt, FALLING);

  // Initialize sensors
  dht.begin();
  ds18b20.begin();

  // Connect to Wi-Fi
  ensureWiFiConnected();

  // Initial upload
  uploadTelemetry();
  lastUploadTime = millis();
}

// --- Arduino Main Loop ---
void loop() {
  unsigned long now = millis();

  // 1. Process physical button acknowledgement
  if (buttonPressedFlag) {
    buttonPressedFlag = false;
    sendButtonAck();
  }

  // 2. Periodic telemetry upload every 60 seconds
  if (now - lastUploadTime >= UPLOAD_INTERVAL_MS) {
    lastUploadTime = now;
    uploadTelemetry();
  }

  // 3. Continuously drive buzzer patterns (non-blocking)
  updateBuzzerPattern();

  delay(20);
}

