"""
Battery logic – placeholder until real BMS sensors are connected.
"""


def get_house_battery_status() -> dict:
    """
    Return house battery bank status (placeholder).

    Returns a dict with keys:
        voltage      – battery voltage in volts
        percent      – state-of-charge percentage (0–100)
        amps         – current draw in amps (positive = charging)
        healthy      – True when SoC is above 20%
    """
    return {
        "voltage": 12.6,
        "percent": 85.0,
        "amps": -5.2,
        "healthy": True,
    }


def get_accessory_battery_status() -> dict:
    """
    Return accessory battery bank status (placeholder).

    Returns a dict with keys:
        voltage      – battery voltage in volts
        percent      – state-of-charge percentage (0–100)
        amps         – current draw in amps (positive = charging)
        healthy      – True when SoC is above 20%
    """
    return {
        "voltage": 12.4,
        "percent": 72.0,
        "amps": -1.8,
        "healthy": True,
    }
