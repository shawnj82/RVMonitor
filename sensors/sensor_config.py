"""
Sensor configuration – maps ESP32 flow-meter module IDs to stream routing.

Add one entry per deployed ESP32 module. Each module publishes two flow
meters and one relay. Each meter should define a ``stream_id`` and a
``routing`` rule with:
    - ``inputs`` (optional upstream streams),
    - ``outputs`` (destination banks + proportions),
    - ``input_policy`` (``weighted`` or ``any_active``),
    - ``priority`` and optional ``source_bank`` for depletion accounting.
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
            "stream_id": "fresh_water_out",
            "description": "Fresh water tank outflow",
            "routing": {
                "priority": 0,
                "input_policy": "weighted",
                "inputs": [],
                "outputs": [
                    {"bank": "grey", "proportion": 0.5},
                    {"bank": "black", "proportion": 0.5},
                ],
                "source_bank": "fresh",
            },
        },
        "flow2": {
            "stream_id": "city_water_in",
            "description": "City water hookup inflow",
            "routing": {
                "priority": 0,
                "input_policy": "weighted",
                "inputs": [],
                "outputs": [
                    {"bank": "grey", "proportion": 0.5},
                    {"bank": "black", "proportion": 0.5},
                ],
                "source_bank": None,
            },
        },
    },
}
