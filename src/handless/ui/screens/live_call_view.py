"""Live Call Screen View with Dotted Fluid Orb and Gemini 3.8 Live Integration.

Provides a full-duplex conversational voice call interface featuring:
- Minimalist Dotted Fluid Orb particle matrix in Handless aesthetic.
- Instant model toggle (Gemini 3.8 Live vs Gemini 3.8 Live Extended Thinking).
- Real-time subtitle feed and tool execution activity banner.
- Mute, Screen Vision, and End Call controls.
"""

from __future__ import annotations

import math
import time
from typing import Optional

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen, QRadialGradient
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from handless.ui.icons import (
    SVG_EYE,
    SVG_MIC,
    SVG_MIC_OFF,
    SVG_PHONE_OFF,
    SVG_SPARKLE,
    render_svg_icon,
    render_svg_pixmap,
)
from handless.ui.thinking_orbs import ThinkingOrbWidget
from handless.voice.gemini_live import (
    MODEL_GEMINI_LIVE,
    MODEL_GEMINI_LIVE_THINKING,
    GeminiLiveSession,
)


class DottedFluidOrbWidget(ThinkingOrbWidget):
    """Thinking-orbs powered Dotted Particle Orb for Live Voice Call AI Core.

    Faithfully implements the 9 geometric modes from Jakub Antalik's thinking-orbs,
    rendering 3D dotted thought-orbs in Handless's signature charcoal & emerald palette.
    """

    def __init__(self, size: int = 170, parent: Optional[QWidget] = None) -> None:
        super().__init__(size=size, state="listening", theme="handless", parent=parent)
        self._target_level = 0.0
        self._is_live = True
        self._is_speaking = False
        self._is_thinking = False

    def set_level(self, level: float) -> None:
        """Set smooth live audio amplitude (0.0 to 1.0)."""
        self._target_level = max(0.0, min(1.0, level))
        super().set_level(level)

    def set_state(self, is_live: bool, is_speaking: bool, is_thinking: bool) -> None:
        """Update active speaking and thinking states."""
        self._is_live = is_live
        self._is_speaking = is_speaking
        self._is_thinking = is_thinking
        if is_thinking:
            super().set_state("solving")
        elif is_speaking:
            super().set_state("composing")
        elif is_live:
            super().set_state("listening")
        else:
            super().set_state("breathing")
        self.update()

    def set_agent_state(self, state: str) -> None:
        """Directly set any of the 9 thinking-orb states."""
        super().set_state(state)


