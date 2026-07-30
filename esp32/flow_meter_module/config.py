"""
ESP32 Flow Meter Module – build-time configuration.

Edit the values in this file before flashing to the ESP32.
Create a ``config_local.py`` (git-ignored) alongside this file to override
individual settings without modifying tracked source:

    # config_local.py
    from config import *
    WIFI_SSID = "MyActualSSID"
    WIFI_PASSWORD = "MyActualPassword"
    MQTT_BROKER = "192.168.1.50"

Then import ``config_local`` instead of ``config`` in main.py.
"""

# ── WiFi ──────────────────────────────────────────────────────────────────────
WIFI_SSID: str = "YourNetworkSSID"
WIFI_PASSWORD: str = "YourNetworkPassword"
WIFI_CONNECT_TIMEOUT_SEC: int = 15

# ── MQTT broker ───────────────────────────────────────────────────────────────
# Point this at the Raspberry Pi (or desktop) running the RV Monitor broker.
MQTT_BROKER: str = "192.168.1.100"
MQTT_PORT: int = 1883
MQTT_KEEPALIVE_SEC: int = 60

# Each module instance needs its own unique client ID on the broker.
MQTT_CLIENT_ID: str = "esp32_flow_module_01"

# ── Sensor identity ───────────────────────────────────────────────────────────
# Used as part of every MQTT topic published by this module.
# Change when deploying more than one flow-meter module on the same network.
SENSOR_ID: str = "flow_module_01"

# ── Publish timing ────────────────────────────────────────────────────────────
# How often (seconds) the module samples the flow meters and publishes data.
PUBLISH_INTERVAL_SEC: int = 5

# ── Simulated sensor bounds (used until real hardware is attached) ─────────────
# Random GPM values are drawn uniformly from [FLOW_MIN_GPM, FLOW_MAX_GPM].
FLOW_MIN_GPM: float = 1.0
FLOW_MAX_GPM: float = 3.0
