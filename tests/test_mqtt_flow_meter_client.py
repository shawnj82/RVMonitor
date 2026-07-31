"""Tests for sensors/mqtt_flow_meter_client.py"""

import sys
import os
import json
from unittest.mock import MagicMock, patch, call

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
import logic.tank_logic as tank_logic
from sensors.mqtt_flow_meter_client import MqttFlowMeterClient


SENSOR_MODULES = {
    "flow_module_01": {
        "description": "Test module",
        "flow1": {
            "stream_id": "fresh_water_out",
            "description": "Fresh outflow",
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
            "description": "City water",
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
    }
}


@pytest.fixture(autouse=True)
def reset_tank_logic():
    """Reset tank logic state before each test."""
    tank_logic.update_from_flow_meter(0.0)
    tank_logic.update_from_city_water_meter(0.0)
    yield
    tank_logic.update_from_flow_meter(0.0)
    tank_logic.update_from_city_water_meter(0.0)


@pytest.fixture()
def client():
    """Return an MqttFlowMeterClient with a mocked paho MQTT client."""
    with patch("sensors.mqtt_flow_meter_client.mqtt.Client") as MockMqtt:
        mock_mqtt_instance = MagicMock()
        MockMqtt.return_value = mock_mqtt_instance
        c = MqttFlowMeterClient("localhost", 1883, SENSOR_MODULES)
        c._mqtt = mock_mqtt_instance
        yield c


class TestMqttFlowMeterClientInit:
    def test_not_connected_initially(self, client):
        assert client.is_connected is False

    def test_initial_flow_rates_are_zero(self, client):
        assert client.get_flow_rate("flow_module_01", 1) == 0.0
        assert client.get_flow_rate("flow_module_01", 2) == 0.0

    def test_initial_total_gallons_are_zero(self, client):
        assert client.get_total_gallons(("flow_module_01"), 1) == 0.0
        assert client.get_total_gallons(("flow_module_01"), 2) == 0.0

    def test_initial_relay_state_is_off(self, client):
        assert client.get_relay_state("flow_module_01") == "off"

    def test_unknown_sensor_returns_defaults(self, client):
        assert client.get_flow_rate("nonexistent", 1) == 0.0
        assert client.get_relay_state("nonexistent") == "off"


class TestMqttFlowMeterClientConnect:
    def test_connect_returns_true_on_success(self, client):
        client._mqtt.connect.return_value = None
        result = client.connect()
        assert result is True

    def test_connect_calls_broker(self, client):
        client.connect()
        client._mqtt.connect.assert_called_once_with("localhost", 1883, keepalive=60)

    def test_connect_starts_loop(self, client):
        client.connect()
        client._mqtt.loop_start.assert_called_once()

    def test_connect_returns_false_on_exception(self, client):
        client._mqtt.connect.side_effect = ConnectionRefusedError("refused")
        result = client.connect()
        assert result is False

    def test_disconnect_stops_loop(self, client):
        client.disconnect()
        client._mqtt.loop_stop.assert_called_once()
        client._mqtt.disconnect.assert_called_once()


class TestMqttFlowMeterClientOnConnect:
    def test_on_connect_sets_connected(self, client):
        reason_code = MagicMock()
        reason_code.is_failure = False
        client._on_connect(client._mqtt, None, None, reason_code, None)
        assert client.is_connected is True

    def test_on_connect_subscribes_to_topics(self, client):
        reason_code = MagicMock()
        reason_code.is_failure = False
        client._on_connect(client._mqtt, None, None, reason_code, None)
        subscribe_calls = client._mqtt.subscribe.call_args_list
        topics_subscribed = [c[0][0] for c in subscribe_calls]
        assert "rv/flowmeter/flow_module_01/flow1" in topics_subscribed
        assert "rv/flowmeter/flow_module_01/flow2" in topics_subscribed
        assert "rv/flowmeter/flow_module_01/relay" in topics_subscribed

    def test_on_connect_failure_does_not_set_connected(self, client):
        reason_code = MagicMock()
        reason_code.is_failure = True
        client._on_connect(client._mqtt, None, None, reason_code, None)
        assert client.is_connected is False

    def test_on_disconnect_clears_connected(self, client):
        client._connected = True
        client._on_disconnect(client._mqtt, None, None, MagicMock(), None)
        assert client.is_connected is False


class TestMqttFlowMeterClientOnMessage:
    def _make_msg(self, topic: str, payload: dict) -> MagicMock:
        msg = MagicMock()
        msg.topic = topic
        msg.payload = json.dumps(payload).encode()
        return msg

    def test_flow1_message_updates_state(self, client):
        msg = self._make_msg(
            "rv/flowmeter/flow_module_01/flow1",
            {"gpm": 2.5, "total_gallons": 12.0},
        )
        client._on_message(None, None, msg)
        assert client.get_flow_rate("flow_module_01", 1) == pytest.approx(2.5)
        assert client.get_total_gallons("flow_module_01", 1) == pytest.approx(12.0)

    def test_flow2_message_updates_state(self, client):
        msg = self._make_msg(
            "rv/flowmeter/flow_module_01/flow2",
            {"gpm": 1.8, "total_gallons": 7.3},
        )
        client._on_message(None, None, msg)
        assert client.get_flow_rate("flow_module_01", 2) == pytest.approx(1.8)
        assert client.get_total_gallons("flow_module_01", 2) == pytest.approx(7.3)

    def test_relay_message_updates_state(self, client):
        msg = self._make_msg(
            "rv/flowmeter/flow_module_01/relay",
            {"state": "on"},
        )
        client._on_message(None, None, msg)
        assert client.get_relay_state("flow_module_01") == "on"

    def test_flow1_triggers_fresh_water_tank_update(self, client):
        msg = self._make_msg(
            "rv/flowmeter/flow_module_01/flow1",
            {"gpm": 2.0, "total_gallons": 10.0},
        )
        client._on_message(None, None, msg)
        # fresh water used = 10.0 → remaining = 50.0
        fresh = tank_logic.get_fresh_level()
        assert fresh["current_gallons"] == pytest.approx(50.0)

    def test_flow2_triggers_city_water_tank_update(self, client):
        msg = self._make_msg(
            "rv/flowmeter/flow_module_01/flow2",
            {"gpm": 1.5, "total_gallons": 8.0},
        )
        client._on_message(None, None, msg)
        # city water 8.0 gal → grey = 4.0, black = 4.0; fresh untouched
        fresh = tank_logic.get_fresh_level()
        grey = tank_logic.get_grey_level()
        assert fresh["current_gallons"] == pytest.approx(60.0)
        assert grey["current_gallons"] == pytest.approx(4.0)

    def test_bad_payload_does_not_crash(self, client):
        msg = MagicMock()
        msg.topic = "rv/flowmeter/flow_module_01/flow1"
        msg.payload = b"not-json"
        # Should log a warning but not raise
        client._on_message(None, None, msg)

    def test_unknown_topic_is_ignored(self, client):
        msg = MagicMock()
        msg.topic = "rv/unknown/topic"
        msg.payload = json.dumps({"gpm": 1.0}).encode()
        client._on_message(None, None, msg)

    def test_custom_stream_id_updates_named_stream(self, client):
        client._sensor_modules["flow_module_01"]["flow2"]["stream_id"] = "toilet_flow"
        client._sensor_modules["flow_module_01"]["flow2"]["routing"] = {
            "priority": 100,
            "input_policy": "any_active",
            "inputs": [
                {"stream": "fresh_water_out", "proportion": None},
                {"stream": "city_water_in", "proportion": None},
            ],
            "outputs": [{"bank": "black", "proportion": 1.0}],
            "source_bank": None,
        }
        client._apply_routing_config()
        client._on_message(
            None,
            None,
            self._make_msg(
                "rv/flowmeter/flow_module_01/flow1",
                {"gpm": 1.0, "total_gallons": 10.0},
            ),
        )
        client._on_message(
            None,
            None,
            self._make_msg(
                "rv/flowmeter/flow_module_01/flow2",
                {"gpm": 0.7, "total_gallons": 2.0},
            ),
        )
        grey = tank_logic.get_grey_level()
        black = tank_logic.get_black_level()
        assert grey["current_gallons"] == pytest.approx(4.0, rel=1e-3)
        assert black["current_gallons"] == pytest.approx(6.0, rel=1e-3)


class TestMqttFlowMeterClientSetRelay:
    def test_set_relay_on_publishes_correct_payload(self, client):
        client.set_relay("flow_module_01", on=True)
        client._mqtt.publish.assert_called_once_with(
            "rv/flowmeter/flow_module_01/relay/set", "on"
        )

    def test_set_relay_off_publishes_correct_payload(self, client):
        client.set_relay("flow_module_01", on=False)
        client._mqtt.publish.assert_called_once_with(
            "rv/flowmeter/flow_module_01/relay/set", "off"
        )
