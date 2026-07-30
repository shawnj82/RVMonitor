"""
Tank logic for fresh, grey, and black water tanks.

Placeholder functions return mock values until real sensors are connected.
Flow logic:
  - Fresh water outflow (flow meter 1): decreases the fresh tank and fills
    grey + black tanks at the configured split ratios.
  - City water inflow (flow meter 2): does NOT decrease the fresh tank but
    still fills grey + black tanks (water is used and ends up in waste tanks).
"""

FRESH_TANK_CAPACITY_GALLONS = 60.0
GREY_TANK_CAPACITY_GALLONS = 60.0
BLACK_TANK_CAPACITY_GALLONS = 40.0

# Grey/black fill split from water outflow
GREY_SPLIT = 0.5
BLACK_SPLIT = 0.5

# Estimated daily fresh-water usage (placeholder – replace with measured rate)
DAILY_USAGE_GALLONS = 15.0

# Module-level state updated by the flow meter integration
_fresh_gallons_used: float = 0.0
_city_gallons_used: float = 0.0


def update_from_flow_meter(total_gallons_used: float) -> None:
    """Update internal state from the fresh-water flow meter's cumulative reading."""
    global _fresh_gallons_used
    _fresh_gallons_used = total_gallons_used


def update_from_city_water_meter(total_gallons_used: float) -> None:
    """
    Update internal state from the city-water flow meter's cumulative reading.

    City water does not draw from the fresh tank but does fill the grey and
    black holding tanks at the same split ratios as fresh outflow.
    """
    global _city_gallons_used
    _city_gallons_used = total_gallons_used


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

    Grey tank fills at GREY_SPLIT of total water outflow (fresh + city water).

    Returns a dict with keys:
        capacity_gallons  – maximum tank size
        current_gallons   – estimated gallons accumulated
        percent_full      – 0–100
        healthy           – True if level is below 80%
    """
    total_outflow = _fresh_gallons_used + _city_gallons_used
    accumulated = min(GREY_TANK_CAPACITY_GALLONS, total_outflow * GREY_SPLIT)
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

    Black tank fills at BLACK_SPLIT of total water outflow (fresh + city water).

    Returns a dict with keys:
        capacity_gallons  – maximum tank size
        current_gallons   – estimated gallons accumulated
        percent_full      – 0–100
        healthy           – True if level is below 80%
    """
    total_outflow = _fresh_gallons_used + _city_gallons_used
    accumulated = min(BLACK_TANK_CAPACITY_GALLONS, total_outflow * BLACK_SPLIT)
    percent = (accumulated / BLACK_TANK_CAPACITY_GALLONS) * 100.0
    return {
        "capacity_gallons": BLACK_TANK_CAPACITY_GALLONS,
        "current_gallons": round(accumulated, 2),
        "percent_full": round(percent, 1),
        "healthy": percent < 80.0,
    }


def get_water_days_remaining() -> float | None:
    """
    Estimate days until water becomes the limiting constraint.

    The bottleneck is whichever comes first:
      • fresh water running out
      • grey or black holding tank filling up

    Returns days as a float, or None if DAILY_USAGE_GALLONS is zero
    (usage rate unknown).
    """
    if DAILY_USAGE_GALLONS <= 0:
        return None

    fresh = get_fresh_level()
    grey = get_grey_level()
    black = get_black_level()

    fresh_days = fresh["current_gallons"] / DAILY_USAGE_GALLONS

    grey_space = grey["capacity_gallons"] - grey["current_gallons"]
    grey_days = grey_space / (DAILY_USAGE_GALLONS * GREY_SPLIT)

    black_space = black["capacity_gallons"] - black["current_gallons"]
    black_days = black_space / (DAILY_USAGE_GALLONS * BLACK_SPLIT)

    return round(min(fresh_days, grey_days, black_days), 1)
