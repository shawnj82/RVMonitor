"""
Navigation manager for the RV Monitor UI.

Provides a simple stack-based navigation system so that screens can push and
pop themselves without knowing about each other.
"""

from __future__ import annotations

from typing import Optional

from PySide6.QtWidgets import QStackedWidget, QWidget


class Navigator:
    """
    Thin wrapper around QStackedWidget that implements push/pop navigation.

    Usage::

        nav = Navigator(stacked_widget)
        nav.push(my_screen)   # show my_screen on top
        nav.pop()             # return to previous screen
    """

    def __init__(self, stack: QStackedWidget) -> None:
        self._stack = stack
        self._history: list[QWidget] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def push(self, screen: QWidget) -> None:
        """Show *screen*, keeping the current screen in history."""
        current = self._stack.currentWidget()
        if current is not None:
            self._history.append(current)

        if self._stack.indexOf(screen) == -1:
            self._stack.addWidget(screen)

        self._stack.setCurrentWidget(screen)

    def pop(self) -> Optional[QWidget]:
        """Return to the previous screen.  Returns the screen that was popped."""
        if not self._history:
            return None

        previous = self._history.pop()
        self._stack.setCurrentWidget(previous)
        return self._stack.currentWidget()

    def replace(self, screen: QWidget) -> None:
        """Replace the current screen without adding an entry to history."""
        if self._stack.indexOf(screen) == -1:
            self._stack.addWidget(screen)
        self._stack.setCurrentWidget(screen)

    @property
    def can_go_back(self) -> bool:
        return len(self._history) > 0
