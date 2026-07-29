"""
Main dashboard screen – tappable tiles for every RV system.

Layout is optimised for a 600 × 1024 vertical touchscreen.
Tiles are grouped by system: Water, Battery, Propane.
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
from logic.tank_logic import get_black_level, get_fresh_level, get_grey_level
from ui.load_screens import LoadPresetBar
from ui.widgets import CircleGauge, TileIcon

if TYPE_CHECKING:
    from ui.navigation import Navigator

# Refresh interval for live data (ms)
REFRESH_MS = 5_000


class SystemTile(QFrame):
    """A single tappable dashboard tile showing a short label and gauge."""

    def __init__(
        self,
        title: str,
        gauge: QWidget,
        navigator: "Navigator",
        detail_screen_factory,
        icon: QWidget | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._detail_factory = detail_screen_factory
        self._detail_screen = None

        self.setObjectName("SystemTile")
        self.setCursor(Qt.PointingHandCursor)
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setStyleSheet(
            "QFrame#SystemTile { background: #111827; border-radius: 16px; border: 1px solid #1f2937; }"
        )

        self._build_ui(title, gauge, icon)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, title: str, gauge: QWidget, icon: QWidget | None = None) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 14, 14, 14)
        layout.setSpacing(6)
        layout.setAlignment(Qt.AlignHCenter)

        # Gauge centered at top
        gauge.setFixedSize(60, 60)
        gauge_row = QHBoxLayout()
        gauge_row.addStretch()
        gauge_row.addWidget(gauge)
        gauge_row.addStretch()
        layout.addLayout(gauge_row)

        # Icon + short label row
        title_row = QHBoxLayout()
        title_row.setSpacing(4)
        title_row.setAlignment(Qt.AlignHCenter)
        if icon is not None:
            title_row.addWidget(icon)
        title_label = QLabel(title)
        title_label.setFont(QFont("Inter", 14, QFont.Bold))
        title_label.setStyleSheet("color: #f8fafc;")
        title_label.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        title_row.addWidget(title_label)
        layout.addLayout(title_row)

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
        Battery  – House | Accessory     (2 tiles across)
        Propane  – Tank 1 | Tank 2       (2 tiles across)
    """

    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._tiles: list[tuple[SystemTile, BarGauge, callable]] = []

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
        )

        nav = self._navigator

        # ── Water ──────────────────────────────────────────────────────
        content.addWidget(_section_header("Water"))

        fresh_data = get_fresh_level()
        fresh_gauge = CircleGauge(
            fresh_data["capacity_gallons"], fresh_data["current_gallons"],
            fill_color=QColor("#4fc3f7"), warn_threshold=0.20, warn_high=False,
        )
        fresh_tile = SystemTile(
            "Fresh", fresh_gauge, nav, lambda: FreshTankDetailScreen(nav),
            icon=TileIcon(TileIcon.WATER_DROP, QColor("#4fc3f7")),
        )
        fresh_tile.set_healthy(fresh_data["healthy"])

        grey_data = get_grey_level()
        grey_gauge = CircleGauge(
            grey_data["capacity_gallons"], grey_data["current_gallons"],
            fill_color=QColor("#78909c"), warn_threshold=0.80, warn_high=True,
        )
        grey_tile = SystemTile(
            "Grey", grey_gauge, nav, lambda: GreyTankDetailScreen(nav),
            icon=TileIcon(TileIcon.WASTE_TANK, QColor("#78909c")),
        )
        grey_tile.set_healthy(grey_data["healthy"])

        black_data = get_black_level()
        black_gauge = CircleGauge(
            black_data["capacity_gallons"], black_data["current_gallons"],
            fill_color=QColor("#424242"), warn_threshold=0.80, warn_high=True,
        )
        black_tile = SystemTile(
            "Black", black_gauge, nav, lambda: BlackTankDetailScreen(nav),
            icon=TileIcon(TileIcon.WASTE_TANK, QColor("#607d8b")),
        )
        black_tile.set_healthy(black_data["healthy"])

        content.addLayout(_tile_row([fresh_tile, grey_tile, black_tile]))

        self._tiles += [
            (fresh_tile, fresh_gauge, get_fresh_level),
            (grey_tile, grey_gauge, get_grey_level),
            (black_tile, black_gauge, get_black_level),
        ]

        # ── Battery ────────────────────────────────────────────────────
        content.addSpacing(16)
        content.addWidget(_section_header("Battery"))

        house_data = get_house_battery_status()
        house_gauge = CircleGauge(
            100, house_data["percent"],
            fill_color=QColor("#aed581"), warn_threshold=0.20, warn_high=False,
        )
        house_tile = SystemTile(
            "House", house_gauge, nav, lambda: HouseBatteryDetailScreen(nav),
            icon=TileIcon(TileIcon.BATTERY, QColor("#aed581")),
        )
        house_tile.set_healthy(house_data["healthy"])

        acc_data = get_accessory_battery_status()
        acc_gauge = CircleGauge(
            100, acc_data["percent"],
            fill_color=QColor("#aed581"), warn_threshold=0.20, warn_high=False,
        )
        acc_tile = SystemTile(
            "Accessory", acc_gauge, nav, lambda: AccessoryBatteryDetailScreen(nav),
            icon=TileIcon(TileIcon.BATTERY, QColor("#aed581")),
        )
        acc_tile.set_healthy(acc_data["healthy"])

        content.addLayout(_tile_row([house_tile, acc_tile]))

        self._tiles += [
            (house_tile, house_gauge, get_house_battery_status),
            (acc_tile, acc_gauge, get_accessory_battery_status),
        ]

        # ── Propane ────────────────────────────────────────────────────
        content.addSpacing(16)
        content.addWidget(_section_header("Propane"))

        p1_data = get_propane_status(1)
        p1_gauge = CircleGauge(
            100, p1_data["percent_full"],
            fill_color=QColor("#ffb74d"), warn_threshold=0.10, warn_high=False,
        )
        p1_tile = SystemTile(
            "Tank 1", p1_gauge, nav, lambda: PropaneDetailScreen(nav, tank_number=1),
            icon=TileIcon(TileIcon.PROPANE_TANK, QColor("#ffb74d")),
        )
        p1_tile.set_healthy(p1_data["healthy"])

        p2_data = get_propane_status(2)
        p2_gauge = CircleGauge(
            100, p2_data["percent_full"],
            fill_color=QColor("#ffb74d"), warn_threshold=0.10, warn_high=False,
        )
        p2_tile = SystemTile(
            "Tank 2", p2_gauge, nav, lambda: PropaneDetailScreen(nav, tank_number=2),
            icon=TileIcon(TileIcon.PROPANE_TANK, QColor("#ffb74d")),
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
                gauge.set_value(data["current_gallons"])
            elif "percent_full" in data:
                gauge.set_value(data["percent_full"])
            elif "percent" in data:
                gauge.set_value(data["percent"])

            tile.set_healthy(data.get("healthy", True))
