"""
Reusable widget helpers for the RV Monitor UI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen, QBrush, QFont
from PySide6.QtWidgets import QWidget


class BarGauge(QWidget):
    """
    A simple vertical bar gauge that fills from the bottom.

    Args:
        capacity: maximum value (100 % full)
        value:    current value
        fill_color: colour of the filled portion
        warn_threshold: if *value / capacity* exceeds this ratio and
                        *warn_high* is True (or falls below it when False),
                        the bar turns amber/red.
        warn_high: True → warn when bar is high (waste tanks),
                   False → warn when bar is low (supply tanks).
    """

    def __init__(
        self,
        capacity: float,
        value: float,
        fill_color: QColor = QColor("#4fc3f7"),
        warn_threshold: float = 0.20,
        warn_high: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._capacity = max(capacity, 1.0)
        self._value = max(0.0, min(value, capacity))
        self._fill_color = fill_color
        self._warn_threshold = warn_threshold
        self._warn_high = warn_high
        self.setMinimumSize(30, 80)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(value, self._capacity))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        border = 3
        inner_h = h - 2 * border
        inner_w = w - 2 * border

        ratio = self._value / self._capacity

        # Determine fill colour based on warning threshold
        if self._warn_high and ratio >= self._warn_threshold:
            color = QColor("#ef5350")  # red
        elif not self._warn_high and ratio <= self._warn_threshold:
            color = QColor("#ffa726")  # amber
        else:
            color = self._fill_color

        fill_h = int(inner_h * ratio)

        # Background
        painter.setBrush(QBrush(QColor("#1f2937")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        # Filled portion (from the bottom) with rounded top cap
        if fill_h > 0:
            top = border + (inner_h - fill_h)
            radius = 4
            path = QPainterPath()
            path.moveTo(border, top + radius)
            path.arcTo(border, top, radius * 2, radius * 2, 180, -90)
            path.lineTo(border + inner_w - radius, top)
            path.arcTo(border + inner_w - radius * 2, top, radius * 2, radius * 2, 90, -90)
            path.lineTo(border + inner_w, border + inner_h)
            path.lineTo(border, border + inner_h)
            path.closeSubpath()
            painter.setBrush(QBrush(color))
            painter.drawPath(path)

        # Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#1f2937"), border))
        painter.drawRoundedRect(border // 2, border // 2, w - border, h - border, 6, 6)

        painter.end()


class CircleGauge(QWidget):
    """
    A simple arc / donut gauge.
    """

    def __init__(
        self,
        capacity: float,
        value: float,
        fill_color: QColor = QColor("#4fc3f7"),
        warn_threshold: float = 0.20,
        warn_high: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._capacity = max(capacity, 1.0)
        self._value = max(0.0, min(value, capacity))
        self._fill_color = fill_color
        self._warn_threshold = warn_threshold
        self._warn_high = warn_high
        self.setMinimumSize(80, 80)

    def set_value(self, value: float) -> None:
        self._value = max(0.0, min(value, self._capacity))
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        w, h = self.width(), self.height()
        size = min(w, h) - 10
        x = (w - size) // 2
        y = (h - size) // 2
        pen_width = max(8, size // 8)

        ratio = self._value / self._capacity

        if self._warn_high and ratio >= self._warn_threshold:
            color = QColor("#ef5350")
        elif not self._warn_high and ratio <= self._warn_threshold:
            color = QColor("#ffa726")
        else:
            color = self._fill_color

        # Background track
        pen = QPen(QColor("#1f2937"), pen_width)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawArc(x, y, size, size, 0, 360 * 16)

        # Filled arc (clockwise from 12 o'clock)
        if ratio > 0:
            pen.setColor(color)
            painter.setPen(pen)
            span = int(ratio * 360 * 16)
            painter.drawArc(x, y, size, size, 90 * 16, -span)

        # Percentage label
        font = QFont("Sans Serif", max(10, size // 6), QFont.Bold)
        painter.setFont(font)
        painter.setPen(QPen(QColor("#eceff1")))
        painter.drawText(x, y, size, size, Qt.AlignCenter, f"{int(ratio * 100)}%")

        painter.end()


class TileIcon(QWidget):
    """
    Small decorative icon drawn with QPainter to identify each system tile.

    Icon types
    ----------
    WATER_DROP   – teardrop shape; use for fresh-water tiles.
    WASTE_TANK   – vertical cylinder; use for grey/black waste tanks.
    BATTERY      – rectangle body with top nub; use for battery tiles.
    PROPANE_TANK – upright rounded cylinder with valve; use for propane tiles.
    """

    WATER_DROP = "water_drop"
    WASTE_TANK = "waste_tank"
    BATTERY = "battery"
    PROPANE_TANK = "propane_tank"

    def __init__(
        self,
        icon_type: str,
        color: QColor,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_type = icon_type
        self._color = color
        self.setFixedSize(22, 22)

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        draw_fn = getattr(self, f"_draw_{self._icon_type}", None)
        if draw_fn is not None:
            draw_fn(painter)
        painter.end()

    # ------------------------------------------------------------------
    # Individual icon painters
    # ------------------------------------------------------------------

    def _draw_water_drop(self, painter: QPainter) -> None:
        """Classic teardrop: point at top, round bulge at bottom."""
        w, h = self.width(), self.height()
        cx = w / 2
        path = QPainterPath()
        path.moveTo(cx, 1)
        path.cubicTo(cx + w * 0.45, h * 0.35, cx + w * 0.45, h * 0.65, cx, h - 1)
        path.cubicTo(cx - w * 0.45, h * 0.65, cx - w * 0.45, h * 0.35, cx, 1)
        painter.setBrush(QBrush(self._color))
        painter.setPen(Qt.NoPen)
        painter.drawPath(path)

    def _draw_waste_tank(self, painter: QPainter) -> None:
        """Vertical cylinder silhouette representing a waste tank."""
        w, h = self.width(), self.height()
        px = int(w * 0.15)
        eh = int(h * 0.22)
        body_top = eh // 2
        body_h = h - eh

        painter.setPen(Qt.NoPen)

        # Cylinder body
        painter.setBrush(QBrush(self._color))
        painter.drawRect(px, body_top, w - 2 * px, body_h)

        # Top ellipse
        painter.setBrush(QBrush(self._color.lighter(130)))
        painter.drawEllipse(px, 0, w - 2 * px, eh)

        # Bottom ellipse (slightly darker to give depth)
        painter.setBrush(QBrush(self._color.darker(130)))
        painter.drawEllipse(px, h - eh, w - 2 * px, eh)

    def _draw_battery(self, painter: QPainter) -> None:
        """Rectangle body with a small top nub; internal cell dividers."""
        w, h = self.width(), self.height()
        nub_w = max(4, w // 3)
        nub_h = max(2, int(h * 0.12))
        body_top = nub_h + 1
        body_h = h - body_top - 1

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color))

        # Nub (top, centered)
        painter.drawRoundedRect((w - nub_w) // 2, 1, nub_w, nub_h, 2, 2)

        # Body
        painter.drawRoundedRect(1, body_top, w - 2, body_h, 3, 3)

        # Cell dividers drawn over the body in the background colour
        painter.setPen(QPen(QColor("#0d1b2a"), 1))
        third = body_h // 3
        for i in (1, 2):
            y = body_top + third * i
            painter.drawLine(2, y, w - 2, y)

    def _draw_propane_tank(self, painter: QPainter) -> None:
        """Upright rounded cylinder with a valve nub at the top."""
        w, h = self.width(), self.height()
        px = int(w * 0.18)
        valve_h = max(2, int(h * 0.14))
        valve_w = max(3, int(w * 0.22))
        tank_top = valve_h + 1
        tank_h = h - tank_top - 1
        tank_x = px
        tank_w = w - 2 * px

        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(self._color))

        # Valve nub at top center
        painter.drawRoundedRect((w - valve_w) // 2, 0, valve_w, valve_h + 2, 2, 2)

        # Tank body – tall rounded rectangle
        painter.drawRoundedRect(tank_x, tank_top, tank_w, tank_h, tank_w // 2, tank_w // 2)

        # Subtle highlight stripe
        highlight = self._color.lighter(150)
        highlight.setAlpha(80)
        painter.setBrush(QBrush(highlight))
        stripe_w = max(2, tank_w // 4)
        painter.drawRoundedRect(
            tank_x + (tank_w - stripe_w) // 2,
            tank_top + 3,
            stripe_w,
            tank_h - 6,
            stripe_w // 2,
            stripe_w // 2,
        )
