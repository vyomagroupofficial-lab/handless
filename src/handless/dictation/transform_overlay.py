"""Floating Transform HUD Menu (Ctrl + Shift + T).

Appears near the active text cursor when the user highlights text and presses the hotkey.
Offers 1-click transformation options:
- Polish
- Prompt Engineer
- Fix Grammar
- Executive Tone
- Bulletize
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Optional

import pyperclip
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
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from handless.dictation.paste_controller import paste_text
from handless.dictation.text_transformer import TransformType, transform_text
from handless.ui.icons import (
    SVG_BRAIN,
    SVG_BRIEFCASE,
    SVG_CHECK,
    SVG_CLOSE,
    SVG_FILE_TEXT,
    SVG_PENCIL,
    SVG_SPARKLE,
    render_svg_icon,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)


def capture_selected_text_with_clipboard() -> str:
    """Capture currently selected text by sending Ctrl+C and reading clipboard safely."""
    import pyautogui
    import pyperclip

    # Ensure modifier keys from global hotkeys (Alt, Shift, Ctrl) are released
    try:
        pyautogui.keyUp("alt")
        pyautogui.keyUp("shift")
        pyautogui.keyUp("ctrl")
    except Exception:
        pass

    old_clip = ""
    try:
        old_clip = pyperclip.paste()
    except Exception:
        pass

    # Clear clipboard temporarily so we know if new text arrives
    try:
        pyperclip.copy("")
    except Exception:
        pass

    time.sleep(0.06)

    # Simulate Ctrl+C
    try:
        pyautogui.hotkey("ctrl", "c")
    except Exception:
        import pynput.keyboard
        kb = pynput.keyboard.Controller()
        with kb.pressed(pynput.keyboard.Key.ctrl):
            kb.tap("c")

    time.sleep(0.08)
    new_clip = ""
    try:
        new_clip = pyperclip.paste()
    except Exception:
        pass

    # If new text arrived, return it
    if new_clip and new_clip.strip():
        return new_clip.strip()

    # Fall back to existing clipboard if available
    if old_clip and old_clip.strip():
        try:
            pyperclip.copy(old_clip)
        except Exception:
            pass
        return old_clip.strip()

    return ""


class TransformOverlay(QWidget):
    """Floating luxury HUD capsule menu for transforming selected text in-place."""

    transform_requested = Signal(str, str)  # text, transform_type
    transform_completed = Signal(str)

    def __init__(
        self,
        llm_client: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.llm_client = llm_client

        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._selected_text = ""
        self._is_transforming = False
        self._init_ui()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 10, 10, 10)

        # Main Capsule Card
        self.card = QWidget(self)
        self.card.setObjectName("transformCard")
        self.card.setStyleSheet("""
            QWidget#transformCard {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 20px;
            }
        """)

        shadow = QGraphicsDropShadowEffect(self.card)
        shadow.setBlurRadius(28)
        shadow.setOffset(0, 6)
        shadow.setColor(QColor(0, 0, 0, 120))
        self.card.setGraphicsEffect(shadow)

        layout = QHBoxLayout(self.card)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(6)

        # Title / Mode Icon
        icon_lbl = QLabel(self.card)
        icon_lbl.setPixmap(render_svg_pixmap(SVG_SPARKLE, 16, 16, color="#10B981"))
        icon_lbl.setFixedSize(16, 16)
        layout.addWidget(icon_lbl)

        self.title_lbl = QLabel("Transform", self.card)
        self.title_lbl.setStyleSheet("color: #FFFFFF; font-weight: 700; font-size: 11.5px; font-family: 'Segoe UI', sans-serif;")
        layout.addWidget(self.title_lbl)

        badge_lbl = QLabel("Ctrl+Alt+T", self.card)
        badge_lbl.setStyleSheet("color: #A1A1AA; font-size: 9px; font-weight: 600; background: #27272A; border-radius: 4px; padding: 2px 5px;")
        layout.addWidget(badge_lbl)

        # Separator
        sep = QWidget(self.card)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: #27272A;")
        layout.addWidget(sep)

        # Action Buttons
        options = [
            ("Polish", TransformType.POLISH, SVG_SPARKLE, "#10B981"),
            ("Prompt Engineer", TransformType.PROMPT_ENGINEER, SVG_BRAIN, "#8B5CF6"),
            ("Fix Grammar", TransformType.GRAMMAR, SVG_PENCIL, "#3B82F6"),
            ("Executive", TransformType.TONE_EXECUTIVE, SVG_BRIEFCASE, "#F59E0B"),
            ("Bullets", TransformType.BULLETIZE, SVG_FILE_TEXT, "#EC4899"),
        ]

        for label, t_type, icon_svg, color in options:
            btn = QPushButton(self.card)
            btn.setIcon(render_svg_icon(icon_svg, 12, color=color))
            btn.setText(label)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setFixedHeight(28)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: #27272A;
                    color: #E4E4E7;
                    font-size: 11px;
                    font-weight: 500;
                    border: 1px solid #3F3F46;
                    border-radius: 14px;
                    padding: 0 10px;
                }}
                QPushButton:hover {{
                    background-color: #3F3F46;
                    color: #FFFFFF;
                    border-color: {color};
                }}
            """)
            btn.clicked.connect(lambda _, t=t_type: self.execute_transform(t))
            layout.addWidget(btn)

        # Close Button
        close_btn = QPushButton(self.card)
        close_btn.setIcon(render_svg_icon(SVG_CLOSE, 12, color="#71717A", hover_color="#FFFFFF"))
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("QPushButton { background-color: transparent; border: none; border-radius: 12px; } QPushButton:hover { background-color: #27272A; }")
        close_btn.clicked.connect(self.hide)
        layout.addWidget(close_btn)

        outer.addWidget(self.card)
        self.resize(600, 52)

    def open_at_cursor(self) -> None:
        """Alias for activate_on_selection."""
        self.activate_on_selection()

    def execute_direct_transform(self, transform_type: str | TransformType) -> None:
        """Capture text from foreground and execute transform directly without opening menu."""
        text = capture_selected_text_with_clipboard()
        if not text:
            logger.info("TransformOverlay: No text currently selected for direct transform.")
            return
        self._selected_text = text
        if isinstance(transform_type, str):
            try:
                t_enum = TransformType(transform_type.lower().strip())
            except Exception:
                t_enum = TransformType.POLISH
        else:
            t_enum = transform_type
        self.execute_transform(t_enum)

    def activate_on_selection(self) -> None:
        """Capture selected text and display menu near mouse cursor."""
        text = capture_selected_text_with_clipboard()
        self._selected_text = text or ""

        if text:
            preview = text[:20] + "..." if len(text) > 20 else text
            self.title_lbl.setText(f'Transform: "{preview}"')
        else:
            self.title_lbl.setText("Transform Text")

        cursor_pos = QCursor.pos()
        screen = QApplication.screenAt(cursor_pos) or QApplication.primaryScreen()
        w = 600
        h = 52
        if screen:
            avail = screen.availableGeometry()
            x = cursor_pos.x() - (w // 2)
            x = max(avail.x() + 10, min(x, avail.x() + avail.width() - w - 10))
            y = cursor_pos.y() - h - 14
            if y < avail.y() + 10:
                y = cursor_pos.y() + 24
            self.setGeometry(x, y, w, h)
        else:
            self.move(cursor_pos.x() - (w // 2), cursor_pos.y() - h - 14)

        self.show()
        self.raise_()
        self.activateWindow()

    def execute_transform(self, transform_type: TransformType) -> None:
        """Transform captured selection in background and paste back in-place."""
        if not self._selected_text:
            self._selected_text = capture_selected_text_with_clipboard()

        if not self._selected_text or self._is_transforming:
            self.hide()
            return

        self._is_transforming = True
        self.hide()

        text_to_transform = self._selected_text
        self.transform_requested.emit(text_to_transform, transform_type.value)

        def worker() -> None:
            try:
                transformed = transform_text(
                    text=text_to_transform,
                    transform_type=transform_type,
                    llm_client=self.llm_client,
                )
                if transformed:
                    # In-place paste back into active window
                    paste_text(transformed, preserve_clipboard=True)
                    self.transform_completed.emit(transformed)
                    logger.info("Transformed text with %s and pasted in-place.", transform_type.value)
            except Exception as exc:
                logger.error("Error executing text transform: %s", exc)
            finally:
                self._is_transforming = False

        threading.Thread(target=worker, daemon=True).start()

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.hide()
            event.accept()
        else:
            super().keyPressEvent(event)

