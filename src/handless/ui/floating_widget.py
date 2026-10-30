"""Floating Action Widget for Vyoma Handless.

Provides a compact, sleek floating square tile that docks on screen with the
Vyoma glowing gradient orb logo. Clicking it smoothly expands and slides open the
copilot sidebar; closing the sidebar smoothly shrinks it back into this floating tile.
Supports mouse dragging, edge snapping, pulsing hover animations, and right-click menus.
"""

from __future__ import annotations

import logging
import math
from typing import Any, Callable, Optional

from PySide6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QRect,
    QSize,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QCursor, QMouseEvent, QPainter, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QMenu,
    QVBoxLayout,
    QWidget,
)

from handless.ui.icons import (
    SVG_CLOSE,
    SVG_GRID_9,
    SVG_PEN,
    SVG_SEARCH,
    SVG_SETTINGS,
    get_bot_logo_pixmap,
    render_svg_icon,
)
from handless.ui.sidebar import GradientOrbWidget

logger = logging.getLogger(__name__)


class FloatingBotLogoWidget(QWidget):
    """Animated Handless bot character with sinusoidal breathing & glowing aura."""

    def __init__(self, parent: Optional[QWidget] = None, size: int = 40) -> None:
        super().__init__(parent)
        self._size = size
        self.setFixedSize(size, size)
        self._phase = 0.0
        self._is_active = False
        self._pixmap = get_bot_logo_pixmap(without_bg=True, size=int(size * 0.95))

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

    def showEvent(self, event: Any) -> None:
        super().showEvent(event)
        if not self._timer.isActive():
            self._timer.start(33)

    def hideEvent(self, event: Any) -> None:
        super().hideEvent(event)
        if self._timer.isActive():
            self._timer.stop()

    def set_active(self, active: bool) -> None:
        self._is_active = active
        self.update()

    def _on_tick(self) -> None:
        step = 0.06 if self._is_active else 0.035
        self._phase = (self._phase + step) % (2 * math.pi)
        self.update()

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setClipRect(self.rect())

        w = self.width()
        h = self.height()
        cx = w / 2.0
        cy = h / 2.0

        # Gentle floating offset
        float_y = math.sin(self._phase) * (2.2 if self._is_active else 1.2)

        # Soft ambient aura glow behind the bot character
        aura_r = (min(w, h) / 2.0) - 1.0 + (math.sin(self._phase * 1.5) * 1.5)
        grad = QRadialGradient(cx, cy + float_y, aura_r)
        if self._is_active:
            grad.setColorAt(0.0, QColor(56, 189, 248, 140))
            grad.setColorAt(0.6, QColor(139, 92, 246, 80))
            grad.setColorAt(1.0, QColor(139, 92, 246, 0))
        else:
            grad.setColorAt(0.0, QColor(56, 189, 248, 70))
            grad.setColorAt(0.7, QColor(139, 92, 246, 35))
            grad.setColorAt(1.0, QColor(139, 92, 246, 0))

        painter.setBrush(grad)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPoint(int(cx), int(cy + float_y)), int(aura_r), int(aura_r))

        # Render bot logo
        if not self._pixmap.isNull():
            pw = self._pixmap.width()
            ph = self._pixmap.height()
            px = int(cx - (pw / 2.0))
            py = int(cy - (ph / 2.0) + float_y)
            painter.drawPixmap(px, py, self._pixmap)
        else:
            painter.setBrush(QColor(56, 189, 248))
            painter.drawEllipse(int(cx - 12), int(cy - 12 + float_y), 24, 24)


