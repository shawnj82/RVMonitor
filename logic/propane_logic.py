"""
Propane logic – placeholder until real sensors are connected.
"""

# Estimated daily consumption as a percentage of one full tank (placeholder)
DAILY_USAGE_PERCENT = 24.0


def get_propane_status(tank_number: int = 1) -> dict:
    """
    Return propane tank status (placeholder).

    Args:
        tank_number: 1 or 2

    Returns a dict with keys:
        tank          – tank identifier
        percent_full  – estimated fill level (0–100)
        psi           – pressure in PSI
        healthy       – True when level is above 10%
    """
    mock_levels = {1: 54.0, 2: 100.0}
    mock_psi = {1: 75.0, 2: 135.0}
    percent = mock_levels.get(tank_number, 0.0)
    psi = mock_psi.get(tank_number, 0.0)
    return {
        "tank": tank_number,
        "percent_full": percent,
        "psi": psi,
        "healthy": percent > 10.0,
    }


def get_propane_days_remaining() -> float | None:
    """
    Estimate days until all propane is exhausted.

    Assumes both tanks are consumed in sequence, so total remaining
    is the sum of both tanks' percentages divided by the daily usage rate.

    Returns days as a float, or None if DAILY_USAGE_PERCENT is zero.
    """
    if DAILY_USAGE_PERCENT <= 0:
        return None
    t1 = get_propane_status(1)
    t2 = get_propane_status(2)
    total_percent = t1["percent_full"] + t2["percent_full"]
    return round(total_percent / DAILY_USAGE_PERCENT, 1)
