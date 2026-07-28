"""
Main dashboard screen – tappable tiles for every RV system.

Layout is optimised for a 600 × 1024 vertical touchscreen.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
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
from ui.widgets import BarGauge

if TYPE_CHECKING:
    from ui.navigation import Navigator

# Refresh interval for live data (ms)
REFRESH_MS = 5_000


class SystemTile(QFrame):
    """A single tappable dashboard tile."""

    def __init__(
        self,
        title: str,
        subtitle: str,
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
        self.setMinimumHeight(120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self._build_ui(title, subtitle, gauge)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self, title: str, subtitle: str, gauge: QWidget) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(16, 12, 16, 12)
        layout.setSpacing(14)

        # Gauge on the left
        gauge.setFixedSize(56, 90)
        layout.addWidget(gauge)

        # Text block
        text_col = QVBoxLayout()
        text_col.setSpacing(4)

        title_label = QLabel(title)
        title_label.setFont(QFont("Sans Serif", 14, QFont.Bold))
        title_label.setStyleSheet("color: #eceff1;")
        text_col.addWidget(title_label)

        sub_label = QLabel(subtitle)
        sub_label.setFont(QFont("Sans Serif", 11))
        sub_label.setStyleSheet("color: #90a4ae;")
        text_col.addWidget(sub_label)

        text_col.addStretch()

        self._status_dot = QLabel("●")
        self._status_dot.setFont(QFont("Sans Serif", 16))
        text_col.addWidget(self._status_dot)

        layout.addLayout(text_col)
        layout.addStretch()

        # Chevron hint
        arrow = QLabel("›")
        arrow.setFont(QFont("Sans Serif", 22))
        arrow.setStyleSheet("color: #546e7a;")
        layout.addWidget(arrow)

    def set_healthy(self, healthy: bool) -> None:
        color = "#66bb6a" if healthy else "#ef5350"
        self._status_dot.setStyleSheet(f"color: {color};")

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
            "QFrame#SystemTile { background: #1a2736; border-radius: 10px; }"
        )

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            "QFrame#SystemTile { background: #152030; border-radius: 10px; }"
        )


class MainScreen(QWidget):
    """
    Main dashboard showing tiles for all RV systems.
    Designed for 600 × 1024 vertical display.
    """

    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._tiles: list[tuple[SystemTile, callable, callable]] = []

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

        # Header bar
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #0d1b2a;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 0, 16, 0)

        title = QLabel("RV Monitor")
        title.setFont(QFont("Sans Serif", 18, QFont.Bold))
        title.setStyleSheet("color: #4fc3f7;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        root.addWidget(header)

        # Scrollable tile grid
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { background: #0d1b2a; border: none; }")
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        container = QWidget()
        container.setStyleSheet("background: #0d1b2a;")
        grid = QGridLayout(container)
        grid.setContentsMargins(12, 12, 12, 12)
        grid.setSpacing(10)

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

        def make_fresh_tile():
            data = get_fresh_level()
            gauge = BarGauge(
                data["capacity_gallons"],
                data["current_gallons"],
                fill_color=QColor("#4fc3f7"),
                warn_threshold=0.20,
                warn_high=False,
            )
            tile = SystemTile(
                "Fresh Water",
                f"{data['capacity_gallons']:.0f} gal tank",
                gauge,
                nav,
                lambda: FreshTankDetailScreen(nav),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, get_fresh_level

        def make_grey_tile():
            data = get_grey_level()
            gauge = BarGauge(
                data["capacity_gallons"],
                data["current_gallons"],
                fill_color=QColor("#78909c"),
                warn_threshold=0.80,
                warn_high=True,
            )
            tile = SystemTile(
                "Grey Water",
                f"{data['capacity_gallons']:.0f} gal tank",
                gauge,
                nav,
                lambda: GreyTankDetailScreen(nav),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, get_grey_level

        def make_black_tile():
            data = get_black_level()
            gauge = BarGauge(
                data["capacity_gallons"],
                data["current_gallons"],
                fill_color=QColor("#424242"),
                warn_threshold=0.80,
                warn_high=True,
            )
            tile = SystemTile(
                "Black Water",
                f"{data['capacity_gallons']:.0f} gal tank",
                gauge,
                nav,
                lambda: BlackTankDetailScreen(nav),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, get_black_level

        def make_house_batt_tile():
            data = get_house_battery_status()
            gauge = BarGauge(
                100,
                data["percent"],
                fill_color=QColor("#aed581"),
                warn_threshold=0.20,
                warn_high=False,
            )
            tile = SystemTile(
                "House Battery",
                "Battery bank",
                gauge,
                nav,
                lambda: HouseBatteryDetailScreen(nav),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, get_house_battery_status

        def make_acc_batt_tile():
            data = get_accessory_battery_status()
            gauge = BarGauge(
                100,
                data["percent"],
                fill_color=QColor("#aed581"),
                warn_threshold=0.20,
                warn_high=False,
            )
            tile = SystemTile(
                "Accessory Battery",
                "Battery bank",
                gauge,
                nav,
                lambda: AccessoryBatteryDetailScreen(nav),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, get_accessory_battery_status

        def make_propane1_tile():
            data = get_propane_status(1)
            gauge = BarGauge(
                100,
                data["percent_full"],
                fill_color=QColor("#ffb74d"),
                warn_threshold=0.10,
                warn_high=False,
            )
            tile = SystemTile(
                "Propane Tank 1",
                "LP gas",
                gauge,
                nav,
                lambda: PropaneDetailScreen(nav, tank_number=1),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, lambda: get_propane_status(1)

        def make_propane2_tile():
            data = get_propane_status(2)
            gauge = BarGauge(
                100,
                data["percent_full"],
                fill_color=QColor("#ffb74d"),
                warn_threshold=0.10,
                warn_high=False,
            )
            tile = SystemTile(
                "Propane Tank 2",
                "LP gas",
                gauge,
                nav,
                lambda: PropaneDetailScreen(nav, tank_number=2),
            )
            tile.set_healthy(data["healthy"])
            return tile, gauge, lambda: get_propane_status(2)

        tile_factories = [
            make_fresh_tile,
            make_grey_tile,
            make_black_tile,
            make_house_batt_tile,
            make_acc_batt_tile,
            make_propane1_tile,
            make_propane2_tile,
        ]

        for idx, factory in enumerate(tile_factories):
            tile, gauge, data_fn = factory()
            row, col = divmod(idx, 2)
            grid.addWidget(tile, row, col)
            self._tiles.append((tile, gauge, data_fn))

        # Make columns equal width
        grid.setColumnStretch(0, 1)
        grid.setColumnStretch(1, 1)

        scroll.setWidget(container)
        root.addWidget(scroll)

    # ------------------------------------------------------------------
    # Data refresh
    # ------------------------------------------------------------------

    def _refresh_data(self) -> None:
        for tile, gauge, data_fn in self._tiles:
            data = data_fn()

            # Determine value/capacity based on whether it's a tank or battery
            if "current_gallons" in data:
                gauge.set_value(data["current_gallons"])
            elif "percent_full" in data:
                gauge.set_value(data["percent_full"])
            elif "percent" in data:
                gauge.set_value(data["percent"])

            tile.set_healthy(data.get("healthy", True))
