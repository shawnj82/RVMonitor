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

    Compares daily solar generation against daily consumption:
        daily_consumption_ah = abs(house amps) * 24 hours
        daily_generation_ah  = solar daily_ah (watts × peak sun hours / voltage)

    A net surplus (generation >= consumption) means no depletion risk.

    Returns:
        float  – days remaining at the current net daily deficit rate, or
        None   – daily generation covers consumption (surplus, no depletion risk).
    """
    from logic.solar_logic import get_solar_charger_status

    house = get_house_battery_status()
    solar = get_solar_charger_status()

    daily_consumption_ah = abs(house["amps"]) * 24.0
    daily_generation_ah = solar.get("daily_ah", 0.0)

    net_daily_ah = daily_generation_ah - daily_consumption_ah

    if net_daily_ah >= 0:
        return None  # surplus – daily generation meets or exceeds consumption

    ah_remaining = (house["percent"] / 100.0) * HOUSE_BATTERY_CAPACITY_AH
    return round(ah_remaining / abs(net_daily_ah), 1)
