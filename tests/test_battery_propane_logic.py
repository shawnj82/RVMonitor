"""Tests for logic/battery_logic.py and logic/propane_logic.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic.battery_logic import get_house_battery_status, get_accessory_battery_status
from logic.propane_logic import get_propane_status


class TestBatteryLogic:
    def test_house_battery_has_required_keys(self):
        data = get_house_battery_status()
        for key in ("voltage", "percent", "amps", "healthy"):
            assert key in data

    def test_house_battery_healthy(self):
        assert get_house_battery_status()["healthy"] is True

    def test_house_battery_voltage_positive(self):
        assert get_house_battery_status()["voltage"] > 0

    def test_house_battery_percent_in_range(self):
        p = get_house_battery_status()["percent"]
        assert 0.0 <= p <= 100.0

    def test_accessory_battery_has_required_keys(self):
        data = get_accessory_battery_status()
        for key in ("voltage", "percent", "amps", "healthy"):
            assert key in data

    def test_accessory_battery_healthy(self):
        assert get_accessory_battery_status()["healthy"] is True

    def test_accessory_battery_percent_in_range(self):
        p = get_accessory_battery_status()["percent"]
        assert 0.0 <= p <= 100.0


class TestPropaneLogic:
    def test_tank1_has_required_keys(self):
        data = get_propane_status(1)
        for key in ("tank", "percent_full", "psi", "healthy"):
            assert key in data

    def test_tank1_number_is_1(self):
        assert get_propane_status(1)["tank"] == 1

    def test_tank2_number_is_2(self):
        assert get_propane_status(2)["tank"] == 2

    def test_tank1_healthy(self):
        assert get_propane_status(1)["healthy"] is True

    def test_tank2_healthy(self):
        assert get_propane_status(2)["healthy"] is True

    def test_percent_in_range(self):
        for tank in (1, 2):
            p = get_propane_status(tank)["percent_full"]
            assert 0.0 <= p <= 100.0

    def test_unknown_tank_returns_zero_percent(self):
        data = get_propane_status(99)
        assert data["percent_full"] == 0.0
        assert data["psi"] == 0.0
        assert data["healthy"] is False
