"""
Solar charger logic – placeholder until MPPT/solar telemetry is connected.
"""


def _mode_from_percent(percent: float) -> str:
    if percent >= 70.0:
        return "sun"
    if percent >= 40.0:
        return "cloud_light"
    if percent >= 15.0:
        return "cloud_heavy"
    return "moon"


def get_solar_charger_status() -> dict:
    """
    Return solar charger status (placeholder).

    Returns a dict with keys:
        watts   – instantaneous solar charger output in watts
        percent – production level percentage (0–100)
        mode    – icon mode: sun/cloud_light/cloud_heavy/moon
        healthy – True when production is above a low threshold
    """
    percent = 62.0
    watts = 455.0
    amps = round(watts / 14.4, 1)
    return {
        "watts": watts,
        "amps": amps,
        "percent": percent,
        "mode": _mode_from_percent(percent),
        "healthy": percent >= 15.0,
    }
