"""
Configuration and regional profiles for PRAHARI.
"""

from pathlib import Path
from typing import Dict, List, Any

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
BRONZE_DIR = DATA_DIR / "bronze"
SILVER_DIR = DATA_DIR / "silver"
GOLD_DIR = DATA_DIR / "gold"
CACHE_DIR = DATA_DIR / "cache"
MODELS_DIR = BASE_DIR / "prahari" / "nlp" / "artifacts"
DETECTION_MODELS_DIR = BASE_DIR / "prahari" / "detection" / "artifacts"

# Small cell suppression threshold (CMS guideline: k <= 10)
SMALL_CELL_K = 10

# Workplace minimum group size (views require >= 50 workers, rates only)
WORKPLACE_MIN_GROUP_SIZE = 50

# Spatial H3 Resolutions
H3_RES_DETECTION = 7  # ~5.16 km2 area
H3_RES_COARSE = 6     # ~36.1 km2 area

# Default Differential Privacy Epsilon (budget per aggregate release)
DEFAULT_DP_EPSILON = 1.0

# WBGT heat stress thresholds (°C)
WBGT_CAUTION = 28.0
WBGT_EXTREME_CAUTION = 30.0
WBGT_DANGER = 32.0

# Supported signal types
SIGNAL_TYPES = [
    "weather_wbgt",
    "air_quality",
    "clinical_syndromic",
    "lab_positivity",
    "workplace_absence",
    "workplace_incident",
]

# --- Sentinel On-Site Hardware Node Configuration ---
SENTINEL_SIGNAL_TYPES = [
    "wbgt_onsite",        # Estimated on-site WBGT from ESP32 sensors
    "air_temp_onsite",    # DHT22 air temperature reading
    "rh_onsite",          # DHT22 relative humidity reading
    "globe_temp_onsite",  # DS18B20 black globe temperature
]

# Sentinel node operational timing and thresholds
SENTINEL_UPLOAD_INTERVAL_SECS = 60         # Expected once per minute
SENTINEL_OFFLINE_THRESHOLD_SECS = 180      # 3 missed uploads = offline
SENTINEL_VALID_UNTIL_BUFFER_SECS = 360     # 6 minutes validity window
SENTINEL_MAX_NODES_PER_SITE = 5            # Limit per worksite

# Sensor sanity bounds (reject physical anomalies or sensor errors)
SENTINEL_BOUNDS = {
    "air_temp_c":   (-10.0, 65.0),    # °C — DHT22 operating range
    "rh_pct":       (0.0, 100.0),     # % — physically bounded
    "globe_temp_c": (-10.0, 85.0),    # °C — black globe solar heating
    "wbgt_est_c":   (-5.0, 50.0),     # °C — derived WBGT bound
}

# Location commissioning accuracy thresholds (metres)
SENTINEL_LOCATION_EXACT_THRESHOLD_M = 50.0
SENTINEL_LOCATION_INFERRED_THRESHOLD_M = 1000.0

