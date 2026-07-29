"""
Battery logic – placeholder until real BMS sensors are connected.
"""

# Usable capacity of the house battery bank in amp-hours (placeholder)
HOUSE_BATTERY_CAPACITY_AH = 200.0


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


def get_power_days_remaining() -> float | None:
    """
    Estimate days until the house battery bank is depleted.

    Net current = house battery amps + solar charging amps.
    A negative net means the battery is discharging; a positive or zero
    net means it is holding or gaining charge, so there is no depletion risk.

    Returns:
        float  – days remaining at the current net discharge rate, or
        None   – battery is charging / net draw is zero (no depletion risk).
    """
    from logic.solar_logic import get_solar_charger_status

    house = get_house_battery_status()
    solar = get_solar_charger_status()

    # house amps: negative = consuming; solar amps: positive = charging
    net_amps = house["amps"] + solar["amps"]

    if net_amps >= 0:
        return None  # charging or balanced – no depletion risk

    ah_remaining = (house["percent"] / 100.0) * HOUSE_BATTERY_CAPACITY_AH
    hours_remaining = ah_remaining / abs(net_amps)
    return round(hours_remaining / 24.0, 1)
