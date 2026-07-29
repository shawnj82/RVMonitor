# RVMonitor

A Raspberry Pi touchscreen dashboard for monitoring and controlling RV systems — water tanks, batteries, solar, and propane — with a dark UI built for a 600 × 1024 vertical display.

---

## Features

### Dashboard tiles
The main screen groups all systems into scrollable sections. Each tile shows a fillable gauge with percentage and a color-coded health indicator.

**Water**
- Fresh tank – remaining gallons tracked via ESP32 flow meter
- Grey tank – estimated fill based on fresh outflow (50% split)
- Black tank – estimated fill based on fresh outflow (50% split)
- Section footer: days until water becomes the limiting constraint (fresh runs out *or* grey/black fill up)

**Power**
- House battery – state of charge (%), voltage, and trend arrow (charging / discharging)
- Accessory battery – same as house
- Solar charger – instantaneous watts and amps; icon reflects production level (sun / light cloud / heavy cloud / moon)
- Section footer: days of battery capacity remaining based on daily solar generation vs. daily consumption; shows **Surplus** when generation covers consumption

**Propane**
- Tank 1 and Tank 2 – fill percentage and pressure (PSI)
- Section footer: combined days of propane remaining at the current daily usage rate

### Detail screens
Tapping any tile navigates to a full-screen detail view with a larger gauge and additional numeric values.

### Load management
A persistent bottom bar offers one-tap preset modes:

| Mode | Description |
|------|-------------|
| Storage | All loads off — safe for long-term storage |
| Boondock | Propane water heater, pump, Starlink, router, inverter on |
| Full Hookup | Electric water heater, pump, Starlink, router on; inverter off |
| Manual | Individual toggle for each load |

---

## Project structure

```
RVMonitor/
├── main.py                   # Application entry point
├── requirements.txt
├── logic/
│   ├── battery_logic.py      # House & accessory battery status, power days remaining
│   ├── solar_logic.py        # Solar charger status, daily Ah generation
│   ├── tank_logic.py         # Fresh / grey / black tank levels, water days remaining
│   ├── propane_logic.py      # Propane tank status, propane days remaining
│   └── load_controller.py    # Load on/off states and preset modes
├── sensors/
│   ├── flow_meter_client.py  # ESP32 flow meter client (HTTP/MQTT, placeholder)
│   └── placeholder_sensors.py
├── ui/
│   ├── main_screen.py        # Main dashboard
│   ├── detail_screens.py     # Per-system detail screens
│   ├── load_screens.py       # Load preset bar and custom load screen
│   ├── navigation.py         # Screen stack navigator
│   └── widgets.py            # TileIcon, BarGauge, CircleGauge, SystemTile
└── tests/
    ├── test_tank_logic.py
    ├── test_battery_propane_logic.py
    ├── test_solar_logic.py
    └── test_flow_meter_client.py
```

---

## Requirements

- Python 3.11+
- PySide6 ≥ 6.4.0

---

## Setup

```bash
pip install -r requirements.txt
```

---

## Running

```bash
# Desktop (windowed, 600 × 1024)
python main.py

# Raspberry Pi (full-screen)
python main.py --fullscreen
```

---

## Configuration

All placeholder constants are at the top of their respective logic modules and can be replaced with live sensor values when hardware is connected.

| File | Constant | Default | Description |
|------|----------|---------|-------------|
| `logic/tank_logic.py` | `DAILY_USAGE_GALLONS` | `15.0` | Estimated daily fresh-water use (gal) |
| `logic/tank_logic.py` | `FRESH_TANK_CAPACITY_GALLONS` | `60.0` | Fresh tank size (gal) |
| `logic/tank_logic.py` | `GREY_TANK_CAPACITY_GALLONS` | `60.0` | Grey tank size (gal) |
| `logic/tank_logic.py` | `BLACK_TANK_CAPACITY_GALLONS` | `40.0` | Black tank size (gal) |
| `logic/battery_logic.py` | `HOUSE_BATTERY_CAPACITY_AH` | `200.0` | Usable house battery capacity (Ah) |
| `logic/solar_logic.py` | `PEAK_SUN_HOURS` | `5.0` | Estimated daily peak sun hours |
| `logic/propane_logic.py` | `DAILY_USAGE_PERCENT` | `5.0` | Daily propane use (% of one full tank) |
| `sensors/flow_meter_client.py` | `host` | `192.168.1.100` | ESP32 flow meter IP address |

### Connecting real sensors

Each `logic/` module contains placeholder return values. To wire in live data:

- **Flow meter**: implement `FlowMeterClient.connect()`, `get_flow_rate()`, and `get_total_gallons_used()` in `sensors/flow_meter_client.py` with real HTTP/MQTT calls to the ESP32.
- **Batteries**: replace the hardcoded dicts in `battery_logic.get_house_battery_status()` / `get_accessory_battery_status()` with BMS reads.
- **Solar**: replace the hardcoded values in `solar_logic.get_solar_charger_status()` with MPPT controller telemetry; populate `daily_ah` from the controller's daily total for the most accurate surplus calculation.
- **Propane**: replace `propane_logic.get_propane_status()` with pressure sensor reads.

---

## Testing

```bash
python -m pytest tests/ -v
```
