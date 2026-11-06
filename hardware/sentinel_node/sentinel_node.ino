/**
 * Munzir Sentinel — On-Site WBGT Microclimate Hardware Node
 * Firmware for ESP32 DevKit + DHT22 + DS18B20 Black Globe + RGB LED
 * 
 * Functions:
 * 1. Reads air temp, humidity, and globe temperature every 60 seconds
 * 2. Computes Stull natural wet-bulb and estimated WBGT
 * 3. Transmits telemetry to Munzir REST API
 * 4. Receives calibrated alert level and drives on-board multi-pattern RGB LED
 * 5. Handles on-board BOOT button for on-site operator acknowledgement
 * 6. Graceful offline fallback with blue-blip status pattern
 */

#include <WiFi.h>
#include <HTTPClient.h>
#include <DHT.h>
#include <OneWire.h>
#include <DallasTemperature.h>
#include <ArduinoJson.h> // Library: ArduinoJson by Benoit Blanchon (v6 or v7)
#include <math.h>

#include "config.h"

// --- Hardware Sensors ---
DHT dht(PIN_DHT22, DHT22);
OneWire oneWire(PIN_DS18B20);
DallasTemperature ds18b20(&oneWire);

// --- Operational State Variables ---
unsigned long lastUploadTime = 0;
unsigned long validUntilEpoch = 0;
int seqNumber = 0;
int failedUploadsInRow = 0;
bool isOfflineMode = false;
volatile bool buttonPressedFlag = false;
unsigned long lastButtonInterrupt = 0;

String currentAlertLevel = "None";

// --- LED Helper Functions ---
void setRgbColor(uint8_t r, uint8_t g, uint8_t b) {
  if (LED_COMMON_ANODE) {
    r = 255 - r;
    g = 255 - g;
    b = 255 - b;
  }
  analogWrite(PIN_LED_RED, r);
  analogWrite(PIN_LED_GREEN, g);
  analogWrite(PIN_LED_BLUE, b);
}

void turnLedOff() {
  setRgbColor(0, 0, 0);
}

// Drive LED pattern non-blocking
void updateLedPattern() {
  unsigned long now = millis();

  if (isOfflineMode) {
    // Blue blip pattern (100ms blue flash every 2 seconds)
    if ((now % 2000) < 100) {
      setRgbColor(0, 0, 255); // Blue flash
    } else {
      // Local fallback colour
      setRgbColor(0, 60, 0);  // Dim green
    }
    return;
  }

  if (currentAlertLevel == "Alert") {
    // Fast Red Blink (250ms on / 250ms off)
    if ((now % 500) < 250) {
      setRgbColor(255, 0, 0); // Bright Red
    } else {
      turnLedOff();
    }
  } else if (currentAlertLevel == "Warning") {
    // Double Orange Blink
    unsigned long cycle = now % 1000;
    if ((cycle < 150) || (cycle >= 250 && cycle < 400)) {
      setRgbColor(255, 90, 0); // Orange
    } else {
      turnLedOff();
    }
  } else if (currentAlertLevel == "Watch") {
    // Slow Yellow Blink (1 Hz)
    if ((now % 1000) < 500) {
      setRgbColor(255, 180, 0); // Yellow
    } else {
      turnLedOff();
    }
  } else {
    // Normal: Solid Green
    setRgbColor(0, 200, 0);
  }
}

// --- BOOT Button ISR ---
void IRAM_ATTR handleButtonInterrupt() {
  unsigned long now = millis();
  // 300ms debounce
  if (now - lastButtonInterrupt > 300) {
    buttonPressedFlag = true;
    lastButtonInterrupt = now;
  }
}

// --- Micrometeorological Physics (Stull 2011) ---
float computeStullWetBulb(float t, float rh) {
  if (rh < 1.0) rh = 1.0;
  if (rh > 100.0) rh = 100.0;
  
  float tw = t * atan(0.151977 * sqrt(rh + 8.313659))
           + atan(t + rh)
           - atan(rh - 1.676331)
           + 0.00391838 * pow(rh, 1.5) * atan(0.023101 * rh)
           - 4.686035;
  return tw;
}

float computeEstimatedWbgt(float tAir, float rh, float tGlobe, bool indoor) {
  float tnw = computeStullWetBulb(tAir, rh);
  float wbgt = 0.0;
  if (indoor || isnan(tGlobe)) {
    float tgEffective = isnan(tGlobe) ? tAir : tGlobe;
    wbgt = 0.7 * tnw + 0.3 * tgEffective;
  } else {
    wbgt = 0.7 * tnw + 0.2 * tGlobe + 0.1 * tAir;
  }
  return wbgt;
}

// --- Wi-Fi Connection Management ---
void ensureWiFiConnected() {
  if (WiFi.status() == WL_CONNECTED) return;

  Serial.print("[WiFi] Connecting to 2.4GHz network: ");
  Serial.println(WIFI_SSID);

  WiFi.mode(WIFI_STA);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

  int attempts = 0;
  while (WiFi.status() != WL_CONNECTED && attempts < 20) {
    delay(500);
    Serial.print(".");
    // Pulse cyan during connection attempt
    setRgbColor(0, 50, 50);
    delay(100);
    turnLedOff();
    attempts++;
  }

  if (WiFi.status() == WL_CONNECTED) {
    Serial.println("\n[WiFi] Connected! IP: " + WiFi.localIP().toString());
    configTime(0, 0, "pool.ntp.org", "time.google.com");
  } else {
    Serial.println("\n[WiFi] Connection timeout. Operating in offline mode.");
    isOfflineMode = true;
  }
}

