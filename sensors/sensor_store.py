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
          "flow1": {
            "stream_id": "fresh_water_out",
            "description": "...",
            "routing": {...}
          },
          "flow2": {
            "stream_id": "city_water_in",
            "description": "...",
            "routing": {...}
          }
        }
      }
    }

Legacy roles: ``"fresh_water_out"``, ``"city_water_in"``, ``"none"``
"""

from __future__ import annotations

import copy
import json
import logging
import os
from typing import Callable

logger = logging.getLogger(__name__)

# Legacy roles kept for backward compatibility/migration.
VALID_ROLES: tuple[str, ...] = ("fresh_water_out", "city_water_in", "none")
VALID_BANKS: tuple[str, ...] = ("fresh", "grey", "black")
VALID_INPUT_POLICIES: tuple[str, ...] = ("weighted", "any_active")

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
        self._modules[sensor_id] = self._normalize_module_config(copy.deepcopy(config))
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
                loaded_modules = data.get("sensor_modules", {})
                self._modules = {
                    sid: self._normalize_module_config(cfg)
                    for sid, cfg in loaded_modules.items()
                }
                logger.info("SensorStore: loaded %d module(s) from %s", len(self._modules), self._path)
                return
            except (OSError, ValueError, KeyError) as exc:
                logger.warning("SensorStore: could not read %s (%s) – using defaults", self._path, exc)

        # Seed from sensor_config.py
        try:
            from sensors.sensor_config import MQTT_BROKER, MQTT_PORT, SENSOR_MODULES  # noqa: PLC0415
            self._mqtt_broker = MQTT_BROKER
            self._mqtt_port = MQTT_PORT
            self._modules = {
                sid: self._normalize_module_config(copy.deepcopy(cfg))
                for sid, cfg in SENSOR_MODULES.items()
            }
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

    # ------------------------------------------------------------------
    # Routing helpers
    # ------------------------------------------------------------------

    def get_flow_routing(self) -> dict[str, dict]:
        """
        Return aggregated routing rules keyed by stream_id.

        Raises ValueError when duplicate stream IDs are found.
        """
        routing: dict[str, dict] = {}
        for sensor_id, module in self._modules.items():
            for meter_key in ("flow1", "flow2"):
                meter_cfg = module.get(meter_key, {})
                stream_id = str(meter_cfg.get("stream_id", "")).strip()
                if not stream_id:
                    continue
                if stream_id in routing:
                    existing = routing[stream_id]
                    current = meter_cfg.get("routing", {})
                    if existing != current:
                        raise ValueError(
                            f"conflicting routing for stream_id '{stream_id}' in module '{sensor_id}'"
                        )
                    continue
                routing[stream_id] = copy.deepcopy(meter_cfg.get("routing", {}))
        return routing

    @staticmethod
    def _normalize_module_config(config: dict) -> dict:
        if not isinstance(config, dict):
            raise ValueError("module config must be a dict")
        normalized = {
            "description": str(config.get("description", "")).strip(),
        }
        for meter_key in ("flow1", "flow2"):
            normalized[meter_key] = SensorStore._normalize_meter_config(
                config.get(meter_key, {})
            )
        return normalized

    @staticmethod
    def _normalize_meter_config(meter_cfg: dict) -> dict:
        if not isinstance(meter_cfg, dict):
            meter_cfg = {}

        stream_id = str(meter_cfg.get("stream_id", "")).strip()
        if not stream_id:
            role = str(meter_cfg.get("role", "none")).strip()
            if role in ("fresh_water_out", "city_water_in"):
                stream_id = role
            else:
                stream_id = "none"

        routing = meter_cfg.get("routing")
        if not isinstance(routing, dict):
            routing = SensorStore._legacy_role_to_routing(str(meter_cfg.get("role", "none")))

        priority = int(routing.get("priority", 0))
        input_policy = str(routing.get("input_policy", "weighted")).strip().lower()
        if input_policy not in VALID_INPUT_POLICIES:
            raise ValueError(f"invalid input_policy '{input_policy}'")

        inputs = SensorStore._normalize_inputs(routing.get("inputs", []))
        outputs = SensorStore._normalize_outputs(routing.get("outputs", []))
        source_bank = routing.get("source_bank")
        if source_bank is not None:
            source_bank = str(source_bank).strip().lower()
            if source_bank not in VALID_BANKS:
                raise ValueError(f"invalid source_bank '{source_bank}'")

        return {
            "stream_id": stream_id,
            "description": str(meter_cfg.get("description", "")).strip(),
            "routing": {
                "priority": priority,
                "input_policy": input_policy,
                "inputs": inputs,
                "outputs": outputs,
                "source_bank": source_bank,
            },
        }

    @staticmethod
    def _normalize_inputs(inputs: object) -> list[dict]:
        if not isinstance(inputs, list):
            raise ValueError("routing inputs must be a list")
        normalized: list[dict] = []
        for item in inputs:
            if isinstance(item, str):
                stream = item.strip()
                if stream:
                    normalized.append({"stream": stream, "proportion": None})
                continue
            if not isinstance(item, dict):
                raise ValueError("invalid routing input entry")
            stream = str(item.get("stream", "")).strip()
            if not stream:
                raise ValueError("routing input stream is required")
            proportion = item.get("proportion")
            if proportion is not None:
                proportion = float(proportion)
                if proportion < 0:
                    raise ValueError("routing input proportion must be >= 0")
            normalized.append({"stream": stream, "proportion": proportion})
        return normalized

    @staticmethod
    def _normalize_outputs(outputs: object) -> list[dict]:
        if not isinstance(outputs, list):
            raise ValueError("routing outputs must be a list")
        normalized: list[dict] = []
        for item in outputs:
            if not isinstance(item, dict):
                raise ValueError("invalid routing output entry")
            bank = str(item.get("bank", "")).strip().lower()
            if bank not in VALID_BANKS:
                raise ValueError(f"invalid routing output bank '{bank}'")
            proportion = float(item.get("proportion", 0.0))
            if proportion < 0:
                raise ValueError("routing output proportion must be >= 0")
            normalized.append({"bank": bank, "proportion": proportion})
        if normalized:
            total = sum(item["proportion"] for item in normalized)
            if abs(total - 1.0) > 1e-6:
                raise ValueError("routing output proportions must sum to 1.0")
        return normalized

    @staticmethod
    def _legacy_role_to_routing(role: str) -> dict:
        role = str(role).strip()
        if role == "fresh_water_out":
            return {
                "priority": 0,
                "input_policy": "weighted",
                "inputs": [],
                "outputs": [
                    {"bank": "grey", "proportion": 0.5},
                    {"bank": "black", "proportion": 0.5},
                ],
                "source_bank": "fresh",
            }
        if role == "city_water_in":
            return {
                "priority": 0,
                "input_policy": "weighted",
                "inputs": [],
                "outputs": [
                    {"bank": "grey", "proportion": 0.5},
                    {"bank": "black", "proportion": 0.5},
                ],
                "source_bank": None,
            }
        return {
            "priority": 0,
            "input_policy": "weighted",
            "inputs": [],
            "outputs": [],
            "source_bank": None,
        }
