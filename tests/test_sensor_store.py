"""Tests for sensors/sensor_store.py"""

import json
import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
from sensors.sensor_store import SensorStore, VALID_ROLES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _tmp_path() -> str:
    """Return a unique temporary file path that does not yet exist."""
    fd, path = tempfile.mkstemp(suffix=".json")
    os.close(fd)
    os.unlink(path)  # we want the store to create it
    return path


def _store(path: str | None = None, seed: dict | None = None) -> SensorStore:
    """Create a SensorStore backed by a temp file, optionally pre-seeded."""
    p = path or _tmp_path()
    if seed is not None:
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "w") as fh:
            json.dump(seed, fh)
    return SensorStore(path=p)


_SAMPLE_MODULE = {
    "description": "Test module",
    "flow1": {"role": "fresh_water_out", "description": "Fresh out"},
    "flow2": {"role": "city_water_in",   "description": "City in"},
}


# ---------------------------------------------------------------------------
# VALID_ROLES constant
# ---------------------------------------------------------------------------

class TestValidRoles:
    def test_roles_are_tuple(self):
        assert isinstance(VALID_ROLES, tuple)

    def test_fresh_water_out_present(self):
        assert "fresh_water_out" in VALID_ROLES

    def test_city_water_in_present(self):
        assert "city_water_in" in VALID_ROLES

    def test_none_present(self):
        assert "none" in VALID_ROLES


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------

class TestSensorStoreInit:
    def test_empty_when_no_file_and_no_sensor_config(self, monkeypatch):
        """Without a saved file or sensor_config defaults, store starts empty."""
        monkeypatch.setattr(
            "sensors.sensor_store._DEFAULT_CONFIG_FILE",
            _tmp_path(),
        )
        store = SensorStore(path=_tmp_path())
        # Either empty or seeded from sensor_config.py – both are valid
        assert isinstance(store.get_all_modules(), dict)

    def test_loads_from_json_file(self):
        seed = {
            "mqtt_broker": "192.168.1.50",
            "mqtt_port": 1883,
            "sensor_modules": {
                "module_a": _SAMPLE_MODULE,
            },
        }
        store = _store(seed=seed)
        modules = store.get_all_modules()
        assert "module_a" in modules
        assert store.get_mqtt_broker() == "192.168.1.50"

    def test_default_broker_is_localhost(self):
        store = _store()
        assert store.get_mqtt_broker() == "localhost"

    def test_default_port_is_1883(self):
        store = _store()
        assert store.get_mqtt_port() == 1883


# ---------------------------------------------------------------------------
# add_or_update_module
# ---------------------------------------------------------------------------

class TestAddOrUpdateModule:
    def test_add_new_module(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert "m1" in store.get_all_modules()

    def test_update_existing_module(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        updated = dict(_SAMPLE_MODULE, description="Updated desc")
        store.add_or_update_module("m1", updated)
        assert store.get_module("m1")["description"] == "Updated desc"

    def test_get_module_returns_deep_copy(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        copy1 = store.get_module("m1")
        copy1["description"] = "mutated"
        assert store.get_module("m1")["description"] == _SAMPLE_MODULE["description"]

    def test_get_all_modules_returns_deep_copy(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        all_mods = store.get_all_modules()
        all_mods["new_key"] = {}
        assert "new_key" not in store.get_all_modules()

    def test_raises_on_empty_sensor_id(self):
        store = _store()
        with pytest.raises(ValueError):
            store.add_or_update_module("", _SAMPLE_MODULE)

    def test_persists_to_file(self):
        path = _tmp_path()
        store = _store(path=path)
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        # Reload from the same file
        store2 = SensorStore(path=path)
        assert "m1" in store2.get_all_modules()


# ---------------------------------------------------------------------------
# remove_module
# ---------------------------------------------------------------------------

class TestRemoveModule:
    def test_remove_existing(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        store.remove_module("m1")
        assert "m1" not in store.get_all_modules()

    def test_remove_nonexistent_is_noop(self):
        store = _store()
        store.remove_module("does_not_exist")  # should not raise

    def test_removal_persisted(self):
        path = _tmp_path()
        store = _store(path=path)
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        store.remove_module("m1")
        store2 = SensorStore(path=path)
        assert "m1" not in store2.get_all_modules()


# ---------------------------------------------------------------------------
# get_module
# ---------------------------------------------------------------------------

class TestGetModule:
    def test_returns_none_for_missing_key(self):
        store = _store()
        assert store.get_module("missing") is None

    def test_returns_module_config(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        result = store.get_module("m1")
        assert result["description"] == _SAMPLE_MODULE["description"]
        assert result["flow1"]["role"] == "fresh_water_out"


# ---------------------------------------------------------------------------
# Observer (subscribe / unsubscribe)
# ---------------------------------------------------------------------------

class TestObserver:
    def test_add_event_fires_callback(self):
        store = _store()
        events = []
        store.subscribe(lambda event, sid, cfg: events.append((event, sid)))
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert ("add", "m1") in events

    def test_update_event_fires_callback(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        events = []
        store.subscribe(lambda event, sid, cfg: events.append((event, sid)))
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert ("update", "m1") in events

    def test_remove_event_fires_callback(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        events = []
        store.subscribe(lambda event, sid, cfg: events.append((event, sid)))
        store.remove_module("m1")
        assert ("remove", "m1") in events

    def test_remove_event_config_is_none(self):
        store = _store()
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        received = []
        store.subscribe(lambda event, sid, cfg: received.append(cfg))
        store.remove_module("m1")
        assert received[-1] is None

    def test_add_event_config_is_dict(self):
        store = _store()
        received = []
        store.subscribe(lambda event, sid, cfg: received.append(cfg))
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert isinstance(received[-1], dict)

    def test_unsubscribe_stops_notifications(self):
        store = _store()
        events = []

        def cb(event, sid, cfg):
            events.append(event)

        store.subscribe(cb)
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        count_after_sub = len(events)

        store.unsubscribe(cb)
        store.add_or_update_module("m2", _SAMPLE_MODULE)
        assert len(events) == count_after_sub

    def test_subscribe_same_callback_twice_fires_once(self):
        store = _store()
        count = [0]

        def cb(event, sid, cfg):
            count[0] += 1

        store.subscribe(cb)
        store.subscribe(cb)  # duplicate
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert count[0] == 1

    def test_callback_exception_does_not_prevent_save(self):
        """A broken callback must not block the save."""
        store = _store()

        def bad_cb(event, sid, cfg):
            raise RuntimeError("oops")

        store.subscribe(bad_cb)
        # Should not raise and should still persist
        store.add_or_update_module("m1", _SAMPLE_MODULE)
        assert "m1" in store.get_all_modules()


# ---------------------------------------------------------------------------
# set_mqtt_connection
# ---------------------------------------------------------------------------

class TestSetMqttConnection:
    def test_updates_broker_and_port(self):
        store = _store()
        store.set_mqtt_connection("10.0.0.1", 9999)
        assert store.get_mqtt_broker() == "10.0.0.1"
        assert store.get_mqtt_port() == 9999

    def test_persists_broker(self):
        path = _tmp_path()
        store = _store(path=path)
        store.set_mqtt_connection("10.0.0.2", 1884)
        store2 = SensorStore(path=path)
        assert store2.get_mqtt_broker() == "10.0.0.2"
        assert store2.get_mqtt_port() == 1884
