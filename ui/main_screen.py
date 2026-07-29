"""
Main dashboard screen – tappable tiles for every RV system.

Layout is optimised for a 600 × 1024 vertical touchscreen.
Tiles are grouped by system: Water, Power, Propane.
Each group has a section header; tiles show a short name only.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from logic.battery_logic import get_accessory_battery_status, get_house_battery_status
from logic.propane_logic import get_propane_status
from logic.solar_logic import get_solar_charger_status
from logic.tank_logic import get_black_level, get_fresh_level, get_grey_level
from ui.load_screens import LoadPresetBar
from ui.widgets import TileIcon

if TYPE_CHECKING:
    from ui.navigation import Navigator

# Refresh interval for live data (ms)
REFRESH_MS = 5_000


class SystemTile(QFrame):
    """A single tappable dashboard tile showing label and icon gauge."""

    def __init__(
        self,
        title: str,
        gauge: QWidget,
        navigator: "Navigator",
        detail_screen_factory,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._detail_factory = detail_screen_factory
        self._detail_screen = None

        self.setObjectName("SystemTile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(210)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "QFrame#SystemTile { background: #111827; border-radius: 16px; border: 1px solid #1f2937; }"
        )

        self._build_ui(title, gauge)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, title: str, gauge: QWidget) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignHCenter)

        # Name at the top
        title_label = QLabel(title)
        title_label.setFont(QFont("Inter", 13, QFont.Bold))
        title_label.setStyleSheet("color: #f8fafc;")
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        # Large status icon gauge centered below
        gauge_row = QHBoxLayout()
        gauge_row.setAlignment(Qt.AlignHCenter)
        gauge_row.addWidget(gauge)
        layout.addLayout(gauge_row)

        # Health indicator pill
        pill_row = QHBoxLayout()
        pill_row.addStretch()
        self._status_dot = QLabel()
        self._status_dot.setFixedSize(40, 8)
        self._status_dot.setStyleSheet("background: #16a34a; border-radius: 4px;")
        pill_row.addWidget(self._status_dot)
        pill_row.addStretch()
        layout.addLayout(pill_row)

    def set_healthy(self, healthy: bool) -> None:
        color = "#16a34a" if healthy else "#dc2626"
        self._status_dot.setStyleSheet(f"background: {color}; border-radius: 4px;")

    # ------------------------------------------------------------------
    # Interaction
    # ------------------------------------------------------------------

    def mousePressEvent(self, event) -> None:  # noqa: N802
        if event.button() == Qt.LeftButton:
            if self._detail_screen is None:
                self._detail_screen = self._detail_factory()
            self._navigator.push(self._detail_screen)

    # ------------------------------------------------------------------
    # Style
    # ------------------------------------------------------------------

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            "QFrame#SystemTile { background: #1a2234; border-radius: 16px; border: 1px solid #2d3f55; }"
        )

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            "QFrame#SystemTile { background: #111827; border-radius: 16px; border: 1px solid #1f2937; }"
        )


def _section_header(text: str) -> QLabel:
    """Return a styled section-group label (e.g. 'Water', 'Battery')."""
    label = QLabel(text.upper())
    label.setFont(QFont("Inter", 10, QFont.Bold))
    label.setStyleSheet(
        "color: #4b5563; letter-spacing: 3px; padding: 12px 0 4px 4px;"
    )
    label.setTextFormat(Qt.PlainText)
    return label


def _tile_row(tiles: list[SystemTile]) -> QHBoxLayout:
    """Pack a list of tiles into an evenly-spaced horizontal row."""
    row = QHBoxLayout()
    row.setSpacing(12)
    for tile in tiles:
        row.addWidget(tile)
    return row


class MainScreen(QWidget):
    """
    Main dashboard showing grouped tiles for all RV systems.
    Designed for 600 × 1024 vertical display.

    Groups:
        Water    – Fresh | Grey | Black  (3 tiles across)
        Power    – House | Accessory | Solar (3 tiles across)
        Propane  – Tank 1 | Tank 2       (2 tiles across)
    """

    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._tiles: list[tuple[SystemTile, TileIcon, callable]] = []

        self._build_ui()
        self._refresh_data()

        # Auto-refresh
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_data)
        self._timer.start(REFRESH_MS)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Scrollable content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #08090e; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: #08090e;")
        content = QVBoxLayout(container)
        content.setContentsMargins(12, 14, 12, 14)
        content.setSpacing(6)

        # Import detail screens here to avoid circular imports
        from ui.detail_screens import (
            AccessoryBatteryDetailScreen,
            BlackTankDetailScreen,
            FreshTankDetailScreen,
            GreyTankDetailScreen,
            HouseBatteryDetailScreen,
            PropaneDetailScreen,
            SolarChargerDetailScreen,
        )

        nav = self._navigator

        # ── Water ──────────────────────────────────────────────────────
        content.addWidget(_section_header("Water"))

        fresh_data = get_fresh_level()
        fresh_gauge = TileIcon(
            TileIcon.WATER_DROP,
            QColor("#4fc3f7"),
            size=102,
            level_percent=(fresh_data["current_gallons"] / max(fresh_data["capacity_gallons"], 1.0)) * 100.0,
            show_percent=True,
            warn_threshold=0.20,
            warn_high=False,
        )
        fresh_tile = SystemTile(
            "Fresh", fresh_gauge, nav, lambda: FreshTankDetailScreen(nav),
        )
        fresh_tile.set_healthy(fresh_data["healthy"])

        grey_data = get_grey_level()
        grey_gauge = TileIcon(
            TileIcon.WASTE_TANK,
            QColor("#78909c"),
            size=102,
            level_percent=(grey_data["current_gallons"] / max(grey_data["capacity_gallons"], 1.0)) * 100.0,
            show_percent=True,
            warn_threshold=0.80,
            warn_high=True,
        )
        grey_tile = SystemTile(
            "Grey", grey_gauge, nav, lambda: GreyTankDetailScreen(nav),
        )
        grey_tile.set_healthy(grey_data["healthy"])

        black_data = get_black_level()
        black_gauge = TileIcon(
            TileIcon.WASTE_TANK,
            QColor("#607d8b"),
            size=102,
            level_percent=(black_data["current_gallons"] / max(black_data["capacity_gallons"], 1.0)) * 100.0,
            show_percent=True,
            warn_threshold=0.80,
            warn_high=True,
        )
        black_tile = SystemTile(
            "Black", black_gauge, nav, lambda: BlackTankDetailScreen(nav),
        )
        black_tile.set_healthy(black_data["healthy"])

        content.addLayout(_tile_row([fresh_tile, grey_tile, black_tile]))

        self._tiles += [
            (fresh_tile, fresh_gauge, get_fresh_level),
            (grey_tile, grey_gauge, get_grey_level),
            (black_tile, black_gauge, get_black_level),
        ]

        # ── Power ──────────────────────────────────────────────────────
        content.addSpacing(16)
        content.addWidget(_section_header("Power"))

        house_data = get_house_battery_status()
        house_gauge = TileIcon(
            TileIcon.BATTERY,
            QColor("#aed581"),
            size=102,
            level_percent=house_data["percent"],
            show_percent=True,
            warn_threshold=0.20,
            warn_high=False,
            show_trend=True,
        )
        house_gauge.set_trend(1 if house_data.get("amps", 0.0) > 0 else -1 if house_data.get("amps", 0.0) < 0 else 0)
        house_tile = SystemTile(
            "House", house_gauge, nav, lambda: HouseBatteryDetailScreen(nav),
        )
        house_tile.set_healthy(house_data["healthy"])

        acc_data = get_accessory_battery_status()
        acc_gauge = TileIcon(
            TileIcon.BATTERY,
            QColor("#aed581"),
            size=102,
            level_percent=acc_data["percent"],
            show_percent=True,
            warn_threshold=0.20,
            warn_high=False,
            show_trend=True,
        )
        acc_gauge.set_trend(1 if acc_data.get("amps", 0.0) > 0 else -1 if acc_data.get("amps", 0.0) < 0 else 0)
        acc_tile = SystemTile(
            "Accessory", acc_gauge, nav, lambda: AccessoryBatteryDetailScreen(nav),
        )
        acc_tile.set_healthy(acc_data["healthy"])

        solar_data = get_solar_charger_status()
        solar_gauge = TileIcon(
            TileIcon.SOLAR,
            QColor("#facc15"),
            size=102,
            level_percent=solar_data["percent"],
            show_percent=True,
            warn_threshold=0.15,
            warn_high=False,
        )
        solar_gauge.set_solar_mode(solar_data.get("mode", "sun"))
        solar_tile = SystemTile(
            "Solar", solar_gauge, nav, lambda: SolarChargerDetailScreen(nav),
        )
        solar_tile.set_healthy(solar_data["healthy"])

        content.addLayout(_tile_row([house_tile, acc_tile, solar_tile]))

        self._tiles += [
            (house_tile, house_gauge, get_house_battery_status),
            (acc_tile, acc_gauge, get_accessory_battery_status),
            (solar_tile, solar_gauge, get_solar_charger_status),
        ]

        # ── Propane ────────────────────────────────────────────────────
        content.addSpacing(16)
        content.addWidget(_section_header("Propane"))

        p1_data = get_propane_status(1)
        p1_gauge = TileIcon(
            TileIcon.PROPANE_TANK,
            QColor("#ffb74d"),
            size=102,
            level_percent=p1_data["percent_full"],
            show_percent=True,
            warn_threshold=0.10,
            warn_high=False,
        )
        p1_tile = SystemTile(
            "Tank 1", p1_gauge, nav, lambda: PropaneDetailScreen(nav, tank_number=1),
        )
        p1_tile.set_healthy(p1_data["healthy"])

        p2_data = get_propane_status(2)
        p2_gauge = TileIcon(
            TileIcon.PROPANE_TANK,
            QColor("#ffb74d"),
            size=102,
            level_percent=p2_data["percent_full"],
            show_percent=True,
            warn_threshold=0.10,
            warn_high=False,
        )
        p2_tile = SystemTile(
            "Tank 2", p2_gauge, nav, lambda: PropaneDetailScreen(nav, tank_number=2),
        )
        p2_tile.set_healthy(p2_data["healthy"])

        content.addLayout(_tile_row([p1_tile, p2_tile]))

        self._tiles += [
            (p1_tile, p1_gauge, lambda: get_propane_status(1)),
            (p2_tile, p2_gauge, lambda: get_propane_status(2)),
        ]

        content.addStretch()
        scroll.setWidget(container)
        root.addWidget(scroll)

        # Preset bar pinned to the bottom
        root.addWidget(LoadPresetBar(self._navigator, self))

    def _refresh_data(self) -> None:
        for tile, gauge, data_fn in self._tiles:
            data = data_fn()

            if "current_gallons" in data:
                level = (
                    data["current_gallons"] / max(data.get("capacity_gallons", 1.0), 1.0)
                ) * 100.0
                gauge.set_level(level)
            elif "percent_full" in data:
                gauge.set_level(data["percent_full"])
            elif "percent" in data:
                gauge.set_level(data["percent"])
                amps = data.get("amps", 0.0)
                gauge.set_trend(1 if amps > 0 else -1 if amps < 0 else 0)
                if "mode" in data:
                    gauge.set_solar_mode(data["mode"])

            tile.set_healthy(data.get("healthy", True))
