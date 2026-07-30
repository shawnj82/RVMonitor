"""
Sensor configuration – maps ESP32 flow-meter module IDs to RV tank roles.

Add one entry per deployed ESP32 module.  Each module publishes two flow
meters and one relay; the ``role`` field tells the Pi-side logic layer what
each meter is measuring.

Supported roles
---------------
``fresh_water_out``
    Water drawn from the fresh-water tank.  Decreases the fresh level and
    increases grey + black levels at the configured split ratios.

``city_water_in``
    Water entering from a city hookup.  Does **not** draw from the fresh tank,
    but does increase grey + black levels (water still goes somewhere after use).

Add new roles here and handle them in ``logic/tank_logic.py`` as needed.
"""

from __future__ import annotations

# ── MQTT broker (the Raspberry Pi or desktop running the broker) ──────────────
MQTT_BROKER: str = "localhost"
MQTT_PORT: int = 1883

# ── Deployed sensor modules ───────────────────────────────────────────────────
# Keys are the SENSOR_ID values configured on each ESP32 module.
SENSOR_MODULES: dict[str, dict] = {
    "flow_module_01": {
        "description": "Bay-area fresh-water and city-water meters + pump relay",
        "flow1": {
            "role": "fresh_water_out",
            "description": "Fresh water tank outflow",
        },
        "flow2": {
            "role": "city_water_in",
            "description": "City water hookup inflow",
        },
    },
}
