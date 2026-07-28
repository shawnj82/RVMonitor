"""
Placeholder sensor stubs – return mock values until real modules are wired up.

Each function mirrors the signature of its real counterpart so callers do not
need to change when real sensor modules are introduced.
"""

from __future__ import annotations

from logic.tank_logic import get_fresh_level, get_grey_level, get_black_level
from logic.battery_logic import get_house_battery_status, get_accessory_battery_status
from logic.propane_logic import get_propane_status

__all__ = [
    "get_fresh_level",
    "get_grey_level",
    "get_black_level",
    "get_house_battery_status",
    "get_accessory_battery_status",
    "get_propane_status",
]
