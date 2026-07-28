"""
Reusable widget helpers for the RV Monitor UI.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPainter, QPen, QBrush, QFont
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
        painter.setBrush(QBrush(QColor("#1e2a38")))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(0, 0, w, h, 6, 6)

        # Filled portion (from the bottom)
        if fill_h > 0:
            painter.setBrush(QBrush(color))
            painter.drawRect(border, border + (inner_h - fill_h), inner_w, fill_h)

        # Border
        painter.setBrush(Qt.NoBrush)
        painter.setPen(QPen(QColor("#546e7a"), border))
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
        pen = QPen(QColor("#1e2a38"), pen_width)
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
