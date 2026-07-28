"""
Tank logic for fresh, grey, and black water tanks.

Placeholder functions return mock values until real sensors are connected.
Flow logic:
  - Fresh water outflow measured by ESP32 flow meter.
  - Fresh outflow is split equally: 50% → grey tank, 50% → black tank.
"""

FRESH_TANK_CAPACITY_GALLONS = 60.0
GREY_TANK_CAPACITY_GALLONS = 60.0
BLACK_TANK_CAPACITY_GALLONS = 40.0

# Grey/black fill split from fresh outflow
GREY_SPLIT = 0.5
BLACK_SPLIT = 0.5

# Module-level state updated by the flow meter integration
_fresh_gallons_used: float = 0.0


def update_from_flow_meter(total_gallons_used: float) -> None:
    """Update internal state from the flow meter's cumulative gallons reading."""
    global _fresh_gallons_used
    _fresh_gallons_used = total_gallons_used


def get_fresh_level() -> dict:
    """
    Return fresh water tank status.

    Returns a dict with keys:
        capacity_gallons  – maximum tank size
        current_gallons   – estimated gallons remaining
        percent_full      – 0–100
        healthy           – True if level is above 20%
    """
    remaining = max(0.0, FRESH_TANK_CAPACITY_GALLONS - _fresh_gallons_used)
    percent = (remaining / FRESH_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": FRESH_TANK_CAPACITY_GALLONS,
        "current_gallons": round(remaining, 2),
        "percent_full": round(percent, 1),
        "healthy": percent > 20.0,
    }


def get_grey_level() -> dict:
    """
    Return grey water tank status.

    Grey tank fills at GREY_SPLIT of fresh water outflow.

    Returns a dict with keys:
        capacity_gallons  – maximum tank size
        current_gallons   – estimated gallons accumulated
        percent_full      – 0–100
        healthy           – True if level is below 80%
    """
    accumulated = min(GREY_TANK_CAPACITY_GALLONS, _fresh_gallons_used * GREY_SPLIT)
    percent = (accumulated / GREY_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": GREY_TANK_CAPACITY_GALLONS,
        "current_gallons": round(accumulated, 2),
        "percent_full": round(percent, 1),
        "healthy": percent < 80.0,
    }


def get_black_level() -> dict:
    """
    Return black water tank status.

    Black tank fills at BLACK_SPLIT of fresh water outflow.

    Returns a dict with keys:
        capacity_gallons  – maximum tank size
        current_gallons   – estimated gallons accumulated
        percent_full      – 0–100
        healthy           – True if level is below 80%
    """
    accumulated = min(BLACK_TANK_CAPACITY_GALLONS, _fresh_gallons_used * BLACK_SPLIT)
    percent = (accumulated / BLACK_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": BLACK_TANK_CAPACITY_GALLONS,
        "current_gallons": round(accumulated, 2),
        "percent_full": round(percent, 1),
        "healthy": percent < 80.0,
    }
