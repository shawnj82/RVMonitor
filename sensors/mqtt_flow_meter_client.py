"""
MQTT-based Flow Meter client (Pi / desktop side).

Subscribes to the ESP32 flow-meter module topics and feeds received data into
the tank logic layer.  Also exposes a ``set_relay`` command to turn the pump
on or off.

Topic scheme
------------
Published by ESP32 (subscribed here):
  rv/flowmeter/{sensor_id}/flow1   → {"gpm": <float>, "total_gallons": <float>}
  rv/flowmeter/{sensor_id}/flow2   → {"gpm": <float>, "total_gallons": <float>}
  rv/flowmeter/{sensor_id}/relay   → {"state": "on"|"off"}

Published here (subscribed by ESP32):
  rv/flowmeter/{sensor_id}/relay/set → "on" or "off"

Usage
-----
    from sensors.mqtt_flow_meter_client import MqttFlowMeterClient
    from sensors.sensor_config import MQTT_BROKER, MQTT_PORT, SENSOR_MODULES

    client = MqttFlowMeterClient(MQTT_BROKER, MQTT_PORT, SENSOR_MODULES)
    client.connect()
    # The client runs a background thread; data is updated automatically.
    gpm1 = client.get_flow_rate("flow_module_01", meter=1)
    client.set_relay("flow_module_01", on=True)
    client.disconnect()
"""

from __future__ import annotations

import json
import logging
import threading
from typing import Any

import paho.mqtt.client as mqtt

from logic import tank_logic

logger = logging.getLogger(__name__)


