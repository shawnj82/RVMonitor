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
    yield
    tank_logic.update_from_flow_meter(0.0)


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