class LiveCallScreenView(QWidget):
    """Full-featured Live Call screen inside Handless Copilot Sidebar."""

    call_ended_requested = Signal()
    model_switch_requested = Signal(str)
    mute_toggled = Signal(bool)
    inspect_screen_requested = Signal()

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setObjectName("liveCallScreenView")
        self._call_start_time = 0.0
        self._current_model = MODEL_GEMINI_LIVE
        self._is_muted = False
        self._is_speaking = False

        self._duration_timer = QTimer(self)
        self._duration_timer.timeout.connect(self._update_call_duration)

        self._init_ui()

    def minimumSizeHint(self) -> QSize:
        return QSize(220, 320)

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 14, 16, 14)
        layout.setSpacing(12)

        # 1. Top Bar: Live Call Badge + Duration + Model Switcher Pill
        top_row = QHBoxLayout()
        top_row.setContentsMargins(0, 0, 0, 0)
        top_row.setSpacing(8)

        # Live status badge
        self.badge_widget = QWidget(self)
        self.badge_widget.setObjectName("readyStatusPill")
        b_layout = QHBoxLayout(self.badge_widget)
        b_layout.setContentsMargins(8, 4, 8, 4)
        b_layout.setSpacing(6)

        self.badge_dot = QLabel("●", self.badge_widget)
        self.badge_dot.setStyleSheet("color: #10B981; font-size: 11px;")
        b_layout.addWidget(self.badge_dot)

        self.badge_text = QLabel("Live Call", self.badge_widget)
        self.badge_text.setStyleSheet("color: #18181B; font-weight: 700; font-size: 11.5px;")
        b_layout.addWidget(self.badge_text)

        self.time_label = QLabel("00:00", self.badge_widget)
        self.time_label.setStyleSheet("color: #71717A; font-weight: 500; font-size: 11px;")
        b_layout.addWidget(self.time_label)

        top_row.addWidget(self.badge_widget)
        top_row.addStretch(1)

        # Model Toggle Button
        self.model_pill = QPushButton(self)
        self.model_pill.setObjectName("liveModelPill")
        self.model_pill.setCursor(Qt.CursorShape.PointingHandCursor)
        self.model_pill.setText("⚡ Gemini 3.8 Live")
        self.model_pill.setToolTip("Click to toggle: Gemini 3.8 Live ⇄ Gemini 3.8 Live Extended Thinking")
        self.model_pill.setStyleSheet("""
            QPushButton#liveModelPill {
                background-color: #F4F3EE;
                border: 1px solid #E5E3DC;
                border-radius: 12px;
                padding: 4px 10px;
                color: #18181B;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton#liveModelPill:hover {
                background-color: #ECEAE3;
            }
        """)
        self.model_pill.clicked.connect(self._toggle_model)
        top_row.addWidget(self.model_pill)

        layout.addLayout(top_row)

        # 2. Main Center Body: Dotted Fluid Orb + Status Indicator
        center_container = QWidget(self)
        center_layout = QVBoxLayout(center_container)
        center_layout.setContentsMargins(0, 10, 0, 8)
        center_layout.setSpacing(8)
        center_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.dotted_orb = DottedFluidOrbWidget(size=170, parent=center_container)
        center_layout.addWidget(self.dotted_orb, alignment=Qt.AlignmentFlag.AlignCenter)

        self.status_title = QLabel("Listening...", center_container)
        self.status_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_title.setStyleSheet("""
            color: #18181B;
            font-size: 15px;
            font-weight: 700;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        center_layout.addWidget(self.status_title)

        self.status_sub = QLabel("Speak naturally — Gemini Live is listening", center_container)
        self.status_sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_sub.setWordWrap(True)
        self.status_sub.setStyleSheet("""
            color: #71717A;
            font-size: 11.5px;
            font-weight: 400;
        """)
        center_layout.addWidget(self.status_sub)

        layout.addWidget(center_container)

        # 3. Live Tool Activity Banner
        self.tool_banner = QFrame(self)
        self.tool_banner.setObjectName("liveToolBanner")
        self.tool_banner.setVisible(False)
        self.tool_banner.setStyleSheet("""
            QFrame#liveToolBanner {
                background-color: #F0FDF4;
                border: 1px solid #BBF7D0;
                border-radius: 10px;
                padding: 6px 12px;
            }
        """)
        tb_layout = QHBoxLayout(self.tool_banner)
        tb_layout.setContentsMargins(8, 4, 8, 4)
        tb_layout.setSpacing(6)

        self.tool_icon = QLabel("⚡", self.tool_banner)
        self.tool_icon.setStyleSheet("color: #10B981; font-weight: bold; font-size: 12px;")
        tb_layout.addWidget(self.tool_icon)

        self.tool_text = QLabel("Executing action...", self.tool_banner)
        self.tool_text.setStyleSheet("color: #15803D; font-size: 11.5px; font-weight: 600;")
        tb_layout.addWidget(self.tool_text, stretch=1)
        layout.addWidget(self.tool_banner)

        # 4. Transcript & Response Subtitle Card
        transcript_box = QFrame(self)
        transcript_box.setObjectName("liveTranscriptCard")
        transcript_box.setStyleSheet("""
            QFrame#liveTranscriptCard {
                background-color: #FFFFFF;
                border: 1px solid #EFECE6;
                border-radius: 14px;
            }
        """)
        t_layout = QVBoxLayout(transcript_box)
        t_layout.setContentsMargins(14, 12, 14, 12)
        t_layout.setSpacing(6)

        t_header = QLabel("LIVE TRANSCRIPT", transcript_box)
        t_header.setStyleSheet("""
            color: #A1A1AA;
            font-size: 9.5px;
            font-weight: 700;
            letter-spacing: 0.5px;
            background: transparent;
            border: none;
        """)
        t_layout.addWidget(t_header)

        self.transcript_label = QLabel("Speak to Gemini Live or ask it to control desktop apps...", transcript_box)
        self.transcript_label.setWordWrap(True)
        self.transcript_label.setStyleSheet("""
            color: #27272A;
            font-size: 13px;
            line-height: 1.45;
            background: transparent;
            border: none;
            font-family: 'Segoe UI', -apple-system, sans-serif;
        """)
        t_layout.addWidget(self.transcript_label)
        t_layout.addStretch(1)

        layout.addWidget(transcript_box, stretch=1)

        # 5. Bottom Action Controls (Mute, Look at Screen, End Call)
        bottom_row = QHBoxLayout()
        bottom_row.setContentsMargins(0, 4, 0, 0)
        bottom_row.setSpacing(10)

        # Mic Mute Button
        self.mute_btn = QPushButton(self)
        self.mute_btn.setObjectName("liveCallControlBtn")
        self.mute_btn.setIcon(render_svg_icon(SVG_MIC, 16, color="#18181B"))
        self.mute_btn.setIconSize(QSize(16, 16))
        self.mute_btn.setFixedSize(36, 36)
        self.mute_btn.setToolTip("Mute / Unmute Microphone")
        self.mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mute_btn.setStyleSheet("""
            QPushButton#liveCallControlBtn {
                background-color: #F4F3EE;
                border: 1px solid #E5E3DC;
                border-radius: 18px;
            }
            QPushButton#liveCallControlBtn:hover {
                background-color: #ECEAE3;
            }
        """)
        self.mute_btn.clicked.connect(self._on_mute_clicked)
        bottom_row.addWidget(self.mute_btn)

        # Look at Screen Vision Button
        self.vision_btn = QPushButton(self)
        self.vision_btn.setObjectName("liveCallControlBtn")
        self.vision_btn.setIcon(render_svg_icon(SVG_EYE, 16, color="#18181B"))
        self.vision_btn.setIconSize(QSize(16, 16))
        self.vision_btn.setFixedSize(36, 36)
        self.vision_btn.setToolTip("Inspect Screen Content")
        self.vision_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.vision_btn.setStyleSheet("""
            QPushButton#liveCallControlBtn {
                background-color: #F4F3EE;
                border: 1px solid #E5E3DC;
                border-radius: 18px;
            }
            QPushButton#liveCallControlBtn:hover {
                background-color: #ECEAE3;
            }
        """)
        self.vision_btn.clicked.connect(self.inspect_screen_requested.emit)
        bottom_row.addWidget(self.vision_btn)

        bottom_row.addStretch(1)

        # Red End Call Pill Button
        self.end_call_btn = QPushButton(self)
        self.end_call_btn.setObjectName("endCallPillBtn")
        self.end_call_btn.setIcon(render_svg_icon(SVG_PHONE_OFF, 16, color="#FFFFFF"))
        self.end_call_btn.setIconSize(QSize(16, 16))
        self.end_call_btn.setText("End Call")
        self.end_call_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.end_call_btn.setFixedHeight(36)
        self.end_call_btn.setStyleSheet("""
            QPushButton#endCallPillBtn {
                background-color: #EF4444;
                color: #FFFFFF;
                font-weight: 700;
                font-size: 12px;
                border: none;
                border-radius: 18px;
                padding: 0 16px;
            }
            QPushButton#endCallPillBtn:hover {
                background-color: #DC2626;
            }
            QPushButton#endCallPillBtn:pressed {
                background-color: #B91C1C;
            }
        """)
        self.end_call_btn.clicked.connect(self.call_ended_requested.emit)
        bottom_row.addWidget(self.end_call_btn)

        layout.addLayout(bottom_row)

    def start_call_timer(self) -> None:
        """Start the call duration clock."""
        self._call_start_time = time.time()
        self._duration_timer.start(1000)
        self.time_label.setText("00:00")
        self.badge_dot.setStyleSheet("color: #10B981; font-size: 11px;")
        self.status_title.setText("Listening...")
        self.status_sub.setText("Speak naturally — Gemini Live is listening")
        self.tool_banner.setVisible(False)

    def stop_call_timer(self) -> None:
        """Stop call clock and reset UI."""
        self._duration_timer.stop()
        self.dotted_orb.set_level(0.0)
        self.dotted_orb.set_state(is_live=False, is_speaking=False, is_thinking=False)
        self.badge_dot.setStyleSheet("color: #71717A; font-size: 11px;")

    def _update_call_duration(self) -> None:
        if self._call_start_time <= 0:
            return
        elapsed = int(time.time() - self._call_start_time)
        mins = elapsed // 60
        secs = elapsed % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

    def _toggle_model(self) -> None:
        if self._current_model == MODEL_GEMINI_LIVE:
            new_model = MODEL_GEMINI_LIVE_THINKING
            self.model_pill.setText("🧠 Extended Thinking")
        else:
            new_model = MODEL_GEMINI_LIVE
            self.model_pill.setText("⚡ Gemini 3.8 Live")
        self._current_model = new_model
        self.model_switch_requested.emit(new_model)

    def _on_mute_clicked(self) -> None:
        self._is_muted = not self._is_muted
        if self._is_muted:
            self.mute_btn.setIcon(render_svg_icon(SVG_MIC_OFF, 16, color="#EF4444"))
            self.mute_btn.setToolTip("Unmute Microphone")
            self.status_title.setText("Microphone Muted")
            self.status_sub.setText("Tap the mic button to speak")
        else:
            self.mute_btn.setIcon(render_svg_icon(SVG_MIC, 16, color="#18181B"))
            self.mute_btn.setToolTip("Mute Microphone")
            self.status_title.setText("Listening...")
            self.status_sub.setText("Speak naturally — Gemini Live is listening")
        self.mute_toggled.emit(self._is_muted)

    def update_audio_level(self, level: float) -> None:
        """Forward live audio level to dotted fluid orb."""
        self.dotted_orb.set_level(level)

    def set_speaking_state(self, is_speaking: bool) -> None:
        """Update speaking state indicator."""
        self._is_speaking = is_speaking
        is_thinking = (self._current_model == MODEL_GEMINI_LIVE_THINKING and not is_speaking)
        self.dotted_orb.set_state(is_live=True, is_speaking=is_speaking, is_thinking=is_thinking)
        if is_speaking:
            self.status_title.setText("Speaking...")
            self.status_sub.setText("Gemini Live is talking")
        elif not self._is_muted:
            self.status_title.setText("Listening...")
            self.status_sub.setText("Speak naturally — Gemini Live is listening")

    def set_transcript_text(self, text: str, is_thought: bool = False) -> None:
        """Display live speech transcript or model thoughts."""
        if is_thought:
            self.status_title.setText("Thinking deeply...")
            self.status_sub.setText("Gemini Extended Thinking is reasoning...")
            self.transcript_label.setText(f"💭 {text}")
        else:
            self.transcript_label.setText(text)

    def show_tool_activity(self, tool_name: str, status: str, details: str) -> None:
        """Display live tool execution feedback."""
        clean_name = tool_name.replace("_", " ").title()
        if status == "running":
            if tool_name == "inspect_screen":
                self.dotted_orb.set_agent_state("searching")
            else:
                self.dotted_orb.set_agent_state("working")
            self.tool_banner.setStyleSheet("""
                QFrame#liveToolBanner {
                    background-color: #FEF3C7;
                    border: 1px solid #FCD34D;
                    border-radius: 10px;
                    padding: 6px 12px;
                }
            """)
            self.tool_icon.setText("⚙️")
            self.tool_icon.setStyleSheet("color: #D97706; font-size: 12px;")
            self.tool_text.setText(f"Executing: {clean_name}...")
            self.tool_text.setStyleSheet("color: #B45309; font-size: 11.5px; font-weight: 600;")
            self.tool_banner.setVisible(True)
        elif status == "done":
            self.tool_banner.setStyleSheet("""
                QFrame#liveToolBanner {
                    background-color: #F0FDF4;
                    border: 1px solid #BBF7D0;
                    border-radius: 10px;
                    padding: 6px 12px;
                }
            """)
            self.tool_icon.setText("✓")
            self.tool_icon.setStyleSheet("color: #10B981; font-size: 12px;")
            self.tool_text.setText(f"Done: {details}")
            self.tool_text.setStyleSheet("color: #15803D; font-size: 11.5px; font-weight: 600;")
            self.tool_banner.setVisible(True)
            self._restore_orb_after_tool()
            QTimer.singleShot(4000, lambda: self.tool_banner.setVisible(False))
        elif status == "error":
            is_session_closed = "closed" in details.lower() or "ended" in details.lower() or "stopped" in details.lower()
            if is_session_closed:
                self.tool_banner.setStyleSheet("""
                    QFrame#liveToolBanner {
                        background-color: #F4F3EE;
                        border: 1px solid #ECE7DC;
                        border-radius: 10px;
                        padding: 6px 12px;
                    }
                """)
                self.tool_icon.setText("ℹ️")
                self.tool_icon.setStyleSheet("color: #71717A; font-size: 12px;")
                self.tool_text.setText(details)
                self.tool_text.setStyleSheet("color: #52525B; font-size: 11.5px; font-weight: 500;")
            else:
                self.tool_banner.setStyleSheet("""
                    QFrame#liveToolBanner {
                        background-color: #FEF2F2;
                        border: 1px solid #FECACA;
                        border-radius: 10px;
                        padding: 6px 12px;
                    }
                """)
                self.tool_icon.setText("⚠️")
                self.tool_icon.setStyleSheet("color: #EF4444; font-size: 12px;")
                self.tool_text.setText(f"Error: {details}")
                self.tool_text.setStyleSheet("color: #B91C1C; font-size: 11.5px; font-weight: 600;")
            self.tool_banner.setVisible(True)
            self._restore_orb_after_tool()
            QTimer.singleShot(4500, lambda: self.tool_banner.setVisible(False))

    def _restore_orb_after_tool(self) -> None:
        if self._is_speaking:
            self.dotted_orb.set_state(is_live=True, is_speaking=True, is_thinking=False)
        elif self._current_model == MODEL_GEMINI_LIVE_THINKING:
            self.dotted_orb.set_state(is_live=True, is_speaking=False, is_thinking=True)
        else:
            self.dotted_orb.set_state(is_live=True, is_speaking=False, is_thinking=False)

