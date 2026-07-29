"""Tests for logic/battery_logic.py and logic/propane_logic.py"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest
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


class TestPropaneDaysRemaining:
    def test_returns_positive_float(self):
        from logic.propane_logic import get_propane_days_remaining
        days = get_propane_days_remaining()
        assert isinstance(days, float)
        assert days > 0

    def test_value_matches_formula(self):
        from logic.propane_logic import get_propane_days_remaining, DAILY_USAGE_PERCENT
        t1 = get_propane_status(1)
        t2 = get_propane_status(2)
        expected = round((t1["percent_full"] + t2["percent_full"]) / DAILY_USAGE_PERCENT, 1)
        assert get_propane_days_remaining() == pytest.approx(expected, rel=1e-3)

    def test_returns_none_when_daily_usage_zero(self):
        import logic.propane_logic as propane_logic
        original = propane_logic.DAILY_USAGE_PERCENT
        try:
            propane_logic.DAILY_USAGE_PERCENT = 0.0
            assert propane_logic.get_propane_days_remaining() is None
        finally:
            propane_logic.DAILY_USAGE_PERCENT = original


class TestPowerDaysRemaining:
    def test_returns_none_or_float(self):
        from logic.battery_logic import get_power_days_remaining
        result = get_power_days_remaining()
        assert result is None or isinstance(result, float)

    def test_returns_none_when_net_charging(self):
        # With default placeholder data: daily consumption = 5.2A × 24 = 124.8 Ah,
        # daily generation = 455W × 5h / 14.4V ≈ 158 Ah → net surplus → None
        from logic.battery_logic import get_power_days_remaining
        result = get_power_days_remaining()
        # Default mock has solar generation exceeding daily draw, so None is expected
        assert result is None

    def test_discharging_returns_positive_days(self):
        import logic.battery_logic as battery_logic
        from unittest.mock import patch

        discharging_house = {"voltage": 12.0, "percent": 50.0, "amps": -10.0, "healthy": True}
        no_solar = {"watts": 0.0, "amps": 0.0, "percent": 0.0, "mode": "moon", "healthy": False, "daily_ah": 0.0}

        with patch("logic.battery_logic.get_house_battery_status", return_value=discharging_house), \
             patch("logic.solar_logic.get_solar_charger_status", return_value=no_solar):
            days = battery_logic.get_power_days_remaining()
        assert isinstance(days, float)
        assert days > 0