// --- Telemetry Upload ---
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
    wbgtEst = computeEstimatedWbgt(airTemp, humidity, globeOk ? globeTemp : airTemp, INDOOR_MODE_DEFAULT);
  }

  Serial.println("----------------------------------------------");
  Serial.printf("[Sensors] Air: %.1f °C | RH: %.1f %% | Globe: %.1f °C | Est WBGT: %.1f °C\n", 
                airTemp, humidity, globeTemp, wbgtEst);

  if (WiFi.status() != WL_CONNECTED) {
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) isOfflineMode = true;
    return;
  }

  // 2. Build JSON
  StaticJsonDocument<512> doc;
  doc["node_id"] = NODE_ID;
  doc["seq"] = ++seqNumber;
  
  // Format current ISO timestamp
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

  JsonObject ok = doc.createNestedObject("ok");
  ok["dht"] = dhtOk;
  ok["globe"] = globeOk;
  ok["rssi"] = WiFi.RSSI();

  String jsonString;
  serializeJson(doc, jsonString);

  // 3. POST to Munzir REST API
  HTTPClient http;
  String uploadUrl = String(MUNZIR_API_BASE) + "/api/v1/sentinel/upload";
  http.begin(uploadUrl);
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Sentinel-Key", SENTINEL_API_KEY);
  http.setTimeout(5000); // 5-second SLA timeout

  Serial.print("[HTTP] POST ");
  Serial.println(uploadUrl);

  int httpCode = http.POST(jsonString);

  if (httpCode == 200) {
    String response = http.getString();
    Serial.println("[HTTP] Response: " + response);

    StaticJsonDocument<256> respDoc;
    DeserializationError error = deserializeJson(respDoc, response);

    if (!error) {
      currentAlertLevel = respDoc["level"].as<String>();
      failedUploadsInRow = 0;
      isOfflineMode = false;
      Serial.println("[Sentinel] Updated Alert Level: " + currentAlertLevel);
    }
  } else {
    Serial.printf("[HTTP] POST failed, error code: %d\n", httpCode);
    failedUploadsInRow++;
    if (failedUploadsInRow >= 3) {
      Serial.println("[Sentinel] 3 consecutive upload failures. Switching to OFFLINE mode.");
      isOfflineMode = true;
    }
  }
  http.end();
}

// --- Operator Button Acknowledgement Dispatch ---
void sendButtonAck() {
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[Ack] Button pressed while Wi-Fi offline. Local feedback only.");
    return;
  }

  HTTPClient http;
  String ackUrl = String(MUNZIR_API_BASE) + "/api/v1/sentinel/ack";
  http.begin(ackUrl);
  http.addHeader("Content-Type", "application/json");
  http.setTimeout(3000);

  StaticJsonDocument<128> doc;
  doc["node_id"] = NODE_ID;

  String jsonPayload;
  serializeJson(doc, jsonPayload);

  Serial.println("[Ack] Dispatching on-site button acknowledgement to Munzir...");
  int code = http.POST(jsonPayload);
  if (code == 200) {
    Serial.println("[Ack] Confirmed by central server.");
    // Visual flash confirmation (Cyan flash)
    setRgbColor(0, 255, 255);
    delay(200);
  }
  http.end();
}

// --- Main Arduino Setup ---
void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial.println("\n==========================================");
  Serial.println("  Munzir Sentinel — Hardware Node v1.0.0  ");
  Serial.println("  Shade-Mounted On-Site WBGT Microclimate ");
  Serial.println("==========================================");

  // Configure RGB LED pins
  pinMode(PIN_LED_RED, OUTPUT);
  pinMode(PIN_LED_GREEN, OUTPUT);
  pinMode(PIN_LED_BLUE, OUTPUT);
  turnLedOff();

  // Configure on-board BOOT button
  pinMode(PIN_BOOT_BUTTON, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_BOOT_BUTTON), handleButtonInterrupt, FALLING);

  // Initialize sensors
  dht.begin();
  ds18b20.begin();

  // Test LED cycle (Red -> Green -> Blue -> Off)
  setRgbColor(255, 0, 0); delay(200);
  setRgbColor(0, 255, 0); delay(200);
  setRgbColor(0, 0, 255); delay(200);
  turnLedOff();

  // Initial Wi-Fi connection
  ensureWiFiConnected();

  // Perform initial telemetry upload
  uploadTelemetry();
  lastUploadTime = millis();
}

// --- Main Loop ---
void loop() {
  unsigned long now = millis();

  // Check physical button press
  if (buttonPressedFlag) {
    buttonPressedFlag = false;
    sendButtonAck();
  }

  // Periodic telemetry upload every UPLOAD_INTERVAL_MS (60s)
  if (now - lastUploadTime >= UPLOAD_INTERVAL_MS) {
    lastUploadTime = now;
    uploadTelemetry();
  }

  // Continuously animate LED patterns
  updateLedPattern();

  delay(20); // Small loop pacing
}

