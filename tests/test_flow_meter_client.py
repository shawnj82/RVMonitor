"""Tests for sensors/flow_meter_client.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from sensors.flow_meter_client import FlowMeterClient


class TestFlowMeterClient:
    def test_default_not_connected(self):
        client = FlowMeterClient()
        assert client.is_connected is False

    def test_connect_returns_true(self):
        client = FlowMeterClient()
        assert client.connect() is True
        assert client.is_connected is True

    def test_disconnect(self):
        client = FlowMeterClient()
        client.connect()
        client.disconnect()
        assert client.is_connected is False

    def test_get_flow_rate_when_not_connected(self):
        client = FlowMeterClient()
        assert client.get_flow_rate() == 0.0

    def test_get_total_gallons_when_not_connected(self):
        client = FlowMeterClient()
        assert client.get_total_gallons_used() == 0.0

    def test_get_flow_rate_when_connected(self):
        client = FlowMeterClient()
        client.connect()
        # Mock returns 0.0 – just verify no exception and correct type
        result = client.get_flow_rate()
        assert isinstance(result, float)

    def test_get_total_gallons_when_connected(self):
        client = FlowMeterClient()
        client.connect()
        result = client.get_total_gallons_used()
        assert isinstance(result, float)
