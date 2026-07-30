"""
Persistent, observable sensor-module configuration store.

The store reads from and writes to a JSON file so that sensor configuration
survives application restarts.  If the file does not exist on first run, the
default modules from ``sensors/sensor_config.py`` are used as the seed.

File location
-------------
The default path is ``data/sensors.json``, relative to the directory that
contains this file.  Pass a custom path to the constructor when testing or
when the application needs a different location.

Observer pattern
----------------
Call ``subscribe(callback)`` to register a function that will be called
whenever sensors are added, updated, or removed.  The callback signature is::

    callback(event: str, sensor_id: str, config: dict | None)

where *event* is one of ``"add"``, ``"update"``, or ``"remove"`` and
*config* is the new module dict (or ``None`` for ``"remove"`` events).

JSON schema
-----------
::

    {
      "mqtt_broker": "localhost",
      "mqtt_port": 1883,
      "sensor_modules": {
        "<sensor_id>": {
          "description": "...",
          "flow1": {"role": "fresh_water_out", "description": "..."},
          "flow2": {"role": "city_water_in",   "description": "..."}
        }
      }
    }

Valid roles: ``"fresh_water_out"``, ``"city_water_in"``, ``"none"``
"""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)

# Roles the UI will offer in its dropdown
VALID_ROLES: tuple[str, ...] = ("fresh_water_out", "city_water_in", "none")

_DEFAULT_CONFIG_FILE = os.path.join(
    os.path.dirname(__file__), "..", "data", "sensors.json"
)


class SensorStore:
    """
    In-memory + file-backed store for ESP32 flow-meter sensor configuration.

    This class is deliberately free of Qt dependencies so it can be used and
    tested independently.
    """

    def __init__(self, path: str | None = None) -> None:
        self._path: str = os.path.normpath(path or _DEFAULT_CONFIG_FILE)
        self._mqtt_broker: str = "localhost"
        self._mqtt_port: int = 1883
        self._modules: dict[str, dict] = {}
        self._callbacks: list[Callable[[str, str, dict | None], None]] = []

        self._load()

    # ------------------------------------------------------------------
    # Observer registration
    # ------------------------------------------------------------------

    def subscribe(self, callback: Callable[[str, str, dict | None], None]) -> None:
        """Register *callback* to receive change events."""
        if callback not in self._callbacks:
            self._callbacks.append(callback)

    def unsubscribe(self, callback: Callable[[str, str, dict | None], None]) -> None:
        """Deregister a previously registered callback."""
        self._callbacks = [c for c in self._callbacks if c is not callback]

    # ------------------------------------------------------------------
    # Data access
    # ------------------------------------------------------------------

    def get_all_modules(self) -> dict[str, dict]:
        """Return a deep copy of all sensor modules (safe to mutate)."""
        return copy.deepcopy(self._modules)

    def get_module(self, sensor_id: str) -> dict | None:
        """Return a deep copy of a single module, or None if not found."""
        module = self._modules.get(sensor_id)
        return copy.deepcopy(module) if module is not None else None

    def get_mqtt_broker(self) -> str:
        return self._mqtt_broker

    def get_mqtt_port(self) -> int:
        return self._mqtt_port

    def set_mqtt_connection(self, broker: str, port: int) -> None:
        """Persist the MQTT broker address."""
        self._mqtt_broker = broker
        self._mqtt_port = port
        self._save()

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def add_or_update_module(self, sensor_id: str, config: dict) -> None:
        """
        Add a new sensor module or update an existing one.

        ``config`` should contain at least ``"description"``, ``"flow1"``, and
        ``"flow2"`` keys matching the schema described in the module docstring.

        Emits an ``"add"`` event for new modules and an ``"update"`` event for
        existing ones.
        """
        if not sensor_id:
            raise ValueError("sensor_id must not be empty")

        event = "update" if sensor_id in self._modules else "add"
        self._modules[sensor_id] = copy.deepcopy(config)
        self._save()
        self._notify(event, sensor_id, self._modules[sensor_id])

    def remove_module(self, sensor_id: str) -> None:
        """
        Remove the sensor module with the given ID.

        Silently does nothing if *sensor_id* is not found.
        Emits a ``"remove"`` event.
        """
        if sensor_id not in self._modules:
            return
        del self._modules[sensor_id]
        self._save()
        self._notify("remove", sensor_id, None)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _load(self) -> None:
        """Load config from the JSON file; fall back to sensor_config.py defaults."""
        if os.path.exists(self._path):
            try:
                with open(self._path, encoding="utf-8") as fh:
                    data = json.load(fh)
                self._mqtt_broker = data.get("mqtt_broker", "localhost")
                self._mqtt_port = int(data.get("mqtt_port", 1883))
                self._modules = data.get("sensor_modules", {})
                logger.info("SensorStore: loaded %d module(s) from %s", len(self._modules), self._path)
                return
            except (OSError, ValueError, KeyError) as exc:
                logger.warning("SensorStore: could not read %s (%s) – using defaults", self._path, exc)

        # Seed from sensor_config.py
        try:
            from sensors.sensor_config import MQTT_BROKER, MQTT_PORT, SENSOR_MODULES  # noqa: PLC0415
            self._mqtt_broker = MQTT_BROKER
            self._mqtt_port = MQTT_PORT
            self._modules = copy.deepcopy(SENSOR_MODULES)
            logger.info("SensorStore: seeded from sensor_config.py (%d module(s))", len(self._modules))
        except ImportError:
            logger.warning("SensorStore: sensor_config.py not available; starting empty")

    def _save(self) -> None:
        """Write the current configuration to the JSON file."""
        os.makedirs(os.path.dirname(self._path), exist_ok=True)
        data = {
            "mqtt_broker": self._mqtt_broker,
            "mqtt_port": self._mqtt_port,
            "sensor_modules": self._modules,
        }
        try:
            with open(self._path, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2)
            logger.debug("SensorStore: saved to %s", self._path)
        except OSError as exc:
            logger.error("SensorStore: could not save to %s – %s", self._path, exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _notify(self, event: str, sensor_id: str, config: dict | None) -> None:
        for cb in list(self._callbacks):
            try:
                cb(event, sensor_id, config)
            except Exception as exc:  # noqa: BLE001
                logger.error("SensorStore: callback raised %s", exc)
