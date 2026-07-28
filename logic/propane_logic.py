"""
Propane logic – placeholder until real sensors are connected.
"""


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
    mock_levels = {1: 65.0, 2: 30.0}
    mock_psi = {1: 90.0, 2: 42.0}
    percent = mock_levels.get(tank_number, 0.0)
    psi = mock_psi.get(tank_number, 0.0)
    return {
        "tank": tank_number,
        "percent_full": percent,
        "psi": psi,
        "healthy": percent > 10.0,
    }
