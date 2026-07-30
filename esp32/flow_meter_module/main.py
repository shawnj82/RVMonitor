"""
ESP32 Flow Meter Module – MicroPython firmware.

Hardware (phase 1 – simulation):
  • Flow Meter 1  – measures fresh-water outflow (GPM)
  • Flow Meter 2  – measures city-water inflow (GPM)
  • Relay 1       – controls the fresh-water pump (on/off)

MQTT topics published:
  rv/flowmeter/{SENSOR_ID}/flow1   → JSON {"gpm": <float>, "total_gallons": <float>}
  rv/flowmeter/{SENSOR_ID}/flow2   → JSON {"gpm": <float>, "total_gallons": <float>}
  rv/flowmeter/{SENSOR_ID}/relay   → JSON {"state": "on"|"off"}

MQTT topics subscribed:
  rv/flowmeter/{SENSOR_ID}/relay/set → "on" or "off"

Replace the simulated sensor reads with real hardware calls once parts arrive.
"""

import json
import random
import time

import network
import ubinascii
from umqtt.simple import MQTTClient

try:
    import config_local as config  # optional local overrides (git-ignored)
except ImportError:
    import config


# ── Topic helpers ─────────────────────────────────────────────────────────────

def _topic(suffix: str) -> bytes:
    return "rv/flowmeter/{}/{}".format(config.SENSOR_ID, suffix).encode()


TOPIC_FLOW1 = _topic("flow1")
TOPIC_FLOW2 = _topic("flow2")
TOPIC_RELAY_STATUS = _topic("relay")
TOPIC_RELAY_CMD = _topic("relay/set")


# ── Module state ──────────────────────────────────────────────────────────────

_relay_state: bool = False          # False = off, True = on
_total_gallons: list = [0.0, 0.0]   # cumulative totals for meter 1 and meter 2


# ── WiFi ──────────────────────────────────────────────────────────────────────

def connect_wifi() -> None:
    """Connect to the configured WiFi network and block until connected."""
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if not wlan.isconnected():
        print("Connecting to WiFi:", config.WIFI_SSID)
        wlan.connect(config.WIFI_SSID, config.WIFI_PASSWORD)
        deadline = time.time() + config.WIFI_CONNECT_TIMEOUT_SEC
        while not wlan.isconnected():
            if time.time() > deadline:
                raise RuntimeError("WiFi connect timeout")
            time.sleep(0.5)
    print("WiFi connected:", wlan.ifconfig())


# ── MQTT ──────────────────────────────────────────────────────────────────────

def _on_message(topic: bytes, msg: bytes) -> None:
    """Handle inbound MQTT messages (relay commands)."""
    global _relay_state
    if topic == TOPIC_RELAY_CMD:
        command = msg.decode().strip().lower()
        if command == "on":
            _relay_state = True
        elif command == "off":
            _relay_state = False
        else:
            print("Unknown relay command:", command)
            return
        _publish_relay_status(client)
        print("Relay set to:", "on" if _relay_state else "off")


def build_mqtt_client() -> MQTTClient:
    """Create and return a connected MQTT client."""
    client = MQTTClient(
        config.MQTT_CLIENT_ID,
        config.MQTT_BROKER,
        port=config.MQTT_PORT,
        keepalive=config.MQTT_KEEPALIVE_SEC,
    )
    client.set_callback(_on_message)
    client.connect()
    client.subscribe(TOPIC_RELAY_CMD)
    print("MQTT connected to", config.MQTT_BROKER)
    return client


# ── Sensor simulation ─────────────────────────────────────────────────────────

def _read_flow_meter(meter_index: int) -> float:
    """
    Return the current flow rate in GPM for the given meter (0- or 1-based index).

    Replace with a real pulse-count calculation once hardware is attached.
    """
    return round(
        random.uniform(config.FLOW_MIN_GPM, config.FLOW_MAX_GPM), 2
    )


# ── Publish helpers ───────────────────────────────────────────────────────────

def _publish_flow(mqtt_client: MQTTClient, meter_index: int, topic: bytes) -> None:
    global _total_gallons
    gpm = _read_flow_meter(meter_index)
    _total_gallons[meter_index] += gpm * (config.PUBLISH_INTERVAL_SEC / 60.0)
    payload = json.dumps({
        "gpm": gpm,
        "total_gallons": round(_total_gallons[meter_index], 4),
    })
    mqtt_client.publish(topic, payload.encode())


def _publish_relay_status(mqtt_client: MQTTClient) -> None:
    payload = json.dumps({"state": "on" if _relay_state else "off"})
    mqtt_client.publish(TOPIC_RELAY_STATUS, payload.encode())


# ── Main loop ─────────────────────────────────────────────────────────────────

client = None  # module-level so _on_message can reference it


def main() -> None:
    global client
    connect_wifi()
    client = build_mqtt_client()

    # Publish initial relay state so the broker has a current reading.
    _publish_relay_status(client)

    while True:
        # Check for inbound commands (non-blocking).
        client.check_msg()

        # Publish both flow meter readings.
        _publish_flow(client, 0, TOPIC_FLOW1)
        _publish_flow(client, 1, TOPIC_FLOW2)

        time.sleep(config.PUBLISH_INTERVAL_SEC)


if __name__ == "__main__":
    main()
