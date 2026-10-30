"""Floating Voice Control Bar for Vyoma Handless.

A minimal, elegant, cream-styled draggable overlay window featuring a microphone
toggle, live transcription display, action status indicator, and emergency stop.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from PySide6.QtCore import QPoint, Qt, QTimer, Signal
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from handless.safety.emergency_stop import emergency_stop
from .styles import VOICE_BAR_QSS

logger = logging.getLogger(__name__)


class VoiceBar(QWidget):
    """Frameless floating voice control bar."""

    # Thread-safe Qt signals
    transcript_updated = Signal(str)
    status_updated = Signal(str)
    listening_changed = Signal(bool)
    dictation_changed = Signal(bool)

    def __init__(
        self,
        on_mic_toggled: Optional[Callable[[bool], None]] = None,
        on_open_settings: Optional[Callable[[], None]] = None,
        on_emergency_stop: Optional[Callable[[], None]] = None,
        on_command_submitted: Optional[Callable[[str], None]] = None,
        on_dictation_toggled: Optional[Callable[[bool], None]] = None,
    ) -> None:
        super().__init__()
        self.on_mic_toggled = on_mic_toggled
        self.on_open_settings = on_open_settings
        self.on_emergency_stop = on_emergency_stop
        self.on_command_submitted = on_command_submitted
        self.on_dictation_toggled = on_dictation_toggled

        self._drag_pos = QPoint()
        self._is_listening = False
        self._is_dictation = False

        self._setup_window_flags()
        self._init_ui()
        self._connect_signals()

    def _setup_window_flags(self) -> None:
        """Configure as frameless, translucent, always-on-top window with taskbar presence."""
        self.setWindowTitle("Vyoma Handless — Voice & Command Studio")
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setStyleSheet(VOICE_BAR_QSS)

        # Size and position: top-center by default for maximum visibility
        self.resize(580, 94)
        screen = QApplication.primaryScreen()
        if screen:
            geom = screen.geometry()
            center_x = max(20, (geom.width() - 580) // 2)
            self.move(center_x, 50)

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Rounded Container with warm drop shadow
        self.container = QWidget(self)
        self.container.setObjectName("voiceBarContainer")

        shadow = QGraphicsDropShadowEffect(self)
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(44, 36, 24, 40))
        shadow.setOffset(0, 4)
        self.container.setGraphicsEffect(shadow)

        container_layout = QHBoxLayout(self.container)
        container_layout.setContentsMargins(14, 10, 14, 10)
        container_layout.setSpacing(10)

        # 1. Microphone Toggle Button
        self.mic_btn = QPushButton("🎙️", self.container)
        self.mic_btn.setObjectName("micButton")
        self.mic_btn.setFixedSize(44, 44)
        self.mic_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mic_btn.clicked.connect(self._handle_mic_click)
        container_layout.addWidget(self.mic_btn)

        # 2. Text Column (Transcript / Input + Action Status)
        text_layout = QVBoxLayout()
        text_layout.setSpacing(3)
        text_layout.setContentsMargins(0, 0, 0, 0)

        self.cmd_input = QLineEdit(self.container)
        self.cmd_input.setObjectName("cmdInput")
        self.cmd_input.setPlaceholderText("Speak (Ctrl+Space) or type command & press Enter...")
        self.cmd_input.returnPressed.connect(self._handle_cmd_enter)
        text_layout.addWidget(self.cmd_input)

        status_row = QHBoxLayout()
        status_row.setSpacing(8)

        self.transcript_label = QLabel("Hold Ctrl+Space to speak", self.container)
        self.transcript_label.setObjectName("transcriptLabel")
        status_row.addWidget(self.transcript_label, stretch=1)

        self.status_label = QLabel("Ready", self.container)
        self.status_label.setObjectName("statusLabel")
        status_row.addWidget(self.status_label)

        text_layout.addLayout(status_row)
        container_layout.addLayout(text_layout, stretch=1)

        # 3. Mode Toggle Pill: Command vs Dictation
        self.mode_btn = QPushButton("🎤 Command", self.container)
        self.mode_btn.setObjectName("modeButton")
        self.mode_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.mode_btn.setToolTip("Click to toggle between Command Mode and Dictation Mode (Ctrl+Alt+D)")
        self.mode_btn.clicked.connect(self._handle_mode_click)
        container_layout.addWidget(self.mode_btn)

        # 4. Emergency Stop Button
        self.stop_btn = QPushButton("⛔ Stop", self.container)
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.clicked.connect(self._handle_stop_click)
        container_layout.addWidget(self.stop_btn)

        # 5. Settings Gear Button
        self.settings_btn = QPushButton("⚙", self.container)
        self.settings_btn.setObjectName("iconButton")
        self.settings_btn.setFixedSize(28, 28)
        self.settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.settings_btn.clicked.connect(self._handle_settings_click)
        container_layout.addWidget(self.settings_btn)

        # 6. Hide / Minimize Button
        self.close_btn = QPushButton("✕", self.container)
        self.close_btn.setObjectName("iconButton")
        self.close_btn.setFixedSize(28, 28)
        self.close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.close_btn.clicked.connect(self.hide)
        container_layout.addWidget(self.close_btn)

        outer_layout.addWidget(self.container)

    def _connect_signals(self) -> None:
        self.transcript_updated.connect(self._set_transcript_text)
        self.status_updated.connect(self._set_status_text)
        self.listening_changed.connect(self._set_listening_ui)
        self.dictation_changed.connect(self._set_dictation_ui)

    def _handle_mode_click(self) -> None:
        new_state = not self._is_dictation
        self.set_dictation_mode(new_state)
        if self.on_dictation_toggled:
            self.on_dictation_toggled(new_state)

    def set_dictation_mode(self, enabled: bool) -> None:
        self.dictation_changed.emit(enabled)

    def _set_dictation_ui(self, enabled: bool) -> None:
        self._is_dictation = enabled
        self.mode_btn.setText("✍️ Dictation" if enabled else "🎤 Command")
        self.mode_btn.setProperty("dictation", "true" if enabled else "false")
        self.mode_btn.style().unpolish(self.mode_btn)
        self.mode_btn.style().polish(self.mode_btn)

        self.container.setProperty("dictation", "true" if enabled else "false")
        self.container.style().unpolish(self.container)
        self.container.style().polish(self.container)

        if enabled:
            self.cmd_input.setPlaceholderText("Dictation Mode active: Speak to paste text directly into active app...")
            self.transcript_label.setText("Dictation mode (Ctrl+Alt+D to switch)")
            self.status_label.setText("✍️ Dictating")
        else:
            self.cmd_input.setPlaceholderText("Speak (Ctrl+Space) or type command & press Enter...")
            self.transcript_label.setText("Hold Ctrl+Space to speak")
            self.status_label.setText("Ready")

    def _handle_mic_click(self) -> None:
        new_state = not self._is_listening
        self.set_listening(new_state)
        if self.on_mic_toggled:
            self.on_mic_toggled(new_state)

    def _handle_stop_click(self) -> None:
        if emergency_stop.is_stopped():
            emergency_stop.reset()
            self.stop_btn.setText("⛔ Stop")
            self.set_status("Ready ✓")
            self.set_transcript("Controls resumed")
        else:
            emergency_stop.trigger(reason="Voice Bar Stop Button")
            self.stop_btn.setText("▶ Resume")
            self.set_status("⛔ Stopped")
            if self.on_emergency_stop:
                self.on_emergency_stop()

    def _handle_settings_click(self) -> None:
        if self.on_open_settings:
            self.on_open_settings()

    def set_listening(self, active: bool) -> None:
        if active and emergency_stop.is_stopped():
            emergency_stop.reset()
            self.stop_btn.setText("⛔ Stop")
        self.listening_changed.emit(active)

    def set_transcript(self, text: str) -> None:
        self.transcript_updated.emit(text)

    def set_status(self, text: str) -> None:
        self.status_updated.emit(text)

    def _set_listening_ui(self, active: bool) -> None:
        self._is_listening = active
        self.mic_btn.setProperty("listening", "true" if active else "false")
        self.mic_btn.style().unpolish(self.mic_btn)
        self.mic_btn.style().polish(self.mic_btn)

        if active:
            self.status_label.setText("Listening...")
            self.transcript_label.setText("...")
        else:
            if self.status_label.text() == "Listening...":
                self.status_label.setText("Processing...")

    def _handle_cmd_enter(self) -> None:
        text = self.cmd_input.text().strip()
        if text:
            if emergency_stop.is_stopped():
                emergency_stop.reset()
                self.stop_btn.setText("⛔ Stop")
            self.set_status("Processing command...")
            if self.on_command_submitted:
                self.on_command_submitted(text)

    def _set_transcript_text(self, text: str) -> None:
        self.transcript_label.setText(text)
        if text:
            self.cmd_input.setText(text)

    def _set_status_text(self, text: str) -> None:
        self.status_label.setText(text)
        # If success message, reset to ready after 2.5s
        if "Done" in text or "✓" in text or "Success" in text:
            QTimer.singleShot(2500, self._reset_to_ready)

    def _reset_to_ready(self) -> None:
        if not self._is_listening:
            self.status_label.setText("✍️ Dictating" if self._is_dictation else "Ready")
            if not emergency_stop.is_stopped():
                self.stop_btn.setText("⛔ Stop")

    # Draggable Frameless Window Handlers
    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton:
            self.move(event.globalPosition().toPoint() - self._drag_pos)
            event.accept()
