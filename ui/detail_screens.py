"""
Detail screens for each RV system tile.

Each screen contains:
  - A larger gauge graphic
  - Numeric values
  - Placeholder health logic description
  - Back button to return to the main dashboard

All screens follow the same BaseDetailScreen pattern.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from logic.battery_logic import get_accessory_battery_status, get_house_battery_status
from logic.propane_logic import get_propane_status
from logic.tank_logic import get_black_level, get_fresh_level, get_grey_level
from ui.widgets import BarGauge, CircleGauge

if TYPE_CHECKING:
    from ui.navigation import Navigator

REFRESH_MS = 5_000


# ---------------------------------------------------------------------------
# Base screen
# ---------------------------------------------------------------------------


class BaseDetailScreen(QWidget):
    """
    Common shell for all detail screens.

    Subclasses implement ``_build_content`` to populate ``self._content_layout``
    and ``_refresh_values`` to update the numeric labels on each timer tick.
    """

    def __init__(
        self,
        navigator: "Navigator",
        title: str,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._value_labels: dict[str, QLabel] = {}

        self._build_shell(title)
        self._build_content()
        self._refresh_values()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh_values)
        self._timer.start(REFRESH_MS)

    # ------------------------------------------------------------------
    # Shell (header + back button)
    # ------------------------------------------------------------------

    def _build_shell(self, title: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #0d1b2a;")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(8, 0, 16, 0)

        back_btn = QPushButton("‹ Back")
        back_btn.setFont(QFont("Sans Serif", 14))
        back_btn.setStyleSheet(
            "QPushButton { color: #4fc3f7; background: transparent; border: none; padding: 4px 8px; }"
            "QPushButton:pressed { color: #0288d1; }"
        )
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self._navigator.pop)
        header_layout.addWidget(back_btn)

        title_label = QLabel(title)
        title_label.setFont(QFont("Sans Serif", 16, QFont.Bold))
        title_label.setStyleSheet("color: #eceff1;")
        title_label.setAlignment(Qt.AlignCenter)
        header_layout.addWidget(title_label, stretch=1)

        root.addWidget(header)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #1e2a38;")
        root.addWidget(divider)

        # Content area
        self._content_widget = QWidget()
        self._content_widget.setStyleSheet("background: #0d1b2a;")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(24, 20, 24, 20)
        self._content_layout.setSpacing(16)

        root.addWidget(self._content_widget, stretch=1)

    # ------------------------------------------------------------------
    # Helpers for subclasses
    # ------------------------------------------------------------------

    def _add_gauge(self, gauge: QWidget) -> None:
        gauge.setFixedSize(180, 180)
        wrapper = QHBoxLayout()
        wrapper.addStretch()
        wrapper.addWidget(gauge)
        wrapper.addStretch()
        self._content_layout.addLayout(wrapper)

    def _add_value_row(self, key: str, label_text: str, value_text: str = "—") -> None:
        row = QHBoxLayout()

        label = QLabel(label_text)
        label.setFont(QFont("Sans Serif", 13))
        label.setStyleSheet("color: #90a4ae;")

        value = QLabel(value_text)
        value.setFont(QFont("Sans Serif", 13, QFont.Bold))
        value.setStyleSheet("color: #eceff1;")
        value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        value.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        row.addWidget(label)
        row.addWidget(value)
        self._content_layout.addLayout(row)
        self._value_labels[key] = value

    def _add_health_banner(self) -> None:
        self._health_label = QLabel()
        self._health_label.setFont(QFont("Sans Serif", 13, QFont.Bold))
        self._health_label.setAlignment(Qt.AlignCenter)
        self._health_label.setMinimumHeight(40)
        self._health_label.setStyleSheet(
            "border-radius: 8px; padding: 6px;"
        )
        self._content_layout.addWidget(self._health_label)

    def _set_health(self, healthy: bool) -> None:
        if healthy:
            self._health_label.setText("● System healthy")
            self._health_label.setStyleSheet(
                "color: #66bb6a; background: #1b2f1f; border-radius: 8px; padding: 6px;"
            )
        else:
            self._health_label.setText("⚠ Attention required")
            self._health_label.setStyleSheet(
                "color: #ef5350; background: #2f1b1b; border-radius: 8px; padding: 6px;"
            )

    # ------------------------------------------------------------------
    # To be implemented by subclasses
    # ------------------------------------------------------------------

    def _build_content(self) -> None:
        raise NotImplementedError

    def _refresh_values(self) -> None:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Fresh Water Tank
# ---------------------------------------------------------------------------


class FreshTankDetailScreen(BaseDetailScreen):
    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, "Fresh Water Tank", parent)

    def _build_content(self) -> None:
        data = get_fresh_level()
        self._gauge = CircleGauge(
            data["capacity_gallons"],
            data["current_gallons"],
            fill_color=QColor("#4fc3f7"),
            warn_threshold=0.20,
            warn_high=False,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("capacity", "Capacity")
        self._add_value_row("current", "Remaining")
        self._add_value_row("percent", "Level")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_fresh_level()
        if self._gauge:
            self._gauge.set_value(data["current_gallons"])
        self._value_labels["capacity"].setText(f"{data['capacity_gallons']:.0f} gal")
        self._value_labels["current"].setText(f"{data['current_gallons']:.1f} gal")
        self._value_labels["percent"].setText(f"{data['percent_full']:.1f} %")
        self._set_health(data["healthy"])


# ---------------------------------------------------------------------------
# Grey Water Tank
# ---------------------------------------------------------------------------


class GreyTankDetailScreen(BaseDetailScreen):
    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, "Grey Water Tank", parent)

    def _build_content(self) -> None:
        data = get_grey_level()
        self._gauge = CircleGauge(
            data["capacity_gallons"],
            data["current_gallons"],
            fill_color=QColor("#78909c"),
            warn_threshold=0.80,
            warn_high=True,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("capacity", "Capacity")
        self._add_value_row("current", "Accumulated")
        self._add_value_row("percent", "Level")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_grey_level()
        if self._gauge:
            self._gauge.set_value(data["current_gallons"])
        self._value_labels["capacity"].setText(f"{data['capacity_gallons']:.0f} gal")
        self._value_labels["current"].setText(f"{data['current_gallons']:.1f} gal")
        self._value_labels["percent"].setText(f"{data['percent_full']:.1f} %")
        self._set_health(data["healthy"])


# ---------------------------------------------------------------------------
# Black Water Tank
# ---------------------------------------------------------------------------


class BlackTankDetailScreen(BaseDetailScreen):
    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, "Black Water Tank", parent)

    def _build_content(self) -> None:
        data = get_black_level()
        self._gauge = CircleGauge(
            data["capacity_gallons"],
            data["current_gallons"],
            fill_color=QColor("#424242"),
            warn_threshold=0.80,
            warn_high=True,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("capacity", "Capacity")
        self._add_value_row("current", "Accumulated")
        self._add_value_row("percent", "Level")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_black_level()
        if self._gauge:
            self._gauge.set_value(data["current_gallons"])
        self._value_labels["capacity"].setText(f"{data['capacity_gallons']:.0f} gal")
        self._value_labels["current"].setText(f"{data['current_gallons']:.1f} gal")
        self._value_labels["percent"].setText(f"{data['percent_full']:.1f} %")
        self._set_health(data["healthy"])


# ---------------------------------------------------------------------------
# House Battery
# ---------------------------------------------------------------------------


class HouseBatteryDetailScreen(BaseDetailScreen):
    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, "House Battery Bank", parent)

    def _build_content(self) -> None:
        data = get_house_battery_status()
        self._gauge = CircleGauge(
            100,
            data["percent"],
            fill_color=QColor("#aed581"),
            warn_threshold=0.20,
            warn_high=False,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("voltage", "Voltage")
        self._add_value_row("percent", "State of Charge")
        self._add_value_row("amps", "Current")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_house_battery_status()
        if self._gauge:
            self._gauge.set_value(data["percent"])
        self._value_labels["voltage"].setText(f"{data['voltage']:.1f} V")
        self._value_labels["percent"].setText(f"{data['percent']:.1f} %")
        amps = data["amps"]
        sign = "+" if amps >= 0 else ""
        self._value_labels["amps"].setText(f"{sign}{amps:.1f} A")
        self._set_health(data["healthy"])


# ---------------------------------------------------------------------------
# Accessory Battery
# ---------------------------------------------------------------------------


class AccessoryBatteryDetailScreen(BaseDetailScreen):
    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, "Accessory Battery Bank", parent)

    def _build_content(self) -> None:
        data = get_accessory_battery_status()
        self._gauge = CircleGauge(
            100,
            data["percent"],
            fill_color=QColor("#aed581"),
            warn_threshold=0.20,
            warn_high=False,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("voltage", "Voltage")
        self._add_value_row("percent", "State of Charge")
        self._add_value_row("amps", "Current")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_accessory_battery_status()
        if self._gauge:
            self._gauge.set_value(data["percent"])
        self._value_labels["voltage"].setText(f"{data['voltage']:.1f} V")
        self._value_labels["percent"].setText(f"{data['percent']:.1f} %")
        amps = data["amps"]
        sign = "+" if amps >= 0 else ""
        self._value_labels["amps"].setText(f"{sign}{amps:.1f} A")
        self._set_health(data["healthy"])


# ---------------------------------------------------------------------------
# Propane
# ---------------------------------------------------------------------------


class PropaneDetailScreen(BaseDetailScreen):
    def __init__(
        self,
        navigator: "Navigator",
        tank_number: int = 1,
        parent: QWidget | None = None,
    ) -> None:
        self._tank_number = tank_number
        self._gauge: CircleGauge | None = None
        super().__init__(navigator, f"Propane Tank {tank_number}", parent)

    def _build_content(self) -> None:
        data = get_propane_status(self._tank_number)
        self._gauge = CircleGauge(
            100,
            data["percent_full"],
            fill_color=QColor("#ffb74d"),
            warn_threshold=0.10,
            warn_high=False,
        )
        self._add_gauge(self._gauge)
        self._add_value_row("percent", "Fill Level")
        self._add_value_row("psi", "Pressure")
        self._add_health_banner()
        self._content_layout.addStretch()

    def _refresh_values(self) -> None:
        data = get_propane_status(self._tank_number)
        if self._gauge:
            self._gauge.set_value(data["percent_full"])
        self._value_labels["percent"].setText(f"{data['percent_full']:.1f} %")
        self._value_labels["psi"].setText(f"{data['psi']:.1f} PSI")
        self._set_health(data["healthy"])