# Regional Profiles
REGIONAL_PROFILES: Dict[str, Dict[str, Any]] = {
    "uae": {
        "region_name": "Dubai & Northern Emirates, UAE",
        "state_name": "Dubai",
        "districts": [
            {"id": "DXB-JA", "name": "Jebel Ali Industrial", "lat": 24.9857, "lon": 55.0272, "population": 380000, "urban_type": "industrial"},
            {"id": "DXB-AQ", "name": "Al Quoz Industrial", "lat": 25.1328, "lon": 55.2341, "population": 310000, "urban_type": "industrial"},
            {"id": "DXB-DS", "name": "Dubai South (Expo City)", "lat": 24.8967, "lon": 55.1583, "population": 220000, "urban_type": "development"},
            {"id": "DXB-BB", "name": "Business Bay & Downtown", "lat": 25.1867, "lon": 55.2744, "population": 410000, "urban_type": "commercial"},
            {"id": "DXB-DR", "name": "Deira Central", "lat": 25.2697, "lon": 55.3129, "population": 520000, "urban_type": "dense_urban"},
            {"id": "DXB-BD", "name": "Bur Dubai Historical", "lat": 25.2532, "lon": 55.2974, "population": 460000, "urban_type": "dense_urban"},
            {"id": "DXB-RK", "name": "Ras Al Khor Industrial", "lat": 25.1764, "lon": 55.3482, "population": 190000, "urban_type": "industrial"},
            {"id": "DXB-AB", "name": "Al Barsha & Al Sufouh", "lat": 25.1054, "lon": 55.1973, "population": 280000, "urban_type": "mixed_residential"},
            {"id": "DXB-MU", "name": "Muhaisnah Workforce City", "lat": 25.2811, "lon": 55.4011, "population": 340000, "urban_type": "worker_residential"},
            {"id": "DXB-HT", "name": "Hatta Mountain District", "lat": 24.8153, "lon": 56.1287, "population": 45000, "urban_type": "rural"},
        ],
        "sites": [
            {"id": "SITE-JA-01", "name": "Jebel Ali Deepwater Port Terminal", "district_id": "DXB-JA", "lat": 24.9920, "lon": 55.0410, "workforce": 3200, "site_type": "outdoor_logistics"},
            {"id": "SITE-JA-02", "name": "Jebel Ali Heavy Fabrication Yard", "district_id": "DXB-JA", "lat": 24.9780, "lon": 55.0150, "workforce": 1400, "site_type": "outdoor_industrial"},
            {"id": "SITE-AQ-01", "name": "Al Quoz Structural Steel Yard", "district_id": "DXB-AQ", "lat": 25.1380, "lon": 55.2390, "workforce": 1850, "site_type": "outdoor_construction"},
            {"id": "SITE-AQ-02", "name": "Al Quoz Food Processing & Central Canteen", "district_id": "DXB-AQ", "lat": 25.1290, "lon": 55.2280, "workforce": 950, "site_type": "indoor_food_processing"},
            {"id": "SITE-DS-01", "name": "Dubai South Infrastructure Mega-Site", "district_id": "DXB-DS", "lat": 24.8910, "lon": 55.1620, "workforce": 4200, "site_type": "outdoor_construction"},
            {"id": "SITE-DS-02", "name": "Aviation Cargo Logistics Hub", "district_id": "DXB-DS", "lat": 24.9040, "lon": 55.1510, "workforce": 1600, "site_type": "outdoor_logistics"},
            {"id": "SITE-RK-01", "name": "Ras Al Khor Fleet Maintenance Depot", "district_id": "DXB-RK", "lat": 25.1790, "lon": 55.3520, "workforce": 800, "site_type": "outdoor_transport"},
            {"id": "SITE-BB-01", "name": "Business Bay Commercial Tower Complex", "district_id": "DXB-BB", "lat": 25.1840, "lon": 55.2710, "workforce": 2600, "site_type": "indoor_office"},
            {"id": "SITE-DR-01", "name": "Deira Central Medical Complex", "district_id": "DXB-DR", "lat": 25.2670, "lon": 55.3180, "workforce": 1100, "site_type": "hospital"},
        ],
    },
    "tamilnadu": {
        "region_name": "Tamil Nadu, India",
        "state_name": "Tamil Nadu",
        "districts": [
            {"id": "TN-CHE", "name": "Chennai", "lat": 13.0827, "lon": 80.2707, "population": 7100000, "urban_type": "metro"},
            {"id": "TN-TIR", "name": "Tiruvallur", "lat": 13.1438, "lon": 79.9077, "population": 3728000, "urban_type": "industrial_suburb"},
            {"id": "TN-KAN", "name": "Kanchipuram", "lat": 12.8342, "lon": 79.7036, "population": 1650000, "urban_type": "semi_urban"},
            {"id": "TN-CGL", "name": "Chengalpattu", "lat": 12.6819, "lon": 79.9888, "population": 2550000, "urban_type": "industrial_suburb"},
            {"id": "TN-CBE", "name": "Coimbatore", "lat": 11.0168, "lon": 76.9558, "population": 3458000, "urban_type": "industrial_city"},
            {"id": "TN-MAD", "name": "Madurai", "lat": 9.9252, "lon": 78.1198, "population": 3038000, "urban_type": "urban"},
            {"id": "TN-SLM", "name": "Salem", "lat": 11.6643, "lon": 78.1460, "population": 3482000, "urban_type": "industrial"},
            {"id": "TN-TRZ", "name": "Tiruchirappalli", "lat": 10.7905, "lon": 78.7047, "population": 2722000, "urban_type": "urban"},
        ],
        "sites": [
            {"id": "SITE-TN-01", "name": "Ennore Thermal & Marine Port", "district_id": "TN-TIR", "lat": 13.2300, "lon": 80.3200, "workforce": 2800, "site_type": "outdoor_logistics"},
            {"id": "SITE-TN-02", "name": "Sriperumbudur Electronics SEZ", "district_id": "TN-KAN", "lat": 12.9700, "lon": 79.9400, "workforce": 5200, "site_type": "factory"},
            {"id": "SITE-TN-03", "name": "Ambattur Industrial Estate Fabrication Yard", "district_id": "TN-CHE", "lat": 13.1100, "lon": 80.1600, "workforce": 1900, "site_type": "outdoor_construction"},
            {"id": "SITE-TN-04", "name": "Coimbatore Foundry & Textile Hub", "district_id": "TN-CBE", "lat": 11.0200, "lon": 76.9800, "workforce": 2400, "site_type": "factory"},
            {"id": "SITE-TN-05", "name": "Maraimalai Nagar Automotive Assembly", "district_id": "TN-CGL", "lat": 12.7900, "lon": 80.0200, "workforce": 3100, "site_type": "factory"},
        ],
    },
}

def get_region_config(region_key: str = "uae") -> Dict[str, Any]:
    """Retrieve configuration profile for selected region."""
    key = region_key.lower()
    if key not in REGIONAL_PROFILES:
        raise ValueError(f"Unknown region '{region_key}'. Choose from: {list(REGIONAL_PROFILES.keys())}")
    return REGIONAL_PROFILES[key]

