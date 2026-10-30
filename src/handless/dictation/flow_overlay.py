"""Wispr Flow Floating HUD Pill Overlay.

Provides a modern floating pill overlay inspired by Wispr Flow and OpenWhispr:
- Appears when user holds Ctrl+Shift to dictate.
- Live sound wave visualizations and instant transcription progress via Groq Whisper.
- Direct desktop Flow bar language switcher (100+ languages, auto-detection).
- 4-Tier Auto Cleanup level selector (None, Light, Medium, High).
- 1-Click Revert/Undo AI Edit button.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

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
from PySide6.QtGui import QColor, QCursor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMenu,
    QPushButton,
    QWidget,
)

from handless.dictation.cleanup_engine import CleanupLevel
from handless.dictation.language_manager import LanguageManager
from handless.ui.icons import SVG_CHECK, SVG_REFRESH, render_svg_icon

logger = logging.getLogger(__name__)


class WisprFlowOverlay(QWidget):
    """Floating acrylic pill HUD for hands-free hold-to-talk dictation."""

    language_changed = Signal(str)        # passes ISO code or 'auto'
    cleanup_level_changed = Signal(str)   # passes none, light, medium, high
    undo_requested = Signal()

    def __init__(
        self,
        language_manager: Optional[LanguageManager] = None,
        cleanup_level: CleanupLevel | str = CleanupLevel.MEDIUM,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.language_manager = language_manager or LanguageManager()
        self.cleanup_level = CleanupLevel(cleanup_level) if isinstance(cleanup_level, str) else cleanup_level

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)

        self._state = "idle"  # idle, listening, transcribing, done
        self._fade_anim = QPropertyAnimation(self, b"windowOpacity")
        self._fade_anim.setDuration(180)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)

        self._init_ui()
        self.hide()

    def _init_ui(self) -> None:
        from handless.ui.sidebar import GradientOrbWidget, SoundWaveVisualizer

        self.setFixedSize(380, 48)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(8)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # 1. Left Gradient Orb
        self.orb = GradientOrbWidget(self, size=22)
        layout.addWidget(self.orb)

        # 2. Central Status Label
        self.status_lbl = QLabel("Flow Dictating...", self)
        font = QFont("Segoe UI", 9, QFont.Weight.DemiBold)
        self.status_lbl.setFont(font)
        self.status_lbl.setStyleSheet("color: #F8FAFC; background: transparent;")
        layout.addWidget(self.status_lbl, stretch=1)

        # 3. Sound Wave Visualizer
        self.wave = SoundWaveVisualizer(self, bar_count=4)
        self.wave.setFixedSize(22, 18)
        layout.addWidget(self.wave)

        # 4. Language Selector Pill
        self.lang_btn = QPushButton(self)
        self.lang_btn.setObjectName("flowLangBtn")
        self.lang_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.lang_btn.setFixedHeight(24)
        self.lang_btn.setStyleSheet("""
            QPushButton#flowLangBtn {
                background-color: rgba(39, 39, 42, 0.9);
                color: #E4E4E7;
                font-size: 10.5px;
                font-weight: 600;
                border: 1px solid rgba(63, 63, 70, 0.8);
                border-radius: 12px;
                padding: 0 8px;
            }
            QPushButton#flowLangBtn:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
                border-color: #10B981;
            }
        """)
        self._update_lang_btn_text()
        self.lang_btn.clicked.connect(self._open_language_menu)
        layout.addWidget(self.lang_btn)

        # 5. Cleanup Tier Selector Pill
        self.cleanup_btn = QPushButton(self)
        self.cleanup_btn.setObjectName("flowCleanupBtn")
        self.cleanup_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.cleanup_btn.setFixedHeight(24)
        self.cleanup_btn.setStyleSheet("""
            QPushButton#flowCleanupBtn {
                background-color: rgba(39, 39, 42, 0.9);
                color: #A1A1AA;
                font-size: 10px;
                font-weight: 600;
                border: 1px solid rgba(63, 63, 70, 0.8);
                border-radius: 12px;
                padding: 0 8px;
            }
            QPushButton#flowCleanupBtn:hover {
                background-color: #3F3F46;
                color: #FFFFFF;
                border-color: #8B5CF6;
            }
        """)
        self._update_cleanup_btn_text()
        self.cleanup_btn.clicked.connect(self._open_cleanup_menu)
        layout.addWidget(self.cleanup_btn)

        # 6. Revert / Undo AI Edit Button (hidden by default)
        self.undo_btn = QPushButton(self)
        self.undo_btn.setObjectName("flowUndoBtn")
        self.undo_btn.setIcon(render_svg_icon(SVG_REFRESH, 11, color="#F59E0B", hover_color="#FBBF24"))
        self.undo_btn.setFixedSize(24, 24)
        self.undo_btn.setToolTip("Revert to Raw Dictation (Ctrl+Alt+Z)")
        self.undo_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.undo_btn.setStyleSheet("""
            QPushButton#flowUndoBtn {
                background-color: rgba(39, 39, 42, 0.9);
                border: 1px solid #78350F;
                border-radius: 12px;
            }
            QPushButton#flowUndoBtn:hover {
                background-color: #451A03;
            }
        """)
        self.undo_btn.clicked.connect(self.undo_requested.emit)
        self.undo_btn.hide()
        layout.addWidget(self.undo_btn)

    def _update_lang_btn_text(self) -> None:
        badge = self.language_manager.get_short_badge()
        self.lang_btn.setText(f"🌐 {badge} ▾")

    def _update_cleanup_btn_text(self) -> None:
        labels = {
            CleanupLevel.NONE: "Raw ▾",
            CleanupLevel.LIGHT: "Light ▾",
            CleanupLevel.MEDIUM: "Med ▾",
            CleanupLevel.HIGH: "Exec ▾",
        }
        self.cleanup_btn.setText(labels.get(self.cleanup_level, "Med ▾"))

    def _open_language_menu(self) -> None:
        """Show fast dropdown menu of pinned languages + all languages."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #18181B;
                color: #E4E4E7;
                border: 1px solid #27272A;
                border-radius: 10px;
                padding: 4px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 5px 18px 5px 10px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #27272A;
                color: #FFFFFF;
            }
        """)

        # Pinned languages
        pinned = self.language_manager.get_pinned_languages()
        cur_lang = self.language_manager.current_language

        for code, eng, nat in pinned:
            prefix = "✓ " if code == cur_lang else "   "
            act = menu.addAction(f"{prefix}{eng} ({nat})")
            act.triggered.connect(lambda _, c=code: self.set_language(c))

        menu.addSeparator()

        # More languages submenu
        more_menu = menu.addMenu("More Languages (100+)...")
        more_menu.setStyleSheet(menu.styleSheet())
        all_langs = self.language_manager.get_all_languages()
        for code, eng, nat in all_langs:
            prefix = "✓ " if code == cur_lang else "   "
            act = more_menu.addAction(f"{prefix}{eng} ({nat})")
            act.triggered.connect(lambda _, c=code: self.set_language(c))

        menu.exec(QCursor.pos())

    def _open_cleanup_menu(self) -> None:
        """Show dropdown to switch between the 4 Auto Cleanup levels."""
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #18181B;
                color: #E4E4E7;
                border: 1px solid #27272A;
                border-radius: 10px;
                padding: 4px;
                font-size: 11px;
            }
            QMenu::item {
                padding: 6px 18px 6px 10px;
                border-radius: 6px;
            }
            QMenu::item:selected {
                background-color: #27272A;
                color: #FFFFFF;
            }
        """)

        levels = [
            (CleanupLevel.NONE, "Level 0: None (Raw Verbatim)", "Zero AI alterations"),
            (CleanupLevel.LIGHT, "Level 1: Light", "Clean fillers, stutters, grammar"),
            (CleanupLevel.MEDIUM, "Level 2: Medium (Default)", "Improve flow, clarity, conciseness"),
            (CleanupLevel.HIGH, "Level 3: High (Executive)", "Cognitive rewrite for executive brevity"),
        ]

        for lvl, title, desc in levels:
            prefix = "✓ " if lvl == self.cleanup_level else "   "
            act = menu.addAction(f"{prefix}{title}")
            act.setToolTip(desc)
            act.triggered.connect(lambda _, l=lvl: self.set_cleanup_level(l))

        menu.exec(QCursor.pos())

    @property
    def lang_pill(self) -> QPushButton:
        return self.lang_btn

    @property
    def cleanup_pill(self) -> QPushButton:
        return self.cleanup_btn

    def set_language_code(self, code: str) -> None:
        self.set_language(code)

    def set_language(self, code: str) -> None:
        """Set active spoken language."""
        if self.language_manager.set_language(code):
            self._update_lang_btn_text()
            self.language_changed.emit(code)

    def set_cleanup_level(self, level: CleanupLevel | str) -> None:
        """Set active auto cleanup tier."""
        self.cleanup_level = CleanupLevel(level) if isinstance(level, str) else level
        self._update_cleanup_btn_text()
        self.cleanup_level_changed.emit(self.cleanup_level.value)

    def _reposition(self) -> None:
        """Position pill horizontally centered near the bottom of primary screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.availableGeometry()
            x = geom.x() + (geom.width() - self.width()) // 2
            y = geom.y() + geom.height() - self.height() - 65
            self.move(x, y)
        else:
            self.move(400, 700)

    # -----------------------------------------------------------------------
    # State Transitions & Animations
    # -----------------------------------------------------------------------

    def start_flow(self) -> None:
        """Activate listening state when Ctrl+Shift is pressed down."""
        self._state = "listening"
        self._reposition()
        self.status_lbl.setText("Flow Dictating...")
        self.status_lbl.setStyleSheet("color: #38BDF8; background: transparent;")
        self.orb.set_active(True)
        self.wave.set_active(True)
        self.wave.show()
        self.undo_btn.hide()

        self._fade_anim.stop()
        self.setWindowOpacity(0.0)
        self.show()
        self.raise_()
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def transcribing_flow(self) -> None:
        """Switch to transcribing state when Ctrl+Shift is released."""
        self._state = "transcribing"
        self.status_lbl.setText("Transcribing & Cleaning...")
        self.status_lbl.setStyleSheet("color: #A78BFA; background: transparent;")
        self.wave.set_active(False)
        self.wave.hide()

    def finish_flow(self, text: str, show_undo: bool = True) -> None:
        """Display success state and fade out smoothly."""
        self._state = "done"
        preview = text[:20] + "..." if len(text) > 20 else text
        self.status_lbl.setText(f"Pasted: \"{preview}\"")
        self.status_lbl.setStyleSheet("color: #34D399; background: transparent;")
        self.orb.set_active(False)

        if show_undo:
            self.undo_btn.show()

        # Display for 1800ms so user can see what was typed and optionally click undo
        QTimer.singleShot(1800, self._fade_out)

    def cancel_flow(self) -> None:
        """Cancel immediately without pasting."""
        self._state = "idle"
        self.status_lbl.setText("Cancelled")
        self.status_lbl.setStyleSheet("color: #F87171; background: transparent;")
        self.orb.set_active(False)
        self.wave.set_active(False)
        QTimer.singleShot(350, self._fade_out)

    def _fade_out(self) -> None:
        if not self.isVisible() or self._state == "listening":
            return
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self.windowOpacity())
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_finished)
        self._fade_anim.start()

    def _on_fade_out_finished(self) -> None:
        self.hide()
        self.undo_btn.hide()
        try:
            self._fade_anim.finished.disconnect(self._on_fade_out_finished)
        except Exception:
            pass

    def paintEvent(self, event) -> None:
        """Draw luxury dark rounded pill background with subtle glow border."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = self.rect().adjusted(1, 1, -1, -1)
        radius = rect.height() / 2.0

        # Semi-translucent dark glass background
        painter.setBrush(QColor(15, 23, 42, 235))
        painter.setPen(QPen(QColor(51, 65, 85, 180), 1.2))
        painter.drawRoundedRect(rect, radius, radius)
