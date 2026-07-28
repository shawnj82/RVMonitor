"""
Load management UI for the RV Monitor.

Classes
-------
LoadPresetBar
    A compact bottom bar with four mutually-exclusive preset mode buttons:
    Storage | Boondock | Full Hookup | Custom.
    Tapping any named preset applies it immediately.
    Tapping Custom navigates to CustomLoadScreen.

CustomLoadScreen
    Full-screen list letting the user toggle each individual load on or off.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from logic.load_controller import LOAD_LABELS, LOADS, controller

if TYPE_CHECKING:
    from ui.navigation import Navigator

# ── Preset names ─────────────────────────────────────────────────────────────

_PRESET_NAMES = ["Storage", "Boondock", "Full Hookup", "Manual"]

# ── Button style sheets ───────────────────────────────────────────────────────

_BTN_ACTIVE = (
    "QPushButton { background: #1565c0; color: #e3f2fd; border-radius: 8px; "
    "font-weight: bold; font-size: 13px; border: 2px solid #42a5f5; padding: 6px 4px; }"
    "QPushButton:pressed { background: #0d47a1; }"
)
_BTN_INACTIVE = (
    "QPushButton { background: #152030; color: #78909c; border-radius: 8px; "
    "font-size: 13px; border: 2px solid #263849; padding: 6px 4px; }"
    "QPushButton:pressed { background: #1a2a3d; color: #90a4ae; }"
)

_TOGGLE_ON = (
    "QPushButton { background: #2e7d32; color: #c8e6c9; border-radius: 8px; "
    "border: 2px solid #4caf50; }"
    "QPushButton:pressed { background: #1b5e20; }"
)
_TOGGLE_OFF = (
    "QPushButton { background: #263849; color: #546e7a; border-radius: 8px; "
    "border: 2px solid #37474f; }"
    "QPushButton:pressed { background: #1e2a38; }"
)


# ── LoadPresetBar ─────────────────────────────────────────────────────────────


class LoadPresetBar(QWidget):
    """
    Compact bottom bar with four mutually-exclusive preset mode buttons.

    Tapping **Storage**, **Boondock**, or **Full Hookup** applies that preset
    immediately.  Tapping **Custom** marks the mode as Custom and navigates to
    :class:`CustomLoadScreen` for individual load control.
    """

    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._custom_screen: CustomLoadScreen | None = None
        self._buttons: dict[str, QPushButton] = {}

        self.setFixedHeight(72)
        self.setStyleSheet("background: #0a1520; border-top: 1px solid #1e2a38;")

        self._build_ui()

        # Reflect mode changes from any source (including CustomLoadScreen)
        controller.mode_changed.connect(self._on_mode_changed)
        self._refresh_buttons(controller.get_active_mode())

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        for name in _PRESET_NAMES:
            btn = QPushButton(name)
            btn.setFont(QFont("Sans Serif", 12))
            btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, n=name: self._on_preset_clicked(n))
            layout.addWidget(btn)
            self._buttons[name] = btn

    def _on_preset_clicked(self, name: str) -> None:
        if name == "Manual":
            controller.enter_manual_mode()
            if self._custom_screen is None:
                self._custom_screen = CustomLoadScreen(self._navigator)
            self._navigator.push(self._custom_screen)
        else:
            controller.apply_preset(name)

    def _on_mode_changed(self, mode: str) -> None:
        self._refresh_buttons(mode)

    def _refresh_buttons(self, active_mode: str) -> None:
        for name, btn in self._buttons.items():
            btn.setStyleSheet(_BTN_ACTIVE if name == active_mode else _BTN_INACTIVE)


# ── CustomLoadScreen ──────────────────────────────────────────────────────────


class CustomLoadScreen(QWidget):
    """
    Full-screen list for toggling individual RV loads on or off.

    Toggling any load sets the active mode to ``"Custom"`` via the controller.
    The screen refreshes its toggle states every time it is shown so that it
    stays in sync when returning from the main dashboard.
    """

    def __init__(self, navigator: "Navigator", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._navigator = navigator
        self._toggle_btns: dict[str, QPushButton] = {}
        self._build_ui()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # Header
        header = QWidget()
        header.setFixedHeight(56)
        header.setStyleSheet("background: #0d1b2a;")
        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(8, 0, 16, 0)

        back_btn = QPushButton("‹ Back")
        back_btn.setFont(QFont("Sans Serif", 14))
        back_btn.setStyleSheet(
            "QPushButton { color: #4fc3f7; background: transparent; border: none; padding: 4px 8px; }"
            "QPushButton:pressed { color: #0288d1; }"
        )
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.clicked.connect(self._navigator.pop)
        h_layout.addWidget(back_btn)

        title_lbl = QLabel("Manual Loads")
        title_lbl.setFont(QFont("Sans Serif", 16, QFont.Bold))
        title_lbl.setStyleSheet("color: #eceff1;")
        title_lbl.setAlignment(Qt.AlignCenter)
        h_layout.addWidget(title_lbl, stretch=1)

        root.addWidget(header)

        # Divider
        divider = QFrame()
        divider.setFrameShape(QFrame.HLine)
        divider.setStyleSheet("color: #1e2a38;")
        root.addWidget(divider)

        # Content
        content_widget = QWidget()
        content_widget.setStyleSheet("background: #0d1b2a;")
        content = QVBoxLayout(content_widget)
        content.setContentsMargins(20, 16, 20, 16)
        content.setSpacing(0)

        subtitle = QLabel("Tap a button to toggle each load on or off.")
        subtitle.setFont(QFont("Sans Serif", 11))
        subtitle.setStyleSheet("color: #546e7a; padding-bottom: 10px;")
        subtitle.setWordWrap(True)
        content.addWidget(subtitle)

        for load in LOADS:
            row = QHBoxLayout()
            row.setContentsMargins(0, 10, 0, 10)
            row.setSpacing(10)

            label = QLabel(LOAD_LABELS[load])
            label.setFont(QFont("Sans Serif", 14))
            label.setStyleSheet("color: #eceff1;")
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
            row.addWidget(label)

            btn = QPushButton()
            btn.setFixedSize(80, 42)
            btn.setFont(QFont("Sans Serif", 12, QFont.Bold))
            btn.setCursor(Qt.PointingHandCursor)
            btn.clicked.connect(lambda checked, ld=load: self._on_toggle(ld))
            row.addWidget(btn)
            self._toggle_btns[load] = btn

            content.addLayout(row)

            sep = QFrame()
            sep.setFrameShape(QFrame.HLine)
            sep.setFixedHeight(1)
            sep.setStyleSheet("background: #1e2a38; border: none;")
            content.addWidget(sep)

        content.addStretch()
        root.addWidget(content_widget, stretch=1)

        self._refresh_toggles()

    def showEvent(self, event) -> None:  # noqa: N802
        """Re-sync toggle states whenever this screen becomes visible."""
        super().showEvent(event)
        self._refresh_toggles()

    # ------------------------------------------------------------------

    def _on_toggle(self, load: str) -> None:
        controller.toggle_load(load)
        self._refresh_toggles()

    def _refresh_toggles(self) -> None:
        states = controller.get_load_states()
        for load, btn in self._toggle_btns.items():
            if states.get(load, False):
                btn.setText("ON")
                btn.setStyleSheet(_TOGGLE_ON)
            else:
                btn.setText("OFF")
                btn.setStyleSheet(_TOGGLE_OFF)
