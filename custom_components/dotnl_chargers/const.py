"""Constants for the DOT-NL Chargers integration."""

from __future__ import annotations

from homeassistant.const import Platform

DOMAIN = "dotnl_chargers"
NAME = "DOT-NL Chargers"
MANUFACTURER = "DonTranQuiL"
VERSION = "0.1.3"
ATTRIBUTION = "Data © NDW / DOT-NL (AFIR open data)"

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.DEVICE_TRACKER,
    Platform.BUTTON,
]

# Upstream endpoints
GEOJSON_URL = (
    "https://dotnl.ndw.nu/api/rest/geojson/dynamic-road-status/"
    "charge-point-data/v1/features"
)
TARIFFS_URL = "https://opendata.ndw.nu/charging_point_tariffs_ocpi.json.gz"

USER_AGENT = f"HomeAssistant-DotNL-Chargers/{VERSION}"

# API limits
MAX_BBOX_AREA_DEG2 = 1.0
MAX_FEATURES = 1000
KM_PER_DEG_LAT = 111.0

# Config keys
CONF_INSTANCE_NAME = "instance_name"
CONF_LATITUDE = "latitude"
CONF_LONGITUDE = "longitude"
CONF_RADIUS_KM = "radius_km"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_MIN_AVAILABLE = "min_available"
CONF_POWER_MIN_KW = "power_min_kw"
CONF_ENABLE_MAP_TRACKERS = "enable_map_trackers"
CONF_ENABLE_TARIFF_ENRICHMENT = "enable_tariff_enrichment"
CONF_MAX_MAP_MARKERS = "max_map_markers"
CONF_SHOW_ONLY_OPEN = "show_only_open"

# Defaults
DEFAULT_RADIUS_KM = 2.0
DEFAULT_SCAN_INTERVAL = 120
MIN_SCAN_INTERVAL = 60
DEFAULT_MIN_AVAILABLE = 0
DEFAULT_POWER_MIN_KW = 0.0
DEFAULT_ENABLE_MAP_TRACKERS = True
DEFAULT_ENABLE_TARIFF_ENRICHMENT = True
DEFAULT_MAX_MAP_MARKERS = 40
DEFAULT_SHOW_ONLY_OPEN = False

# History / tracker
HISTORY_MAX = 50
TARIFF_REFRESH_SECONDS = 6 * 3600  # 6 hours (max cadence 6–12h)

# Bus events
EVENT_ENTRY = f"{DOMAIN}_entry"
EVENT_EXIT = f"{DOMAIN}_exit"

# Item field whitelist
ITEM_FIELDS = (
    "id",
    "name",
    "latitude",
    "longitude",
    "distance_km",
    "address",
    "operator",
    "cpo_id",
    "open",
    "available",
    "total",
    "occupied",
    "status",
    "connectors",
    "max_power_kw",
    "energy_price_eur_kwh",
    "tariff_ids",
    "last_updated",
)

STATUS_AVAILABLE = "available"
STATUS_PARTIAL = "partial"
STATUS_OCCUPIED = "occupied"
STATUS_UNKNOWN = "unknown"
