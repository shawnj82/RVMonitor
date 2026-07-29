"""Tests for logic/solar_logic.py"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from logic.solar_logic import get_solar_charger_status


class TestSolarLogic:
    def test_solar_status_has_required_keys(self):
        data = get_solar_charger_status()
        for key in ("watts", "percent", "mode", "healthy"):
            assert key in data

    def test_solar_percent_in_range(self):
        p = get_solar_charger_status()["percent"]
        assert 0.0 <= p <= 100.0

    def test_solar_mode_is_valid(self):
        assert get_solar_charger_status()["mode"] in {
            "sun",
            "cloud_light",
            "cloud_heavy",
            "moon",
        }
