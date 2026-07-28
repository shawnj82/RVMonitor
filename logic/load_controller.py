"""
Load controller – manages controllable RV loads and preset modes.

Loads
-----
pump                  fresh-water pump
starlink              Starlink satellite dish / router
router                secondary WiFi router
water_heater_electric electric water heater element
water_heater_propane  propane water heater
inverter              DC→AC inverter

Preset modes
------------
Storage     everything off; safe for long-term storage
Boondock    propane WH, pump, Starlink, router, inverter on
Full Hookup electric WH, pump, Starlink, router on; inverter / propane WH off
Custom      user-defined via individual toggles

A module-level singleton ``controller`` is imported by UI components so that
all parts of the app share the same state.
"""

from __future__ import annotations

from PySide6.QtCore import QObject, Signal

# ── Load catalogue ──────────────────────────────────────────────────────────

LOADS: list[str] = [
    "pump",
    "starlink",
    "router",
    "water_heater_electric",
    "water_heater_propane",
    "inverter",
]

LOAD_LABELS: dict[str, str] = {
    "pump": "Water Pump",
    "starlink": "Starlink",
    "router": "Router",
    "water_heater_electric": "Water Heater (Electric)",
    "water_heater_propane": "Water Heater (Propane)",
    "inverter": "Inverter",
}

# ── Preset definitions ──────────────────────────────────────────────────────

PRESETS: dict[str, dict[str, bool]] = {
    "Storage": {
        "pump": False,
        "starlink": False,
        "router": False,
        "water_heater_electric": False,
        "water_heater_propane": False,
        "inverter": False,
    },
    "Boondock": {
        "pump": True,
        "starlink": True,
        "router": True,
        "water_heater_electric": False,
        "water_heater_propane": True,
        "inverter": True,
    },
    "Full Hookup": {
        "pump": False,
        "starlink": True,
        "router": True,
        "water_heater_electric": True,
        "water_heater_propane": False,
        "inverter": False,
    },
}

# ── Controller ──────────────────────────────────────────────────────────────


class LoadController(QObject):
    """
    In-memory store for load on/off states.

    Signals
    -------
    mode_changed(str)
        Emitted whenever the active mode changes.  The argument is one of
        ``"Storage"``, ``"Boondock"``, ``"Full Hookup"``, or ``"Custom"``.
    """

    mode_changed = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._states: dict[str, bool] = {load: False for load in LOADS}
        self._mode: str = "Storage"

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def apply_preset(self, mode: str) -> None:
        """Apply a named preset and emit ``mode_changed``."""
        if mode not in PRESETS:
            raise ValueError(f"Unknown preset: {mode!r}")
        self._states.update(PRESETS[mode])
        self._mode = mode
        self.mode_changed.emit(mode)

    def enter_manual_mode(self) -> None:
        """Mark the active mode as Manual without altering load states."""
        self._mode = "Manual"
        self.mode_changed.emit("Manual")

    def toggle_load(self, load: str) -> None:
        """Flip one load and set the active mode to Custom."""
        if load not in self._states:
            raise ValueError(f"Unknown load: {load!r}")
        self._states[load] = not self._states[load]
        self._mode = "Manual"
        self.mode_changed.emit("Manual")

    def get_load_states(self) -> dict[str, bool]:
        """Return a snapshot of all load states."""
        return dict(self._states)

    def get_active_mode(self) -> str:
        """Return the current mode name."""
        return self._mode


# Module-level singleton shared by all UI components
controller: LoadController = LoadController()