class MqttFlowMeterClient:
    """
    MQTT subscriber / publisher for ESP32 flow-meter modules.

    One instance manages *all* configured sensor modules.  Data from each
    module is automatically forwarded to the tank logic layer whenever a new
    MQTT message arrives.
    """

    def __init__(
        self,
        broker: str,
        port: int,
        sensor_modules: dict[str, dict],
    ) -> None:
        self._broker = broker
        self._port = port
        self._sensor_modules = sensor_modules

        # Per-sensor state: {sensor_id: {"flow1": {...}, "flow2": {...}, "relay": {...}}}
        self._state: dict[str, dict[str, Any]] = {
            sid: {
                "flow1": {"gpm": 0.0, "total_gallons": 0.0},
                "flow2": {"gpm": 0.0, "total_gallons": 0.0},
                "relay": {"state": "off"},
            }
            for sid in sensor_modules
        }

        self._lock = threading.Lock()
        self._connected = False

        self._mqtt = mqtt.Client(
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
            client_id="rv_monitor_pi",
        )
        self._mqtt.on_connect = self._on_connect
        self._mqtt.on_message = self._on_message
        self._mqtt.on_disconnect = self._on_disconnect

    # ------------------------------------------------------------------
    # Connection management
    # ------------------------------------------------------------------

    def connect(self) -> bool:
        """
        Connect to the MQTT broker and start the background network loop.

        Returns True when the connection is initiated successfully.
        """
        try:
            self._mqtt.connect(self._broker, self._port, keepalive=60)
            self._mqtt.loop_start()
            logger.info("MqttFlowMeterClient: connecting to %s:%s", self._broker, self._port)
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("MqttFlowMeterClient: connection failed – %s", exc)
            return False

    def disconnect(self) -> None:
        """Stop the background loop and disconnect from the broker."""
        self._mqtt.loop_stop()
        self._mqtt.disconnect()
        self._connected = False
        logger.info("MqttFlowMeterClient: disconnected")

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_flow_rate(self, sensor_id: str, meter: int) -> float:
        """
        Return the latest flow rate in GPM for a specific meter.

        Args:
            sensor_id: The SENSOR_ID of the ESP32 module.
            meter:     1 or 2 (flow meter number).
        """
        key = f"flow{meter}"
        with self._lock:
            return self._state.get(sensor_id, {}).get(key, {}).get("gpm", 0.0)

    def get_total_gallons(self, sensor_id: str, meter: int) -> float:
        """
        Return the cumulative gallons for a specific meter since last ESP32 reset.

        Args:
            sensor_id: The SENSOR_ID of the ESP32 module.
            meter:     1 or 2 (flow meter number).
        """
        key = f"flow{meter}"
        with self._lock:
            return self._state.get(sensor_id, {}).get(key, {}).get("total_gallons", 0.0)

    def get_relay_state(self, sensor_id: str) -> str:
        """Return ``"on"`` or ``"off"`` for the relay on the given module."""
        with self._lock:
            return self._state.get(sensor_id, {}).get("relay", {}).get("state", "off")

    # ------------------------------------------------------------------
    # Commands
    # ------------------------------------------------------------------

    def set_relay(self, sensor_id: str, *, on: bool) -> None:
        """
        Send a relay command to the ESP32 module.

        Args:
            sensor_id: The SENSOR_ID of the target module.
            on:        True to turn the relay on, False to turn it off.
        """
        topic = f"rv/flowmeter/{sensor_id}/relay/set"
        payload = "on" if on else "off"
        self._mqtt.publish(topic, payload)
        logger.info("MqttFlowMeterClient: relay command '%s' → %s", payload, topic)

    # ------------------------------------------------------------------
    # MQTT callbacks
    # ------------------------------------------------------------------

    def _on_connect(self, client, userdata, connect_flags, reason_code, properties) -> None:
        if reason_code.is_failure:
            logger.error("MqttFlowMeterClient: broker refused connection – %s", reason_code)
            return

        self._connected = True
        logger.info("MqttFlowMeterClient: connected to broker")

        # Subscribe to all configured modules.
        for sensor_id in self._sensor_modules:
            base = f"rv/flowmeter/{sensor_id}"
            client.subscribe(f"{base}/flow1")
            client.subscribe(f"{base}/flow2")
            client.subscribe(f"{base}/relay")
            logger.debug("MqttFlowMeterClient: subscribed to topics for %s", sensor_id)

    def _on_disconnect(self, client, userdata, disconnect_flags, reason_code, properties) -> None:
        self._connected = False
        logger.warning("MqttFlowMeterClient: disconnected from broker – %s", reason_code)

    def _on_message(self, client, userdata, msg) -> None:
        """Route inbound messages to state and tank logic updates."""
        topic: str = msg.topic
        try:
            payload: dict = json.loads(msg.payload.decode())
        except (ValueError, UnicodeDecodeError) as exc:
            logger.warning("MqttFlowMeterClient: bad payload on %s – %s", topic, exc)
            return

        # Determine which sensor and sub-topic this message belongs to.
        for sensor_id, module_cfg in self._sensor_modules.items():
            base = f"rv/flowmeter/{sensor_id}"
            if topic == f"{base}/flow1":
                self._handle_flow(sensor_id, "flow1", payload, module_cfg)
                return
            if topic == f"{base}/flow2":
                self._handle_flow(sensor_id, "flow2", payload, module_cfg)
                return
            if topic == f"{base}/relay":
                self._handle_relay(sensor_id, payload)
                return

        logger.debug("MqttFlowMeterClient: unhandled topic %s", topic)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _handle_flow(
        self,
        sensor_id: str,
        meter_key: str,
        payload: dict,
        module_cfg: dict,
    ) -> None:
        gpm = float(payload.get("gpm", 0.0))
        total = float(payload.get("total_gallons", 0.0))

        with self._lock:
            self._state[sensor_id][meter_key] = {"gpm": gpm, "total_gallons": total}

        role = module_cfg.get(meter_key, {}).get("role", "")
        if role == "fresh_water_out":
            tank_logic.update_from_flow_meter(total)
            logger.debug(
                "MqttFlowMeterClient: fresh outflow %.3f gpm, total %.2f gal",
                gpm, total,
            )
        elif role == "city_water_in":
            tank_logic.update_from_city_water_meter(total)
            logger.debug(
                "MqttFlowMeterClient: city water %.3f gpm, total %.2f gal",
                gpm, total,
            )

    def _handle_relay(self, sensor_id: str, payload: dict) -> None:
        state = str(payload.get("state", "off")).lower()
        with self._lock:
            self._state[sensor_id]["relay"] = {"state": state}
        logger.debug("MqttFlowMeterClient: relay %s → %s", sensor_id, state)
