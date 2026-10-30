"""Floating HUD Banner for "Watch Me & Automate" No-Code Voice Macro Recording.

Appears at top-center of the screen during active macro recording. Displays:
- Pulsing SVG recording indicator
- Live action counter (clicks, typing, shortcuts)
- Target application badge
- One-click Save and Discard buttons
"""

from __future__ import annotations

import logging
from typing import Optional

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
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from handless.actions.macro_recorder import MacroRecorder
from handless.ui.icons import (
    SVG_CHECK,
    SVG_CLOSE,
    SVG_RECORD_DOT,
    SVG_STOP,
    render_svg_icon,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)


class MacroRecordingBanner(QWidget):
    """Floating luxury HUD pill displayed while Handless records user actions."""

    save_requested = Signal(str)      # workflow name (can be empty string for auto-name)
    discard_requested = Signal()

    def __init__(
        self,
        macro_recorder: Optional[MacroRecorder] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.macro_recorder = macro_recorder

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._pulse_alpha = 255
        self._pulse_direction = -1
        self._anim: Optional[QPropertyAnimation] = None

        self._init_ui()
        self._setup_pulse_timer()

        if self.macro_recorder:
            self.macro_recorder.recording_started.connect(self.show_animated)
            self.macro_recorder.recording_stopped.connect(self.hide_animated)
            self.macro_recorder.action_count_changed.connect(self.update_action_count)

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 8, 10, 8)

        # 1. Main Capsule Frame
        self.card = QWidget(self)
        self.card.setObjectName("macroBannerCard")
        self.card.setStyleSheet("""
            QWidget#macroBannerCard {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 20px;
            }
        """)

        # Drop shadow
        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(24)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 90))
        self.card.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.card)
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # Pulsing Red Record Dot
        self.dot_lbl = QLabel(self.card)
        self.dot_lbl.setPixmap(render_svg_pixmap(SVG_RECORD_DOT, 18, 18, color="#EF4444"))
        self.dot_lbl.setFixedSize(18, 18)
        layout.addWidget(self.dot_lbl)

        # Labels Column
        label_col = QVBoxLayout()
        label_col.setContentsMargins(0, 0, 0, 0)
        label_col.setSpacing(1)

        self.title_lbl = QLabel("Watch Me & Automate", self.card)
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 12.5px; font-family: 'Segoe UI', sans-serif;")
        label_col.addWidget(self.title_lbl)

        self.status_lbl = QLabel("0 actions recorded — perform actions now", self.card)
        self.status_lbl.setStyleSheet("color: #A1A1AA; font-size: 11px; font-family: 'Segoe UI', sans-serif;")
        label_col.addWidget(self.status_lbl)

        layout.addLayout(label_col)

        # Separator
        sep = QWidget(self.card)
        sep.setFixedSize(1, 24)
        sep.setStyleSheet("background-color: #27272A;")
        layout.addWidget(sep)

        # Save Button
        self.save_btn = QPushButton(self.card)
        self.save_btn.setObjectName("macroSaveBtn")
        self.save_btn.setIcon(render_svg_icon(SVG_CHECK, 14, color="#FFFFFF"))
        self.save_btn.setText("Save")
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.save_btn.setFixedHeight(28)
        self.save_btn.setStyleSheet("""
            QPushButton#macroSaveBtn {
                background-color: #10B981;
                color: #FFFFFF;
                font-weight: 600;
                font-size: 11.5px;
                border: none;
                border-radius: 14px;
                padding: 0 12px;
            }
            QPushButton#macroSaveBtn:hover {
                background-color: #059669;
            }
        """)
        self.save_btn.clicked.connect(self._on_save_clicked)
        layout.addWidget(self.save_btn)

        # Discard Button
        self.discard_btn = QPushButton(self.card)
        self.discard_btn.setObjectName("macroDiscardBtn")
        self.discard_btn.setIcon(render_svg_icon(SVG_CLOSE, 14, color="#D4D4D8", hover_color="#FFFFFF"))
        self.discard_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.discard_btn.setFixedSize(28, 28)
        self.discard_btn.setToolTip("Discard recording (Esc)")
        self.discard_btn.setStyleSheet("""
            QPushButton#macroDiscardBtn {
                background-color: #27272A;
                border: 1px solid #3F3F46;
                border-radius: 14px;
            }
            QPushButton#macroDiscardBtn:hover {
                background-color: #3F3F46;
            }
        """)
        self.discard_btn.clicked.connect(self._on_discard_clicked)
        layout.addWidget(self.discard_btn)

        outer.addWidget(self.card)
        self.resize(380, 56)

    def _setup_pulse_timer(self) -> None:
        self._pulse_timer = QTimer(self)
        self._pulse_timer.timeout.connect(self._pulse_tick)
        self._pulse_timer.start(50)

    def _pulse_tick(self) -> None:
        self._pulse_alpha += self._pulse_direction * 10
        if self._pulse_alpha <= 70:
            self._pulse_alpha = 70
            self._pulse_direction = 1
        elif self._pulse_alpha >= 255:
            self._pulse_alpha = 255
            self._pulse_direction = -1

        # Adjust dot opacity
        self.dot_lbl.setStyleSheet(f"opacity: {self._pulse_alpha / 255.0:.2f};")

    def update_action_count(self, count: int) -> None:
        """Update live actions counter label."""
        if count == 1:
            self.status_lbl.setText("1 action recorded — keep going or say 'Call this...'")
        else:
            self.status_lbl.setText(f"{count} actions recorded — perform actions or save")

    def _on_save_clicked(self) -> None:
        """Handle save button click."""
        self.save_requested.emit("")
        if self.macro_recorder:
            wf = self.macro_recorder.save_macro()
            logger.info("Macro saved via HUD banner: %s", wf.name)
        self.hide_animated()

    def _on_discard_clicked(self) -> None:
        """Handle discard button click."""
        self.discard_requested.emit()
        if self.macro_recorder:
            self.macro_recorder.discard_recording()
        self.hide_animated()

    def show_animated(self) -> None:
        """Slide down gracefully from the top center of the screen."""
        screen = QApplication.primaryScreen()
        if not screen:
            self.show()
            return

        avail = screen.availableGeometry()
        w = max(420, self.sizeHint().width())
        h = 56
        x = avail.x() + (avail.width() - w) // 2
        target_y = avail.y() + 16
        start_y = avail.y() - h - 20

        self.setGeometry(x, start_y, w, h)
        self.show()
        self.raise_()

        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(240)
        self._anim.setStartValue(QPoint(x, start_y))
        self._anim.setEndValue(QPoint(x, target_y))
        self._anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._anim.start()

    def hide_animated(self) -> None:
        """Slide up out of screen."""
        if not self.isVisible():
            return

        screen = self.screen() or QApplication.primaryScreen()
        avail = screen.availableGeometry() if screen else QRect(0, 0, 1920, 1080)
        cur_x = self.x()
        cur_y = self.y()
        end_y = avail.y() - self.height() - 20

        if self._anim and self._anim.state() == QPropertyAnimation.State.Running:
            self._anim.stop()

        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(200)
        self._anim.setStartValue(QPoint(cur_x, cur_y))
        self._anim.setEndValue(QPoint(cur_x, end_y))
        self._anim.setEasingCurve(QEasingCurve.Type.InCubic)
        self._anim.finished.connect(self.hide)
        self._anim.start()

    def keyPressEvent(self, event) -> None:
        """Dismiss on Esc key."""
        if event.key() == Qt.Key.Key_Escape:
            self._on_discard_clicked()
            event.accept()
        else:
            super().keyPressEvent(event)

