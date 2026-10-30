"""Modern Call & Meeting Transcription Screen for Vyoma Handless.

Provides real-time dual-stream transcription for Zoom, Google Meet, WhatsApp, and Teams:
- Diarized live stream: 'You' (Mic - Emerald) vs 'Speaker 1/2' (System - Indigo).
- Wispr Flow-style smart entity bolding & colored badges.
- Dual audio level visualizers (Mic + System loopback).
- 1-Click AI Summarize (Executive Summary, Action Items, Key Decisions).
- 1-Click Copy for Claude (formatted meta-prompt), Plain Text, and Markdown export.
"""

from __future__ import annotations

import logging
import os
import time
from typing import Any, Callable, Dict, List, Optional

import pyperclip
from PySide6.QtCore import QPoint, QRect, QSize, Qt, QTimer, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from handless.meeting.models import (
    MeetingSession,
    MeetingSummary,
    TranscriptTurn,
    apply_wispr_flow_highlights,
)
from handless.ui.icons import (
    SVG_ARROW_LEFT,
    SVG_ARROW_UP,
    SVG_CHECK,
    SVG_CHEVRON_RIGHT,
    SVG_COPY,
    SVG_DOWNLOAD,
    SVG_MIC,
    SVG_MORE_HORIZONTAL,
    SVG_PHONE,
    SVG_PHONE_OFF,
    SVG_RECORD_DOT,
    SVG_REFRESH,
    SVG_SEARCH,
    SVG_SPARKLE,
    SVG_STOP,
    SVG_VIDEO_CAMERA,
    SVG_VOICE_WAVE,
    render_svg_icon,
    render_svg_pixmap,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Visual Equalizer Indicator for Audio Level
# ---------------------------------------------------------------------------

class MiniEqualizerBar(QWidget):
    """Compact 4-bar audio equalizer showing live sound activity."""

    def __init__(self, color_hex: str = "#10B981", parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFixedSize(22, 16)
        self._color = QColor(color_hex)
        self._level = 0.0

    def set_level(self, level: float) -> None:
        self._level = max(0.0, min(1.0, level))
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(self._color)

        bar_width = 3.0
        gap = 2.5
        x_start = 2.0
        h_max = float(self.height() - 2)

        # 4 bars with varying phase sensitivity
        for i in range(4):
            mult = [0.8, 1.2, 1.0, 0.7][i]
            bar_h = max(2.5, min(h_max, (self._level * mult) * h_max))
            y = self.height() - bar_h - 1.0
            x = x_start + i * (bar_width + gap)
            painter.drawRoundedRect(int(x), int(y), int(bar_width), int(bar_h), 1.5, 1.5)


# ---------------------------------------------------------------------------
# Individual Diarized Speech Bubble Card
# ---------------------------------------------------------------------------

class TranscriptCard(QFrame):
    """Diarized transcript card with colored speaker pill, timestamp, and bolded text."""

    def __init__(self, turn: TranscriptTurn, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.turn = turn
        self.setObjectName("transcriptCard")

        # Styling based on speaker: "You" (Emerald) vs "Speaker" (Indigo)
        is_user = turn.is_user
        border_col = "#D1FAE5" if is_user else "#E0E7FF"
        bg_col = "#FFFFFF"

        self.setStyleSheet(f"""
            QFrame#transcriptCard {{
                background-color: {bg_col};
                border: 1px solid {border_col};
                border-radius: 12px;
            }}
            QFrame#transcriptCard:hover {{
                border-color: {'#A7F3D0' if is_user else '#C7D2FE'};
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(6)

        # Top Meta Row: Speaker Badge + Timestamp + Copy Button
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Speaker Badge Pill
        badge = QWidget(self)
        b_layout = QHBoxLayout(badge)
        b_layout.setContentsMargins(7, 3, 7, 3)
        b_layout.setSpacing(5)

        badge_bg = "#ECFDF5" if is_user else "#EEF2FF"
        badge_border = "#A7F3D0" if is_user else "#C7D2FE"
        dot_color = "#10B981" if is_user else "#6366F1"
        text_color = "#065F46" if is_user else "#3730A3"

        badge.setStyleSheet(f"""
            background-color: {badge_bg};
            border: 1px solid {badge_border};
            border-radius: 9px;
        """)

        dot_lbl = QLabel(badge)
        dot_lbl.setPixmap(render_svg_pixmap(SVG_RECORD_DOT, 8, 8, color=dot_color))
        dot_lbl.setFixedSize(8, 8)
        dot_lbl.setStyleSheet("border: none; background: transparent;")
        b_layout.addWidget(dot_lbl)

        speaker_name = "You" if is_user else turn.speaker
        self.speaker_badge = QLabel(speaker_name, badge)
        self.speaker_badge.setStyleSheet(f"color: {text_color}; font-weight: 700; font-size: 11px; border: none; background: transparent;")
        b_layout.addWidget(self.speaker_badge)
        top_row.addWidget(badge)

        # Timestamp
        time_lbl = QLabel(turn.time_str, self)
        time_lbl.setStyleSheet("color: #A1A1AA; font-size: 10.5px; font-weight: 500;")
        top_row.addWidget(time_lbl)

        top_row.addStretch(1)

        # Mini Copy turn button
        copy_btn = QPushButton(self)
        copy_btn.setIcon(render_svg_icon(SVG_COPY, 12, color="#A1A1AA", hover_color="#18181B"))
        copy_btn.setFixedSize(20, 20)
        copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        copy_btn.setToolTip("Copy statement")
        copy_btn.setStyleSheet("background: transparent; border: none;")
        copy_btn.clicked.connect(lambda: pyperclip.copy(turn.text))
        top_row.addWidget(copy_btn)

        layout.addLayout(top_row)

        # Content Text with Wispr Flow smart bolding
        self.text_label = QLabel(self)
        self.text_label.setTextFormat(Qt.TextFormat.RichText)
        self.text_label.setWordWrap(True)
        self.text_label.setText(turn.highlighted_html)
        self.text_label.setStyleSheet("""
            color: #18181B;
            font-size: 12.5px;
            line-height: 1.45;
            background: transparent;
            border: none;
        """)
        layout.addWidget(self.text_label)


# ---------------------------------------------------------------------------
# Main MeetingTranscriptsView Screen (Screen 8)
# ---------------------------------------------------------------------------

class MeetingTranscriptsView(QWidget):
    """Full-featured Live Call and Meeting Transcription screen."""

    command_submitted = Signal(str)
    voice_toggled = Signal()

    def __init__(
        self,
        transcriber: Optional[Any] = None,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("meetingTranscriptsView")
        self.transcriber = transcriber

        self._active_filter = "all"  # "all", "you", "speakers"
        self._search_query = ""
        self._cards: List[TranscriptCard] = []
        self._session_start_time = 0.0

        # Duration Clock Timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)

        self._init_ui()
        self._connect_transcriber()

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 320)

    def _init_ui(self) -> None:
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(14, 12, 14, 12)
        main_layout.setSpacing(10)

        # -------------------------------------------------------------------
        # 1. Header Bar: Meeting Title + App Badge + Duration + Audio Meters
        # -------------------------------------------------------------------
        header_card = QFrame(self)
        header_card.setObjectName("meetingHeaderCard")
        header_card.setStyleSheet("""
            QFrame#meetingHeaderCard {
                background-color: #FFFFFF;
                border: 1px solid #ECEAE3;
                border-radius: 14px;
                padding: 10px 14px;
            }
        """)
        h_layout = QVBoxLayout(header_card)
        h_layout.setContentsMargins(4, 4, 4, 4)
        h_layout.setSpacing(8)

        # Top title row
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)

        title_col = QVBoxLayout()
        title_col.setContentsMargins(0, 0, 0, 0)
        title_col.setSpacing(1)

        self.title_label = QLabel("Call Transcripts & Notes", header_card)
        self.title_label.setStyleSheet("color: #18181B; font-weight: 800; font-size: 14px;")
        title_col.addWidget(self.title_label)

        self.sub_label = QLabel("Auto-capturing Zoom, Meet, WhatsApp & Teams", header_card)
        self.sub_label.setStyleSheet("color: #71717A; font-size: 11px;")
        title_col.addWidget(self.sub_label)
        title_row.addLayout(title_col)

        title_row.addStretch(1)

        # App Detection Badge with SVG icon
        self.app_badge = QPushButton(header_card)
        self.app_badge.setObjectName("appBadge")
        self.app_badge.setIcon(render_svg_icon(SVG_VIDEO_CAMERA, 13, color="#18181B"))
        self.app_badge.setIconSize(QSize(13, 13))
        self.app_badge.setText("General Call")
        self.app_badge.setStyleSheet("""
            QPushButton#appBadge {
                background-color: #F4F3EE;
                border: 1px solid #E5E3DC;
                border-radius: 10px;
                padding: 4px 10px;
                color: #18181B;
                font-size: 11px;
                font-weight: 600;
            }
        """)
        title_row.addWidget(self.app_badge)

        h_layout.addLayout(title_row)

        # Secondary row: Dual Audio Meters + Recording Status Pill
        meters_row = QHBoxLayout()
        meters_row.setContentsMargins(0, 0, 0, 0)
        meters_row.setSpacing(14)

        # Mic Visualizer: "You" (with SVG Mic Icon)
        mic_box = QHBoxLayout()
        mic_box.setSpacing(5)
        mic_icn = QLabel(header_card)
        mic_icn.setPixmap(render_svg_pixmap(SVG_MIC, 12, 12, color="#10B981"))
        mic_icn.setFixedSize(12, 12)
        mic_lbl = QLabel("You:", header_card)
        mic_lbl.setStyleSheet("color: #71717A; font-size: 10.5px; font-weight: 600;")
        self.mic_eq = MiniEqualizerBar(color_hex="#10B981", parent=header_card)
        mic_box.addWidget(mic_icn)
        mic_box.addWidget(mic_lbl)
        mic_box.addWidget(self.mic_eq)
        meters_row.addLayout(mic_box)

        # System Loopback Visualizer: "Call / Speakers" (with SVG Phone Icon)
        sys_box = QHBoxLayout()
        sys_box.setSpacing(5)
        sys_icn = QLabel(header_card)
        sys_icn.setPixmap(render_svg_pixmap(SVG_PHONE, 12, 12, color="#6366F1"))
        sys_icn.setFixedSize(12, 12)
        sys_lbl = QLabel("Call:", header_card)
        sys_lbl.setStyleSheet("color: #71717A; font-size: 10.5px; font-weight: 600;")
        self.sys_eq = MiniEqualizerBar(color_hex="#6366F1", parent=header_card)
        sys_box.addWidget(sys_icn)
        sys_box.addWidget(sys_lbl)
        sys_box.addWidget(self.sys_eq)
        meters_row.addLayout(sys_box)

        meters_row.addStretch(1)

        # Duration Clock Pill with SVG dot
        self.clock_pill = QPushButton(header_card)
        self.clock_pill.setObjectName("clockPill")
        self.clock_pill.setIcon(render_svg_icon(SVG_RECORD_DOT, 9, color="#71717A"))
        self.clock_pill.setIconSize(QSize(9, 9))
        self.clock_pill.setText("Standby 00:00")
        self.clock_pill.setStyleSheet("""
            QPushButton#clockPill {
                background: transparent;
                border: none;
                color: #71717A;
                font-size: 11px;
                font-weight: 600;
                padding: 2px 4px;
            }
        """)
        meters_row.addWidget(self.clock_pill)

        h_layout.addLayout(meters_row)
        main_layout.addWidget(header_card)

        # -------------------------------------------------------------------
        # 2. Main Control Ribbon: Record/Stop + 1-Click AI + Copy for Claude
        # -------------------------------------------------------------------
        ribbon_layout = QHBoxLayout()
        ribbon_layout.setContentsMargins(0, 0, 0, 0)
        ribbon_layout.setSpacing(6)

        # Record / Stop Call Button
        self.record_btn = QPushButton(self)
        self.record_btn.setObjectName("recordCallBtn")
        self.record_btn.setIcon(render_svg_icon(SVG_RECORD_DOT, 11, color="#FFFFFF"))
        self.record_btn.setIconSize(QSize(11, 11))
        self.record_btn.setText("Record")
        self.record_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.record_btn.setStyleSheet("""
            QPushButton#recordCallBtn {
                background-color: #EF4444;
                color: #FFFFFF;
                border: none;
                border-radius: 12px;
                padding: 6px 11px;
                font-weight: 700;
                font-size: 11px;
            }
            QPushButton#recordCallBtn:hover {
                background-color: #DC2626;
            }
        """)
        self.record_btn.clicked.connect(self._toggle_recording)
        ribbon_layout.addWidget(self.record_btn)

        # 1-Click AI Summarize Button
        self.summarize_btn = QPushButton(self)
        self.summarize_btn.setObjectName("summarizeCallBtn")
        self.summarize_btn.setText("Summarize")
        self.summarize_btn.setIcon(render_svg_icon(SVG_SPARKLE, 13, color="#18181B"))
        self.summarize_btn.setIconSize(QSize(13, 13))
        self.summarize_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.summarize_btn.setToolTip("1-Click AI Summary: Executive notes, Action items & Decisions")
        self.summarize_btn.setStyleSheet("""
            QPushButton#summarizeCallBtn {
                background-color: #FFFFFF;
                color: #18181B;
                border: 1px solid #E5E3DC;
                border-radius: 12px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton#summarizeCallBtn:hover {
                background-color: #F4F3EE;
                border-color: #D1CFC7;
            }
        """)
        self.summarize_btn.clicked.connect(self._on_summarize_click)
        ribbon_layout.addWidget(self.summarize_btn)

        # Copy for Claude Button
        self.claude_btn = QPushButton(self)
        self.claude_btn.setObjectName("copyClaudeBtn")
        self.claude_btn.setText("Claude")
        self.claude_btn.setIcon(render_svg_icon(SVG_COPY, 12, color="#18181B"))
        self.claude_btn.setIconSize(QSize(12, 12))
        self.claude_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.claude_btn.setToolTip("Copy formatted transcript meta-prompt ready to paste into Claude")
        self.claude_btn.setStyleSheet("""
            QPushButton#copyClaudeBtn {
                background-color: #FFFFFF;
                color: #18181B;
                border: 1px solid #E5E3DC;
                border-radius: 12px;
                padding: 6px 10px;
                font-weight: 600;
                font-size: 11px;
            }
            QPushButton#copyClaudeBtn:hover {
                background-color: #F4F3EE;
                border-color: #D1CFC7;
            }
        """)
        self.claude_btn.clicked.connect(self._copy_for_claude)
        ribbon_layout.addWidget(self.claude_btn)

        ribbon_layout.addStretch(1)

        # More Actions Menu (Copy Plain, Export .md, Clear)
        self.more_btn = QPushButton(self)
        self.more_btn.setIcon(render_svg_icon(SVG_MORE_HORIZONTAL, 15, color="#52525B"))
        self.more_btn.setIconSize(QSize(15, 15))
        self.more_btn.setFixedSize(28, 28)
        self.more_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.more_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFFFFF;
                border: 1px solid #E5E3DC;
                border-radius: 8px;
            }
            QPushButton:hover {
                background-color: #F4F3EE;
            }
        """)
        self.more_btn.clicked.connect(self._open_more_menu)
        ribbon_layout.addWidget(self.more_btn)

        main_layout.addLayout(ribbon_layout)

        # -------------------------------------------------------------------
        # 3. Filter Strip & Live Search Bar
        # -------------------------------------------------------------------
        filter_row = QHBoxLayout()
        filter_row.setContentsMargins(0, 0, 0, 0)
        filter_row.setSpacing(6)

        # Speaker Filter Buttons: All, You, Speakers
        self.btn_filter_all = self._create_filter_button("All", "all", active=True)
        self.btn_filter_you = self._create_filter_button("You", "you", active=False)
        self.btn_filter_speakers = self._create_filter_button("Speakers", "speakers", active=False)

        filter_row.addWidget(self.btn_filter_all)
        filter_row.addWidget(self.btn_filter_you)
        filter_row.addWidget(self.btn_filter_speakers)
        filter_row.addStretch(1)

        # Search Bar
        search_box = QFrame(self)
        search_box.setStyleSheet("""
            background-color: #FFFFFF;
            border: 1px solid #E5E3DC;
            border-radius: 10px;
            padding: 2px 8px;
        """)
        s_layout = QHBoxLayout(search_box)
        s_layout.setContentsMargins(4, 2, 4, 2)
        s_layout.setSpacing(4)

        s_icon = QLabel(search_box)
        s_icon.setPixmap(render_svg_pixmap(SVG_SEARCH, 12, 12, color="#71717A"))
        s_layout.addWidget(s_icon)

        self.search_input = QLineEdit(search_box)
        self.search_input.setPlaceholderText("Search words...")
        self.search_input.setStyleSheet("border: none; background: transparent; font-size: 11px; color: #18181B;")
        self.search_input.textChanged.connect(self._on_search_changed)
        s_layout.addWidget(self.search_input)
        filter_row.addWidget(search_box)

        main_layout.addLayout(filter_row)

        # -------------------------------------------------------------------
        # 4. View Switcher Stack: Live Transcript Feed & AI Summary Panel
        # -------------------------------------------------------------------
        self.body_stack = QStackedWidget(self)

        # Page 0: Scrollable Transcript Feed
        self.scroll_area = QScrollArea(self.body_stack)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setStyleSheet("background: transparent; border: none;")

        self.feed_widget = QWidget()
        self.feed_widget.setStyleSheet("background: transparent;")
        self.feed_layout = QVBoxLayout(self.feed_widget)
        self.feed_layout.setContentsMargins(0, 0, 0, 0)
        self.feed_layout.setSpacing(8)

        # Empty state prompt
        self.empty_label = QLabel("No speech recorded yet.\nClick 'Record Call' when in Zoom, Meet, or WhatsApp.", self.feed_widget)
        self.empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.empty_label.setStyleSheet("color: #A1A1AA; font-size: 12px; padding: 40px 10px; line-height: 1.5;")
        self.feed_layout.addWidget(self.empty_label)
        self.feed_layout.addStretch(1)

        self.scroll_area.setWidget(self.feed_widget)
        self.body_stack.addWidget(self.scroll_area)

        # Page 1: AI Summary & Action Items View
        self.summary_card = QFrame(self.body_stack)
        self.summary_card.setObjectName("summaryCardView")
        self.summary_card.setStyleSheet("""
            QFrame#summaryCardView {
                background-color: #FFFFFF;
                border: 1px solid #ECEAE3;
                border-radius: 14px;
            }
        """)
        sum_scroll = QScrollArea(self.summary_card)
        sum_scroll.setWidgetResizable(True)
        sum_scroll.setFrameShape(QFrame.Shape.NoFrame)
        sum_scroll.setStyleSheet("background: transparent; border: none;")

        self.summary_content = QWidget()
        self.sum_layout = QVBoxLayout(self.summary_content)
        self.sum_layout.setContentsMargins(14, 14, 14, 14)
        self.sum_layout.setSpacing(10)

        self.summary_header = QLabel("AI Meeting Minutes & Executive Summary", self.summary_content)
        self.summary_header.setStyleSheet("color: #18181B; font-size: 13.5px; font-weight: 700;")
        self.sum_layout.addWidget(self.summary_header)

        self.summary_text_lbl = QLabel(self.summary_content)
        self.summary_text_lbl.setWordWrap(True)
        self.summary_text_lbl.setTextFormat(Qt.TextFormat.MarkdownText)
        self.summary_text_lbl.setStyleSheet("color: #27272A; font-size: 12px; line-height: 1.5;")
        self.sum_layout.addWidget(self.summary_text_lbl)
        self.sum_layout.addStretch(1)

        sum_scroll.setWidget(self.summary_content)
        c_layout = QVBoxLayout(self.summary_card)
        c_layout.setContentsMargins(0, 0, 0, 0)
        c_layout.addWidget(sum_scroll)

        # Back to Transcript button inside Summary Card (Clean SVG Arrow)
        back_btn = QPushButton("Return to Live Transcript", self.summary_card)
        back_btn.setIcon(render_svg_icon(SVG_ARROW_LEFT, 13, color="#18181B"))
        back_btn.setIconSize(QSize(13, 13))
        back_btn.setStyleSheet("""
            background-color: #F4F3EE;
            border: 1px solid #E5E3DC;
            border-radius: 10px;
            padding: 6px 12px;
            color: #18181B;
            font-weight: 600;
            font-size: 11px;
            margin: 8px 14px;
        """)
        back_btn.clicked.connect(lambda: self.body_stack.setCurrentIndex(0))
        c_layout.addWidget(back_btn)

        self.body_stack.addWidget(self.summary_card)
        main_layout.addWidget(self.body_stack, stretch=1)

        # 4. Synchronized Bottom Prompt Bar
        bottom_bar = self._build_bottom_bar()
        main_layout.addWidget(bottom_bar)

    def _build_bottom_bar(self) -> QWidget:
        container = QWidget(self)
        container.setObjectName("promptContainerCard")
        container.setStyleSheet(
            "QWidget#promptContainerCard { background-color: #F5F4EE; border: 1px solid #E7E4DA; border-radius: 18px; padding: 6px; }"
        )
        layout = QHBoxLayout(container)
        layout.setContentsMargins(8, 4, 6, 4)
        layout.setSpacing(8)

        wave_btn = QPushButton(container)
        wave_btn.setIcon(render_svg_icon(SVG_VOICE_WAVE, 16, color="#71717A", hover_color="#18181B"))
        wave_btn.setFixedSize(24, 24)
        wave_btn.setStyleSheet("background: transparent; border: none;")
        wave_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        wave_btn.clicked.connect(self.voice_toggled)
        layout.addWidget(wave_btn)

        sep = QWidget(container)
        sep.setFixedSize(1, 16)
        sep.setStyleSheet("background-color: #E2DFD6;")
        layout.addWidget(sep)

        self.input_field = QLineEdit(container)
        self.input_field.setPlaceholderText("Tell Handless what to do...")
        self.input_field.setStyleSheet(
            "background: transparent; border: none; color: #18181B; font-size: 12.5px;"
        )
        self.input_field.returnPressed.connect(self._handle_enter)
        layout.addWidget(self.input_field, stretch=1)

        send_btn = QPushButton(container)
        send_btn.setIcon(render_svg_icon(SVG_ARROW_UP, 14, color="#FFFFFF"))
        send_btn.setFixedSize(28, 28)
        send_btn.setStyleSheet("background-color: #18181B; border-radius: 14px; border: none;")
        send_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        send_btn.clicked.connect(self._handle_enter)
        layout.addWidget(send_btn)

        return container

    def _handle_enter(self) -> None:
        text = self.input_field.text().strip()
        if text:
            self.command_submitted.emit(text)
            self.input_field.clear()

    def set_transcriber(self, transcriber: Any) -> None:
        """Attach or update MeetingTranscriber engine instance."""
        self.transcriber = transcriber
        self._connect_transcriber()

    def _create_filter_button(self, label: str, filter_key: str, active: bool = False) -> QPushButton:
        btn = QPushButton(label, self)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._update_filter_button_style(btn, active)
        btn.clicked.connect(lambda: self._set_filter(filter_key, btn))
        return btn

    def _update_filter_button_style(self, btn: QPushButton, active: bool) -> None:
        if active:
            btn.setStyleSheet("""
                background-color: #18181B;
                color: #FFFFFF;
                border: none;
                border-radius: 9px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 700;
            """)
        else:
            btn.setStyleSheet("""
                background-color: #F4F3EE;
                color: #71717A;
                border: 1px solid #E5E3DC;
                border-radius: 9px;
                padding: 4px 10px;
                font-size: 11px;
                font-weight: 600;
            """)

    def _set_filter(self, filter_key: str, active_btn: QPushButton) -> None:
        self._active_filter = filter_key
        for b in (self.btn_filter_all, self.btn_filter_you, self.btn_filter_speakers):
            self._update_filter_button_style(b, b == active_btn)
        self._refilter_cards()

    def _connect_transcriber(self) -> None:
        if not self.transcriber:
            return
        self.transcriber.turn_added.connect(self.add_turn)
        self.transcriber.mic_level_changed.connect(self.mic_eq.set_level)
        self.transcriber.system_level_changed.connect(self.sys_eq.set_level)
        self.transcriber.recording_state_changed.connect(self._on_recording_state_changed)
        self.transcriber.summary_ready.connect(self._on_summary_ready)

    def _toggle_recording(self) -> None:
        if not self.transcriber:
            return
        if self.transcriber.is_recording:
            self.transcriber.stop_recording()
        else:
            self.transcriber.start_recording()

    def _on_recording_state_changed(self, is_recording: bool) -> None:
        if is_recording:
            self.record_btn.setText("Stop")
            self.record_btn.setIcon(render_svg_icon(SVG_STOP, 11, color="#FFFFFF"))
            self.record_btn.setStyleSheet("""
                QPushButton#recordCallBtn {
                    background-color: #18181B;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 12px;
                    font-weight: 700;
                    font-size: 11px;
                }
                QPushButton#recordCallBtn:hover {
                    background-color: #27272A;
                }
            """)
            self._session_start_time = time.time()
            self._clock_timer.start(1000)
            self.clock_pill.setIcon(render_svg_icon(SVG_RECORD_DOT, 9, color="#EF4444"))
            self.clock_pill.setStyleSheet("color: #EF4444; font-size: 11px; font-weight: 700; background: transparent; border: none;")
            sess = self.transcriber.current_session
            if sess:
                self.app_badge.setText(sess.app_name)
                self.title_label.setText(sess.title)
        else:
            self.record_btn.setText("Record")
            self.record_btn.setIcon(render_svg_icon(SVG_RECORD_DOT, 11, color="#FFFFFF"))
            self.record_btn.setStyleSheet("""
                QPushButton#recordCallBtn {
                    background-color: #EF4444;
                    color: #FFFFFF;
                    border: none;
                    border-radius: 12px;
                    padding: 6px 11px;
                    font-weight: 700;
                    font-size: 11px;
                }
                QPushButton#recordCallBtn:hover {
                    background-color: #DC2626;
                }
            """)
            self._clock_timer.stop()
            self.clock_pill.setIcon(render_svg_icon(SVG_CHECK, 10, color="#10B981"))
            self.clock_pill.setStyleSheet("color: #71717A; font-size: 11px; font-weight: 600; background: transparent; border: none;")
            self.clock_pill.setText("Saved")

    def _update_clock(self) -> None:
        if self._session_start_time <= 0:
            return
        elapsed = int(time.time() - self._session_start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        self.clock_pill.setText(f"Rec {mins:02d}:{secs:02d}")

    def add_turn(self, turn: TranscriptTurn) -> None:
        """Add speech statement card to feed."""
        self.empty_label.setVisible(False)
        card = TranscriptCard(turn, parent=self.feed_widget)
        self._cards.append(card)

        # Insert before bottom stretch
        count = self.feed_layout.count()
        index = max(0, count - 1)
        self.feed_layout.insertWidget(index, card)

        self._apply_card_visibility(card)

        # Auto-scroll to bottom
        QTimer.singleShot(40, lambda: self.scroll_area.verticalScrollBar().setValue(
            self.scroll_area.verticalScrollBar().maximum()
        ))

    def _apply_card_visibility(self, card: TranscriptCard) -> None:
        turn = card.turn
        visible = True
        if self._active_filter == "you" and not turn.is_user:
            visible = False
        elif self._active_filter == "speakers" and turn.is_user:
            visible = False

        if visible and self._search_query:
            visible = (self._search_query.lower() in turn.text.lower())

        card.setVisible(visible)

    def _refilter_cards(self) -> None:
        for card in self._cards:
            self._apply_card_visibility(card)

    def _on_search_changed(self, text: str) -> None:
        self._search_query = text.strip()
        self._refilter_cards()

    def _on_summarize_click(self) -> None:
        if self.transcriber:
            self.transcriber.generate_summary()
            self.body_stack.setCurrentIndex(1)
            self.summary_text_lbl.setText("*Synthesizing executive summary and extracting action items via AI...*")

    def _on_summary_ready(self, summary: MeetingSummary) -> None:
        self.summary_text_lbl.setText(summary.markdown_full)
        self.body_stack.setCurrentIndex(1)

    def _copy_for_claude(self) -> None:
        """Copy formatted meta-prompt tailored for Claude."""
        if not self.transcriber or not self.transcriber.current_session:
            return
        prompt = self.transcriber.current_session.generate_claude_prompt()
        pyperclip.copy(prompt)
        self.claude_btn.setText("Copied!")
        self.claude_btn.setIcon(render_svg_icon(SVG_CHECK, 12, color="#10B981"))
        QTimer.singleShot(
            2500,
            lambda: (
                self.claude_btn.setText("Claude"),
                self.claude_btn.setIcon(render_svg_icon(SVG_COPY, 12, color="#18181B")),
            ),
        )

    def _open_more_menu(self) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #FFFFFF;
                border: 1px solid #E5E3DC;
                border-radius: 10px;
                padding: 4px;
            }
            QMenu::item {
                padding: 6px 16px;
                border-radius: 6px;
                color: #18181B;
                font-size: 11.5px;
            }
            QMenu::item:selected {
                background-color: #F4F3EE;
            }
        """)

        act_copy_clean = menu.addAction(render_svg_icon(SVG_COPY, 13, color="#52525B"), "Copy Plain Transcript")
        act_copy_summary = menu.addAction(render_svg_icon(SVG_SPARKLE, 13, color="#52525B"), "Copy AI Summary")
        act_export_md = menu.addAction(render_svg_icon(SVG_DOWNLOAD, 13, color="#52525B"), "Export Markdown (.md)")
        act_clear = menu.addAction(render_svg_icon(SVG_REFRESH, 13, color="#EF4444"), "Clear Transcript")

        action = menu.exec(self.more_btn.mapToGlobal(QPoint(0, self.more_btn.height() + 4)))
        if not self.transcriber or not self.transcriber.current_session:
            return

        sess = self.transcriber.current_session
        if action == act_copy_clean:
            pyperclip.copy(sess.generate_clean_transcript_text())
        elif action == act_copy_summary:
            if sess.summary:
                pyperclip.copy(sess.summary.markdown_full)
        elif action == act_export_md:
            path, _ = QFileDialog.getSaveFileName(self, "Export Meeting Notes", f"{sess.session_id}.md", "Markdown Files (*.md)")
            if path:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(sess.storage.render_session_markdown(sess) if hasattr(sess, 'storage') else sess.generate_clean_transcript_text())
        elif action == act_clear:
            self._clear_transcript()

    def _clear_transcript(self) -> None:
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()
        self.empty_label.setVisible(True)
        if self.transcriber and self.transcriber.current_session:
            self.transcriber.current_session.turns.clear()