class FloatingCopilotWidget(QWidget):
    """Compact floating square tile with official Handless bot logo and smooth animations."""

    clicked = Signal()

    def __init__(
        self,
        on_open_sidebar: Optional[Callable[[], None]] = None,
        on_open_inspector: Optional[Callable[[], None]] = None,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_toggle_dictation: Optional[Callable[[], None]] = None,
        on_exit_app: Optional[Callable[[], None]] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.on_open_sidebar = on_open_sidebar
        self.on_open_inspector = on_open_inspector
        self.on_open_settings = on_open_settings
        self.on_toggle_dictation = on_toggle_dictation
        self.on_exit_app = on_exit_app

        self._drag_start_pos: Optional[QPoint] = None
        self._is_dragging = False
        self._hovered = False
        self._dock_side = "right"

        self._init_window()
        self._init_ui()
        self._init_animations()

    def set_dock_side(self, side: str) -> None:
        """Position floating widget along the corresponding edge."""
        self._dock_side = side
        screen = QApplication.screenAt(QCursor.pos()) or QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            if side == "left":
                self.move(avail.x() + 20, avail.y() + 100)
            else:
                self.move(avail.x() + avail.width() - 76, avail.y() + 100)

    def _init_window(self) -> None:
        self.setWindowTitle("Vyoma Floating Copilot")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setFixedSize(58, 58)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setToolTip("Vyoma Handless (Click to open, drag to move)")

        # Position docked at top-right edge by default
        screen = QApplication.primaryScreen()
        if screen:
            avail = screen.availableGeometry()
            self.move(avail.x() + avail.width() - 76, avail.y() + 100)
        else:
            self.move(100, 100)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Center animated Handless Bot Logo
        self.bot_logo = FloatingBotLogoWidget(self, size=40)
        self.orb = self.bot_logo  # Backwards compatibility alias
        layout.addWidget(self.bot_logo)

    def _init_animations(self) -> None:
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(220)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

    # -----------------------------------------------------------------------
    # Show / Hide with Smooth Slide & Fade
    # -----------------------------------------------------------------------

    def show_animated(self) -> None:
        """Fade in and pop the floating widget into view."""
        self.set_dock_side(self._dock_side)
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self.activateWindow()

        self._fade_anim.stop()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def hide_animated(self, on_finish: Optional[Callable[[], None]] = None) -> None:
        """Smoothly fade out and hide."""
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)

        def _done():
            self.hide()
            try:
                self._fade_anim.finished.disconnect()
            except Exception:
                pass
            if on_finish:
                on_finish()

        self._fade_anim.finished.connect(_done)
        self._fade_anim.start()

    # -----------------------------------------------------------------------
    # Painting & Aesthetics
    # -----------------------------------------------------------------------

    def paintEvent(self, event: Any) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setClipRect(self.rect())

        rect = self.rect().adjusted(2, 2, -2, -2)

        # Acrylic dark background with subtle border
        bg_color = QColor(15, 23, 42, 230) if not self._hovered else QColor(30, 41, 59, 245)
        border_color = QColor(56, 189, 248, 160) if self._hovered else QColor(51, 65, 85, 180)
        border_width = 1.8 if self._hovered else 1.2

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, border_width))
        painter.drawRoundedRect(rect, 16, 16)

        painter.end()

    def enterEvent(self, event: Any) -> None:
        self._hovered = True
        self.orb.set_active(True)
        self.update()
        super().enterEvent(event)

    def leaveEvent(self, event: Any) -> None:
        self._hovered = False
        self.orb.set_active(False)
        self.update()
        super().leaveEvent(event)

    # -----------------------------------------------------------------------
    # Mouse Dragging & Click Handling
    # -----------------------------------------------------------------------

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_start_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            self._is_dragging = False
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu(event.globalPosition().toPoint())
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if event.buttons() & Qt.MouseButton.LeftButton and self._drag_start_pos is not None:
            new_pos = event.globalPosition().toPoint() - self._drag_start_pos
            # Threshold to distinguish click from drag
            if not self._is_dragging:
                delta = (event.globalPosition().toPoint() - (self.frameGeometry().topLeft() + self._drag_start_pos)).manhattanLength()
                if delta > 4:
                    self._is_dragging = True
            self.move(new_pos)
            event.accept()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            if not self._is_dragging:
                # User clicked on the floating widget
                self._handle_click()
            else:
                self._snap_to_nearest_edge()
            self._drag_start_pos = None
            self._is_dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)

    def _handle_click(self) -> None:
        """Trigger sidebar expansion."""
        self.clicked.emit()
        if self.on_open_sidebar:
            self.on_open_sidebar()

    def _snap_to_nearest_edge(self) -> None:
        """Snap floating widget gracefully to left or right screen border if close."""
        screen = QApplication.primaryScreen()
        if not screen:
            return
        avail = screen.availableGeometry()
        curr_x = self.x()
        curr_y = max(avail.y() + 20, min(self.y(), avail.y() + avail.height() - self.height() - 20))

        dist_left = abs(curr_x - avail.x())
        dist_right = abs((avail.x() + avail.width()) - (curr_x + self.width()))

        # If within 80px of left or right margin, snap to edge
        target_x = curr_x
        if dist_right < 90:
            target_x = avail.x() + avail.width() - self.width() - 14
        elif dist_left < 90:
            target_x = avail.x() + 14

        self.move(target_x, curr_y)

    # -----------------------------------------------------------------------
    # Context Menu
    # -----------------------------------------------------------------------

    def _show_context_menu(self, global_pos: QPoint) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1, stop:0 #1E293B, stop:1 #0F172A);
                border: 1px solid #334155;
                border-radius: 8px;
                padding: 6px;
                color: #F8FAFC;
                font-size: 12px;
                font-family: 'Segoe UI', -apple-system, sans-serif;
            }
            QMenu::item {
                padding: 6px 14px;
                border-radius: 5px;
            }
            QMenu::item:selected {
                background: #0284C7;
                color: #FFFFFF;
            }
            QMenu::separator {
                height: 1px;
                background: #334155;
                margin: 4px 6px;
            }
        """)

        act_open = menu.addAction("Open Vyoma Copilot", self._handle_click)
        act_open.setIcon(render_svg_icon(SVG_GRID_9, 14, color="#38BDF8"))

        if self.on_open_inspector:
            act_inspect = menu.addAction("Desktop Element Inspector", self.on_open_inspector)
            act_inspect.setIcon(render_svg_icon(SVG_SEARCH, 14, color="#0284C7"))

        if self.on_toggle_dictation:
            act_dict = menu.addAction("Toggle Dictation Mode", self.on_toggle_dictation)
            act_dict.setIcon(render_svg_icon(SVG_PEN, 14, color="#10B981"))

        if self.on_open_settings:
            act_sett = menu.addAction("Settings", self.on_open_settings)
            act_sett.setIcon(render_svg_icon(SVG_SETTINGS, 14, color="#94A3B8"))

        menu.addSeparator()

        if self.on_exit_app:
            act_exit = menu.addAction("Exit Application", self.on_exit_app)
            act_exit.setIcon(render_svg_icon(SVG_CLOSE, 14, color="#EF4444"))

        menu.exec(global_pos)

