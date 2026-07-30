"""Tests for logic/tank_logic.py"""

import sys
import os

# Allow imports from the project root
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import logic.tank_logic as tank_logic
import pytest


@pytest.fixture(autouse=True)
def reset_flow_meter():
    """Reset module state before each test."""
    tank_logic.update_from_flow_meter(0.0)
    tank_logic.update_from_city_water_meter(0.0)
    yield
    tank_logic.update_from_flow_meter(0.0)
    tank_logic.update_from_city_water_meter(0.0)


class TestFreshLevel:
    def test_full_tank_at_zero_usage(self):
        data = tank_logic.get_fresh_level()
        assert data["current_gallons"] == 60.0
        assert data["percent_full"] == 100.0
        assert data["healthy"] is True

    def test_capacity_is_correct(self):
        assert tank_logic.get_fresh_level()["capacity_gallons"] == 60.0

    def test_partial_usage(self):
        tank_logic.update_from_flow_meter(15.0)
        data = tank_logic.get_fresh_level()
        assert data["current_gallons"] == 45.0
        assert data["percent_full"] == pytest.approx(75.0, rel=1e-3)
        assert data["healthy"] is True

    def test_below_healthy_threshold(self):
        # 20% of 60 = 12 gal remaining → exactly at threshold (not > 20%)
        tank_logic.update_from_flow_meter(48.0)
        data = tank_logic.get_fresh_level()
        assert data["percent_full"] == pytest.approx(20.0, rel=1e-3)
        assert data["healthy"] is False

    def test_never_goes_negative(self):
        tank_logic.update_from_flow_meter(200.0)
        data = tank_logic.get_fresh_level()
        assert data["current_gallons"] == 0.0
        assert data["percent_full"] == 0.0


class TestGreyLevel:
    def test_empty_at_zero_usage(self):
        data = tank_logic.get_grey_level()
        assert data["current_gallons"] == 0.0
        assert data["percent_full"] == 0.0
        assert data["healthy"] is True

    def test_fills_at_half_fresh_outflow(self):
        tank_logic.update_from_flow_meter(20.0)
        data = tank_logic.get_grey_level()
        assert data["current_gallons"] == pytest.approx(10.0, rel=1e-3)

    def test_capped_at_capacity(self):
        tank_logic.update_from_flow_meter(200.0)
        data = tank_logic.get_grey_level()
        assert data["current_gallons"] == 60.0

    def test_unhealthy_when_above_80_percent(self):
        # 80% of 60 = 48 gal accumulated → need 96 gal of fresh outflow
        tank_logic.update_from_flow_meter(96.0)
        data = tank_logic.get_grey_level()
        assert data["percent_full"] == pytest.approx(80.0, rel=1e-3)
        assert data["healthy"] is False


class TestBlackLevel:
    def test_empty_at_zero_usage(self):
        data = tank_logic.get_black_level()
        assert data["current_gallons"] == 0.0
        assert data["healthy"] is True

    def test_fills_at_half_fresh_outflow(self):
        tank_logic.update_from_flow_meter(20.0)
        data = tank_logic.get_black_level()
        assert data["current_gallons"] == pytest.approx(10.0, rel=1e-3)

    def test_capacity_is_40_gallons(self):
        assert tank_logic.get_black_level()["capacity_gallons"] == 40.0

    def test_capped_at_capacity(self):
        tank_logic.update_from_flow_meter(500.0)
        data = tank_logic.get_black_level()
        assert data["current_gallons"] == 40.0

    def test_unhealthy_when_above_80_percent(self):
        # 80% of 40 = 32 gal → need 64 gal of fresh outflow
        tank_logic.update_from_flow_meter(64.0)
        data = tank_logic.get_black_level()
        assert data["percent_full"] == pytest.approx(80.0, rel=1e-3)
        assert data["healthy"] is False


class TestWaterDaysRemaining:
    def test_returns_float_at_zero_usage(self):
        # Full fresh tank, empty waste tanks – should return a positive number
        days = tank_logic.get_water_days_remaining()
        assert isinstance(days, float)
        assert days > 0

    def test_fresh_tank_limits_days(self):
        # Use up all fresh water; days should be 0
        tank_logic.update_from_flow_meter(tank_logic.FRESH_TANK_CAPACITY_GALLONS)
        days = tank_logic.get_water_days_remaining()
        assert days == 0.0

    def test_waste_tank_can_be_bottleneck(self):
        # Fill grey tank close to capacity so it limits sooner than fresh runs out
        # Grey caps at 60 gal; it fills at 0.5 * outflow.
        # With 0 usage: grey_days = 60 / (15 * 0.5) = 8, fresh_days = 60 / 15 = 4
        # fresh is the bottleneck at zero usage; test after partial use
        tank_logic.update_from_flow_meter(50.0)
        days = tank_logic.get_water_days_remaining()
        assert days is not None
        assert days >= 0.0

    def test_returns_none_when_daily_usage_zero(self):
        original = tank_logic.DAILY_USAGE_GALLONS
        try:
            tank_logic.DAILY_USAGE_GALLONS = 0.0
            assert tank_logic.get_water_days_remaining() is None
        finally:
            tank_logic.DAILY_USAGE_GALLONS = original


class TestCityWaterMeter:
    def test_city_water_does_not_affect_fresh_tank(self):
        tank_logic.update_from_city_water_meter(30.0)
        fresh = tank_logic.get_fresh_level()
        assert fresh["current_gallons"] == 60.0

    def test_city_water_fills_grey_tank(self):
        tank_logic.update_from_city_water_meter(20.0)
        grey = tank_logic.get_grey_level()
        assert grey["current_gallons"] == pytest.approx(10.0, rel=1e-3)

    def test_city_water_fills_black_tank(self):
        tank_logic.update_from_city_water_meter(20.0)
        black = tank_logic.get_black_level()
        assert black["current_gallons"] == pytest.approx(10.0, rel=1e-3)

    def test_city_and_fresh_water_accumulate_in_waste_tanks(self):
        # 10 gal fresh + 10 gal city = 20 gal total outflow → 10 gal grey, 10 gal black
        tank_logic.update_from_flow_meter(10.0)
        tank_logic.update_from_city_water_meter(10.0)
        grey = tank_logic.get_grey_level()
        black = tank_logic.get_black_level()
        assert grey["current_gallons"] == pytest.approx(10.0, rel=1e-3)
        assert black["current_gallons"] == pytest.approx(10.0, rel=1e-3)

    def test_city_water_only_fresh_tank_unaffected_by_city(self):
        # Fresh tank should only be drawn down by fresh water meter, not city
        tank_logic.update_from_flow_meter(20.0)
        tank_logic.update_from_city_water_meter(40.0)
        fresh = tank_logic.get_fresh_level()
        # Only 20 gallons drawn from fresh tank
        assert fresh["current_gallons"] == pytest.approx(40.0, rel=1e-3)

    def test_update_from_city_water_meter(self):
        tank_logic.update_from_city_water_meter(15.0)
        assert tank_logic._city_gallons_used == pytest.approx(15.0, rel=1e-3)
