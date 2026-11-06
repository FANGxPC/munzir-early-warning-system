#ifndef SENTINEL_CONFIG_H
#define SENTINEL_CONFIG_H

// --- Munzir Sentinel Node Configuration ---
// Adjust these parameters before flashing to your ESP32 DevKit

// 1. Wi-Fi Configuration (2.4 GHz only)
// If using phone hotspot, enable "Maximize Compatibility" / 2.4 GHz mode
#define WIFI_SSID         "Your_WiFi_SSID"
#define WIFI_PASSWORD     "Your_WiFi_Password"

// 2. Munzir Central Platform API URL
// For local testing: "http://<YOUR_LAPTOP_IP>:8000"
// For live Azure Container App: "https://munzir.agreeablestone-12345.uaenorth.azurecontainerapps.io"
#define MUNZIR_API_BASE   "http://192.168.1.100:8000"
#define SENTINEL_API_KEY  "munzir_sentinel_secret_2026"

// 3. Hardware Identity
#define NODE_ID           "SENT-001"

// 4. Pin Assignments (ESP32 DevKit)
#define PIN_DHT22         4       // DHT22 Data pin
#define PIN_DS18B20       18      // DS18B20 1-Wire Data pin (needs 4.7kΩ pull-up to 3.3V)
#define PIN_LED_RED       25      // Red LED channel (through 220Ω resistor)
#define PIN_LED_GREEN     26      // Green LED channel (through 220Ω resistor)
#define PIN_LED_BLUE      27      // Blue LED channel (through 220Ω resistor)
#define PIN_BOOT_BUTTON   0       // Built-in BOOT button (GPIO 0 on standard ESP32)

// 5. LED Type Configuration
// Set to true if common-anode; false if common-cathode
#define LED_COMMON_ANODE  false

// 6. Timing Intervals
#define UPLOAD_INTERVAL_MS   60000   // Telemetry sample rate: 1 minute
#define HEARTBEAT_TIMEOUT_MS 180000  // 3 missed uploads -> switch to offline mode

// 7. Sensor Operational Mode
// true = indoor / canteen mode (no solar radiant term)
// false = outdoor shade mode (includes black globe radiant term)
#define INDOOR_MODE_DEFAULT  false

#endif // SENTINEL_CONFIG_H
