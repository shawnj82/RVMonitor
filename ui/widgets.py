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
    Large icon gauge drawn with QPainter for each system tile.

    Icon types
    ----------
    WATER_DROP   – wide-bottom droplet; use for fresh-water tiles.
    WASTE_TANK   – vertical cylinder; use for grey/black waste tanks.
    BATTERY      – car-battery silhouette with two terminals.
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
        *,
        size: int = 22,
        level_percent: float = 0.0,
        show_percent: bool = False,
        warn_threshold: float | None = None,
        warn_high: bool = False,
        show_trend: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._icon_type = icon_type
        self._color = color
        self._level_percent = max(0.0, min(level_percent, 100.0))
        self._show_percent = show_percent
        self._warn_threshold = warn_threshold
        self._warn_high = warn_high
        self._show_trend = show_trend
        self._trend = 0
        self.setFixedSize(size, size)

    def set_level(self, level_percent: float) -> None:
        self._level_percent = max(0.0, min(level_percent, 100.0))
        self.update()

    def set_value(self, value: float, capacity: float = 100.0) -> None:
        if capacity <= 0:
            self.set_level(0.0)
            return
        self.set_level((value / capacity) * 100.0)

    def set_trend(self, direction: int) -> None:
        self._trend = 1 if direction > 0 else -1 if direction < 0 else 0
        self.update()

    def _fill_color(self) -> QColor:
        ratio = self._level_percent / 100.0
        if self._warn_threshold is None:
            return self._color
        if self._warn_high and ratio >= self._warn_threshold:
            return QColor("#ef5350")
        if not self._warn_high and ratio <= self._warn_threshold:
            return QColor("#ffa726")
        return self._color

    def _icon_rect(self):
        margin = 6.0
        right_margin = 16.0 if self._show_trend else 6.0
        return (
            margin,
            margin,
            max(12.0, self.width() - margin - right_margin),
            max(12.0, self.height() - margin * 2),
        )

    def _icon_path(self) -> QPainterPath:
        draw_fn = getattr(self, f"_path_{self._icon_type}", None)
        if draw_fn is None:
            return QPainterPath()
        return draw_fn()

    def paintEvent(self, event) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        path = self._icon_path()

        if not path.isEmpty():
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(QColor("#1f2937")))
            painter.drawPath(path)

            ratio = self._level_percent / 100.0
            if ratio > 0:
                x, y, w, h = self._icon_rect()
                top = y + (1.0 - ratio) * h
                painter.save()
                painter.setClipPath(path)
                painter.setBrush(QBrush(self._fill_color()))
                painter.drawRect(x, top, w, (y + h) - top + 1)
                painter.restore()

            painter.setBrush(Qt.NoBrush)
            painter.setPen(QPen(QColor("#cbd5e1"), 2))
            painter.drawPath(path)

            if self._show_percent:
                text_pen = QPen(QColor("#f8fafc"))
                painter.setPen(text_pen)
                x, y, w, h = self._icon_rect()
                font = QFont("Inter", max(10, int(h * 0.18)), QFont.Bold)
                painter.setFont(font)
                painter.drawText(int(x), int(y), int(w), int(h), Qt.AlignCenter, f"{int(round(self._level_percent))}%")

        if self._show_trend and self._trend != 0:
            arrow_color = QColor("#22c55e") if self._trend > 0 else QColor("#f97316")
            painter.setPen(Qt.NoPen)
            painter.setBrush(QBrush(arrow_color))
            cx = self.width() - 8
            cy = self.height() // 2
            arrow = QPainterPath()
            if self._trend > 0:
                arrow.moveTo(cx, cy - 8)
                arrow.lineTo(cx - 5, cy + 2)
                arrow.lineTo(cx + 5, cy + 2)
            else:
                arrow.moveTo(cx, cy + 8)
                arrow.lineTo(cx - 5, cy - 2)
                arrow.lineTo(cx + 5, cy - 2)
            arrow.closeSubpath()
            painter.drawPath(arrow)

        painter.end()

    # ------------------------------------------------------------------
    # Individual icon paths
    # ------------------------------------------------------------------

    def _path_water_drop(self) -> QPainterPath:
        """Wide-bottom water droplet."""
        x, y, w, h = self._icon_rect()
        cx = x + (w / 2)
        path = QPainterPath()
        path.moveTo(cx, y + 1)
        path.cubicTo(cx + w * 0.50, y + h * 0.33, cx + w * 0.46, y + h * 0.84, cx, y + h - 1)
        path.cubicTo(cx - w * 0.46, y + h * 0.84, cx - w * 0.50, y + h * 0.33, cx, y + 1)
        return path

    def _path_waste_tank(self) -> QPainterPath:
        """Vertical cylinder silhouette representing a waste tank."""
        x, y, w, h = self._icon_rect()
        px = w * 0.16
        tank_x = x + px
        tank_w = w - (2 * px)
        top_y = y + h * 0.12
        bottom_y = y + h * 0.88
        path = QPainterPath()
        path.addRoundedRect(tank_x, top_y, tank_w, bottom_y - top_y, tank_w * 0.22, tank_w * 0.22)
        return path

    def _path_battery(self) -> QPainterPath:
        """Car battery with two top terminals."""
        x, y, w, h = self._icon_rect()
        body_top = y + h * 0.28
        body_h = h * 0.66
        body_x = x + 1
        body_w = w - 2
        term_w = max(4.0, body_w * 0.16)
        term_h = max(4.0, h * 0.13)
        left_term_x = body_x + body_w * 0.22 - (term_w / 2)
        right_term_x = body_x + body_w * 0.78 - (term_w / 2)

        path = QPainterPath()
        path.addRoundedRect(body_x, body_top, body_w, body_h, 6, 6)
        path.addRoundedRect(left_term_x, y + 2, term_w, term_h, 2, 2)
        path.addRoundedRect(right_term_x, y + 2, term_w, term_h, 2, 2)
        return path

    def _path_propane_tank(self) -> QPainterPath:
        """Upright rounded cylinder with a valve nub at the top."""
        x, y, w, h = self._icon_rect()
        px = w * 0.2
        valve_h = max(4.0, h * 0.12)
        valve_w = max(6.0, w * 0.24)
        tank_top = y + valve_h + 2
        tank_h = h - valve_h - 4
        tank_x = x + px
        tank_w = w - (2 * px)
        path = QPainterPath()
        path.addRoundedRect((x + w / 2) - (valve_w / 2), y + 1, valve_w, valve_h, 2, 2)
        path.addRoundedRect(tank_x, tank_top, tank_w, tank_h, tank_w / 2, tank_w / 2)
        return path
