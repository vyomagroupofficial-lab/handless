"""Universal Screen Lens Overlay (Win + Shift + Space).

Instant vision query on whatever is currently on your screen without leaving your workflow:
- Highlights the active window with a fluid glowing bounding box.
- Accepts voice questions or quick action chips:
    * "Explain this error in my terminal"
    * "Summarize this long email"
    * "Extract numbers in this chart into a table"
- Renders an in-place floating answer card with instant copy and voice narration.
- Dismissable via Esc or clicking outside the window.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Any, Callable, Dict, Optional

from PIL import Image, ImageGrab
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
from PySide6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

try:
    import win32gui
    import win32process
except ImportError:
    win32gui = None  # type: ignore
    win32process = None  # type: ignore

import pyperclip

from handless.intelligence.gemini_client import GeminiInterpreter
from handless.intelligence.groq_client import GroqInterpreter
from handless.ui.icons import (
    SVG_ARROW_UP,
    SVG_CHECK,
    SVG_CLOSE,
    SVG_COPY,
    SVG_EYE,
    SVG_MIC,
    SVG_SPARKLE,
    SVG_WINDOW,
    render_svg_icon,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)


def get_foreground_window_info() -> Dict[str, Any]:
    """Retrieve the title and bounding rectangle of the current foreground window."""
    if not win32gui:
        return {"title": "Desktop Screen", "rect": None}
    try:
        hwnd = win32gui.GetForegroundWindow()
        if hwnd:
            title = win32gui.GetWindowText(hwnd).strip()
            rect = win32gui.GetWindowRect(hwnd)  # (left, top, right, bottom)
            return {"hwnd": hwnd, "title": title or "Active Window", "rect": rect}
    except Exception as exc:
        logger.debug("Could not inspect foreground window: %s", exc)
    return {"title": "Active Window", "rect": None}


class ScreenLensOverlay(QWidget):
    """Full-screen transparent overlay highlighting the active window with interactive AI lens."""

    lens_closed = Signal()
    query_submitted = Signal(str)

    def __init__(
        self,
        gemini: Optional[GeminiInterpreter] = None,
        groq: Optional[GroqInterpreter] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.gemini = gemini
        self.groq = groq

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self._active_window_title = "Active Window"
        self._target_rect: Optional[QRect] = None
        self._captured_image: Optional[Image.Image] = None
        self._glow_phase = 0.0
        self._is_analyzing = False

        self._init_ui()
        self._setup_glow_timer()

    def _init_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # Container widget for floating controls
        self.hud_container = QWidget(self)
        self.hud_container.setObjectName("lensHudContainer")
        self.hud_container.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)

        hud_layout = QVBoxLayout(self.hud_container)
        hud_layout.setContentsMargins(20, 20, 20, 20)
        hud_layout.setSpacing(12)
        hud_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

        # 1. Top HUD Capsule (Title + Query bar + Close)
        self.pill_bar = QWidget(self.hud_container)
        self.pill_bar.setObjectName("lensPillBar")
        self.pill_bar.setFixedWidth(640)
        self.pill_bar.setStyleSheet("""
            QWidget#lensPillBar {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 22px;
            }
        """)

        pill_shadow = QGraphicsDropShadowEffect(self.pill_bar)
        pill_shadow.setBlurRadius(28)
        pill_shadow.setOffset(0, 8)
        pill_shadow.setColor(QColor(0, 0, 0, 110))
        self.pill_bar.setGraphicsEffect(pill_shadow)

        pill_layout = QHBoxLayout(self.pill_bar)
        pill_layout.setContentsMargins(14, 8, 14, 8)
        pill_layout.setSpacing(10)

        # Sparkle Lens Icon
        sparkle_lbl = QLabel(self.pill_bar)
        sparkle_lbl.setPixmap(render_svg_pixmap(SVG_SPARKLE, 20, 20, color="#10B981"))
        sparkle_lbl.setFixedSize(20, 20)
        pill_layout.addWidget(sparkle_lbl)

        # Active Window Title Badge
        self.target_badge = QLabel("Screen Lens", self.pill_bar)
        self.target_badge.setObjectName("targetBadge")
        self.target_badge.setStyleSheet("""
            QLabel#targetBadge {
                background-color: #27272A;
                color: #E4E4E7;
                font-weight: 600;
                font-size: 11px;
                padding: 4px 10px;
                border-radius: 10px;
            }
        """)
        self.target_badge.setMaximumWidth(160)
        pill_layout.addWidget(self.target_badge)

        # Query Input Field
        self.query_input = QLineEdit(self.pill_bar)
        self.query_input.setObjectName("lensQueryInput")
        self.query_input.setPlaceholderText("Ask anything about this screen (or speak)...")
        self.query_input.setStyleSheet("""
            QLineEdit#lensQueryInput {
                background-color: transparent;
                color: #FFFFFF;
                font-size: 12.5px;
                border: none;
                padding: 4px 6px;
            }
            QLineEdit#lensQueryInput::placeholder {
                color: #71717A;
            }
        """)
        self.query_input.returnPressed.connect(self._on_submit_query)
        pill_layout.addWidget(self.query_input, stretch=1)

        # Send / Ask Button
        self.send_btn = QPushButton(self.pill_bar)
        self.send_btn.setObjectName("lensSendBtn")
        self.send_btn.setIcon(render_svg_icon(SVG_ARROW_UP, 14, color="#FFFFFF"))
        self.send_btn.setFixedSize(28, 28)
        self.send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.send_btn.setStyleSheet("""
            QPushButton#lensSendBtn {
                background-color: #10B981;
                border: none;
                border-radius: 14px;
            }
            QPushButton#lensSendBtn:hover {
                background-color: #059669;
            }
        """)
        self.send_btn.clicked.connect(self._on_submit_query)
        pill_layout.addWidget(self.send_btn)

        # Close Button
        close_btn = QPushButton(self.pill_bar)
        close_btn.setObjectName("lensCloseBtn")
        close_btn.setIcon(render_svg_icon(SVG_CLOSE, 14, color="#A1A1AA", hover_color="#FFFFFF"))
        close_btn.setFixedSize(28, 28)
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton#lensCloseBtn {
                background-color: #27272A;
                border: none;
                border-radius: 14px;
            }
            QPushButton#lensCloseBtn:hover {
                background-color: #3F3F46;
            }
        """)
        close_btn.clicked.connect(self.close_lens)
        pill_layout.addWidget(close_btn)

        hud_layout.addWidget(self.pill_bar, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 2. Quick Action Chips Row
        self.chips_row = QWidget(self.hud_container)
        chips_layout = QHBoxLayout(self.chips_row)
        chips_layout.setContentsMargins(0, 0, 0, 0)
        chips_layout.setSpacing(8)
        chips_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        chips_data = [
            ("Explain this error", "Explain any errors, warnings, or anomalies visible on this screen clearly."),
            ("Summarize content", "Summarize the primary document or contents visible on screen."),
            ("Extract numbers & data", "Extract all numerical metrics, numbers, and data points into a clear markdown table."),
            ("Key takeaways", "List the key takeaways and actionable items from this window."),
        ]

        for label, query_text in chips_data:
            chip_btn = QPushButton(label, self.chips_row)
            chip_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            chip_btn.setStyleSheet("""
                QPushButton {
                    background-color: rgba(24, 24, 27, 0.85);
                    color: #D4D4D8;
                    font-size: 11px;
                    font-weight: 500;
                    border: 1px solid rgba(63, 63, 70, 0.7);
                    border-radius: 12px;
                    padding: 5px 12px;
                }
                QPushButton:hover {
                    background-color: #27272A;
                    color: #FFFFFF;
                    border-color: #10B981;
                }
            """)
            chip_btn.clicked.connect(lambda _, q=query_text: self.ask_question(q))
            chips_layout.addWidget(chip_btn)

        hud_layout.addWidget(self.chips_row, alignment=Qt.AlignmentFlag.AlignHCenter)

        # 3. Floating Answer Card
        self.answer_card = QWidget(self.hud_container)
        self.answer_card.setObjectName("lensAnswerCard")
        self.answer_card.setFixedWidth(640)
        self.answer_card.hide()
        self.answer_card.setStyleSheet("""
            QWidget#lensAnswerCard {
                background-color: #18181B;
                border: 1px solid #27272A;
                border-radius: 18px;
            }
        """)

        card_shadow = QGraphicsDropShadowEffect(self.answer_card)
        card_shadow.setBlurRadius(32)
        card_shadow.setOffset(0, 10)
        card_shadow.setColor(QColor(0, 0, 0, 130))
        self.answer_card.setGraphicsEffect(card_shadow)

        card_layout = QVBoxLayout(self.answer_card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(10)

        # Answer Header
        ans_hdr = QHBoxLayout()
        ans_hdr.setSpacing(8)

        ai_badge = QLabel("Lens Intelligence", self.answer_card)
        ai_badge.setStyleSheet("color: #10B981; font-weight: 700; font-size: 11.5px; font-family: 'Segoe UI', sans-serif;")
        ans_hdr.addWidget(ai_badge)

        self.model_badge = QLabel("Gemini Vision", self.answer_card)
        self.model_badge.setStyleSheet("color: #71717A; font-size: 10.5px;")
        ans_hdr.addWidget(self.model_badge)

        ans_hdr.addStretch(1)

        copy_btn = QPushButton(self.answer_card)
        copy_btn.setIcon(render_svg_icon(SVG_COPY, 13, color="#A1A1AA", hover_color="#FFFFFF"))
        copy_btn.setFixedSize(24, 24)
        copy_btn.setToolTip("Copy to Clipboard")
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setStyleSheet("QPushButton { background-color: #27272A; border: none; border-radius: 12px; } QPushButton:hover { background-color: #3F3F46; }")
        copy_btn.clicked.connect(self._copy_answer)
        ans_hdr.addWidget(copy_btn)

        card_layout.addLayout(ans_hdr)

        # Scrollable Answer Text
        self.answer_text = QTextEdit(self.answer_card)
        self.answer_text.setReadOnly(True)
        self.answer_text.setFixedHeight(220)
        self.answer_text.setStyleSheet("""
            QTextEdit {
                background-color: #202023;
                color: #F4F4F5;
                font-size: 12px;
                line-height: 1.5;
                border: 1px solid #2E2E32;
                border-radius: 12px;
                padding: 10px;
                font-family: 'Segoe UI', sans-serif;
            }
        """)
        card_layout.addWidget(self.answer_text)

        hud_layout.addWidget(self.answer_card, alignment=Qt.AlignmentFlag.AlignHCenter)

    def _setup_glow_timer(self) -> None:
        self._glow_timer = QTimer(self)
        self._glow_timer.timeout.connect(self._on_glow_tick)
        self._glow_timer.start(40)

    def _on_glow_tick(self) -> None:
        self._glow_phase = (self._glow_phase + 0.05)
        self.update()

    def activate_lens(self) -> None:
        """Inspect foreground window, grab screen crop, and display lens overlay."""
        # 1. Inspect Foreground Window
        info = get_foreground_window_info()
        self._active_window_title = info.get("title", "Active Window")
        trunc_title = self._active_window_title[:22] + "..." if len(self._active_window_title) > 22 else self._active_window_title
        self.target_badge.setText(trunc_title)
        self.target_badge.setToolTip(self._active_window_title)

        # 2. Geometry & Screen Sizing
        screen = QApplication.primaryScreen()
        if screen:
            screen_geom = screen.geometry()
            self.setGeometry(screen_geom)
        else:
            self.setGeometry(0, 0, 1920, 1080)

        # 3. Calculate target bounding box
        rect_tuple = info.get("rect")
        if rect_tuple and len(rect_tuple) == 4:
            l, t, r, b = rect_tuple
            # Clamp to screen
            w = max(100, r - l)
            h = max(100, b - t)
            self._target_rect = QRect(l, t, w, h)
        else:
            self._target_rect = None

        # 4. Capture screenshot
        try:
            if self._target_rect:
                self._captured_image = ImageGrab.grab(
                    bbox=(self._target_rect.left(), self._target_rect.top(), self._target_rect.right(), self._target_rect.bottom())
                )
            else:
                self._captured_image = ImageGrab.grab()
        except Exception as exc:
            logger.warning("Screen capture failed for lens: %s", exc)
            self._captured_image = None

        # 5. Position HUD Pill above or inside window
        self.answer_card.hide()
        self.query_input.clear()
        self.show()
        self.raise_()
        self.activateWindow()
        self.query_input.setFocus()

    def close_lens(self) -> None:
        """Dismiss the lens overlay."""
        self.hide()
        self.lens_closed.emit()

    def _on_submit_query(self) -> None:
        text = self.query_input.text().strip()
        if text:
            self.ask_question(text)

    def ask_question(self, question: str) -> None:
        """Submit vision query to Gemini/Groq and display structured answer in card."""
        if not question:
            return

        self.query_submitted.emit(question)
        self.query_input.setText(question)
        self.answer_text.setText("Analyzing screen content with Gemini Vision...")
        self.answer_card.show()
        self._is_analyzing = True

        threading.Thread(target=self._run_vision_analysis_worker, args=(question,), daemon=True).start()

    def _run_vision_analysis_worker(self, question: str) -> None:
        """Background thread executing multimodal analysis."""
        try:
            img = self._captured_image
            if img is None:
                img = ImageGrab.grab()

            answer = ""
            # Tier 1: Gemini Multimodal Vision
            if self.gemini and self.gemini.is_available:
                self.model_badge.setText("Gemini 2.5 Flash Vision")
                prompt = (
                    f"You are the Handless Screen Lens inspecting the user's active window ('{self._active_window_title}').\n"
                    f"User Question: {question}\n\n"
                    "Analyze the provided screenshot carefully. Provide a direct, concise, formatted, practical answer. "
                    "Use bullet points or tables where appropriate."
                )
                answer = self.gemini.analyze_image(img, prompt=prompt)

            # Fallback or Tier 2: Groq / Local OCR fallback
            if not answer and self.groq and self.groq.is_available:
                self.model_badge.setText("Groq Cloud Vision")
                answer = self.groq.chat(f"Context: inspecting window '{self._active_window_title}'. User question: {question}")

            if not answer:
                answer = (
                    f"Analyzed active window: {self._active_window_title}.\n\n"
                    "Unable to connect to Vision API. Please verify GEMINI_API_KEY in Settings."
                )

            QTimer.singleShot(0, lambda: self._display_answer(answer))
        except Exception as exc:
            logger.error("Screen Lens error: %s", exc)
            QTimer.singleShot(0, lambda: self._display_answer(f"Analysis error: {exc}"))

    def _display_answer(self, text: str) -> None:
        self._is_analyzing = False
        self.answer_text.setMarkdown(text)

    def _copy_answer(self) -> None:
        text = self.answer_text.toPlainText()
        if text:
            pyperclip.copy(text)

    def paintEvent(self, event) -> None:
        """Render fluid dark backdrop with glowing active window bounding box."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()

        # Dimmed backdrop
        if self._target_rect:
            # Cut-out active window so it stays crystal clear
            path = QPainterPath()
            path.addRect(0, 0, w, h)

            # Subtract active window rect with rounded corners
            win_path = QPainterPath()
            win_path.addRoundedRect(self._target_rect, 10, 10)
            dim_path = path.subtracted(win_path)

            painter.fillPath(dim_path, QColor(0, 0, 0, 95))

            # Emerald Glowing Border around the active window
            glow_alpha = int(140 + 70 * (0.5 + 0.5 * (self._glow_phase % 6.28)))
            pen = QPen(QColor(16, 185, 129, min(255, glow_alpha)), 2.8)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRoundedRect(self._target_rect, 10, 10)

            # Outer subtle glow line
            outer_pen = QPen(QColor(16, 185, 129, 45), 6.0)
            painter.setPen(outer_pen)
            painter.drawRoundedRect(self._target_rect.adjusted(-2, -2, 2, 2), 12, 12)
        else:
            painter.fillRect(0, 0, w, h, QColor(0, 0, 0, 110))

    def mousePressEvent(self, event) -> None:
        """Close lens when clicking outside the HUD controls and outside active window."""
        pos = event.position().toPoint()
        # If clicked inside hud pill or answer card, keep focus
        if self.pill_bar.geometry().contains(pos) or (self.answer_card.isVisible() and self.answer_card.geometry().contains(pos)):
            super().mousePressEvent(event)
            return

        # Otherwise clicking outside dismisses lens
        self.close_lens()

    def keyPressEvent(self, event) -> None:
        """Dismiss on Esc key."""
        if event.key() == Qt.Key.Key_Escape:
            self.close_lens()
            event.accept()
        else:
            super().keyPressEvent(event)

