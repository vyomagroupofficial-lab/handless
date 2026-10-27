"""System Tray Integration for Vyoma Handless.

Keeps the application alive in the Windows notification area with a context menu
for quick access to the Voice Bar, Settings, Emergency Stop, and Safe Exit.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon

from handless.safety.emergency_stop import emergency_stop

logger = logging.getLogger(__name__)


def create_tray_icon_pixmap() -> QIcon:
    """Generate a clean cream/terracotta vector-style tray icon dynamically."""
    pixmap = QPixmap(32, 32)
    pixmap.fill(QColor(0, 0, 0, 0))

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer circle in terracotta
    painter.setBrush(QColor(196, 112, 75))  # #C4704B
    painter.setPen(QColor(232, 223, 208))  # #E8DFD0
    painter.drawEllipse(2, 2, 28, 28)

    # Inner microphone capsule in cream
    painter.setBrush(QColor(253, 246, 236))  # #FDF6EC
    painter.setPen(QColor(44, 36, 24))
    painter.drawRoundedRect(11, 7, 10, 14, 5, 5)

    # Base arc and stand
    painter.drawLine(8, 16, 8, 19)
    painter.drawLine(24, 16, 24, 19)
    painter.drawLine(8, 19, 24, 19)
    painter.drawLine(16, 20, 16, 25)
    painter.drawLine(12, 25, 20, 25)

    painter.end()
    return QIcon(pixmap)


class HandlessTrayIcon(QSystemTrayIcon):
    """System Tray icon with context menu."""

    def __init__(
        self,
        on_toggle_bar: Optional[Callable[[], None]] = None,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.on_toggle_bar = on_toggle_bar
        self.on_open_settings = on_open_settings
        self.on_exit = on_exit

        self.setIcon(create_tray_icon_pixmap())
        self.setToolTip("Vyoma Handless — Voice Controlled PC")

        # Build Context Menu
        self.menu = QMenu()

        self.toggle_action = QAction("Show / Hide Voice Bar", self.menu)
        if self.on_toggle_bar:
            self.toggle_action.triggered.connect(self.on_toggle_bar)
        self.menu.addAction(self.toggle_action)

        self.settings_action = QAction("Settings...", self.menu)
        if self.on_open_settings:
            self.settings_action.triggered.connect(self.on_open_settings)
        self.menu.addAction(self.settings_action)

        self.stop_action = QAction("⛔ Emergency Stop", self.menu)
        self.stop_action.triggered.connect(lambda: emergency_stop.trigger(reason="Tray Menu"))
        self.menu.addAction(self.stop_action)

        self.menu.addSeparator()

        self.exit_action = QAction("Exit Handless", self.menu)
        if self.on_exit:
            self.exit_action.triggered.connect(self.on_exit)
        else:
            self.exit_action.triggered.connect(QApplication.quit)
        self.menu.addAction(self.exit_action)

        self.setContextMenu(self.menu)
        self.activated.connect(self._handle_activated)

    def _handle_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            if self.on_toggle_bar:
                self.on_toggle_bar()
