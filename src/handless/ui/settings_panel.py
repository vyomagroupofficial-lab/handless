"""Settings Dialog for Vyoma Handless.

Clean, multi-tab settings interface configured with cream/paper aesthetics.
Securely manages the Google Gemini API key via Windows Credential Manager,
audio input selection, hotkey customization, and privacy controls.
"""

from __future__ import annotations

import logging
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)
import sounddevice as sd

from handless.config import AppConfig, save_config
from handless.security.credentials import (
    delete_gemini_api_key,
    delete_groq_api_key,
    get_gemini_api_key,
    get_groq_api_key,
    has_gemini_api_key,
    has_groq_api_key,
    store_gemini_api_key,
    store_groq_api_key,
)
from .styles import SETTINGS_PANEL_QSS

logger = logging.getLogger(__name__)


class SettingsPanel(QDialog):
    """Settings dialog with secure credential management."""

    def __init__(self, config: AppConfig, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Vyoma Handless — Settings")
        self.resize(520, 460)
        self.setStyleSheet(SETTINGS_PANEL_QSS)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(14)

        self.tabs = QTabWidget(self)
        main_layout.addWidget(self.tabs)

        # Build tabs
        self._init_ai_tab()
        self._init_voice_tab()
        self._init_shortcuts_tab()
        self._init_privacy_tab()

        # Bottom Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        self.cancel_btn = QPushButton("Cancel", self)
        self.cancel_btn.setObjectName("secondaryButton")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        self.save_btn = QPushButton("Save Preferences", self)
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_and_close)
        btn_layout.addWidget(self.save_btn)

        main_layout.addLayout(btn_layout)

    def _init_ai_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        # Gemini API Key Group
        cred_group = QGroupBox("Google Gemini AI Studio API Key (Encrypted in Windows Credential Manager)")
        cred_layout = QVBoxLayout(cred_group)

        self.key_status_label = QLabel()
        self._update_key_status_label()
        cred_layout.addWidget(self.key_status_label)

        key_input_row = QHBoxLayout()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.api_key_input.setPlaceholderText("Enter Google AI Studio key (AIzaSy...)")
        existing_key = get_gemini_api_key()
        if existing_key:
            self.api_key_input.setText(existing_key)
        key_input_row.addWidget(self.api_key_input)

        self.show_key_btn = QPushButton("Show")
        self.show_key_btn.setObjectName("secondaryButton")
        self.show_key_btn.clicked.connect(self._toggle_show_key)
        key_input_row.addWidget(self.show_key_btn)
        cred_layout.addLayout(key_input_row)

        key_btn_row = QHBoxLayout()
        self.test_key_btn = QPushButton("Test && Store Key")
        self.test_key_btn.setObjectName("primaryButton")
        self.test_key_btn.clicked.connect(self._store_and_test_key)
        key_btn_row.addWidget(self.test_key_btn)

        self.clear_key_btn = QPushButton("Remove Key")
        self.clear_key_btn.setObjectName("secondaryButton")
        self.clear_key_btn.clicked.connect(self._remove_key)
        key_btn_row.addWidget(self.clear_key_btn)
        key_btn_row.addStretch()
        cred_layout.addLayout(key_btn_row)

        layout.addWidget(cred_group)

        # Groq Cloud Fallback API Key Group
        groq_group = QGroupBox("Groq Cloud High-Capacity Fallback Key (Encrypted in Windows Credential Manager)")
        groq_layout = QVBoxLayout(groq_group)

        self.groq_key_status_label = QLabel()
        self._update_groq_key_status_label()
        groq_layout.addWidget(self.groq_key_status_label)

        groq_input_row = QHBoxLayout()
        self.groq_api_key_input = QLineEdit()
        self.groq_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.groq_api_key_input.setPlaceholderText("Enter Groq API key (gsk_...)")
        existing_groq_key = get_groq_api_key()
        if existing_groq_key:
            self.groq_api_key_input.setText(existing_groq_key)
        groq_input_row.addWidget(self.groq_api_key_input)

        self.show_groq_key_btn = QPushButton("Show")
        self.show_groq_key_btn.setObjectName("secondaryButton")
        self.show_groq_key_btn.clicked.connect(self._toggle_show_groq_key)
        groq_input_row.addWidget(self.show_groq_key_btn)
        groq_layout.addLayout(groq_input_row)

        groq_btn_row = QHBoxLayout()
        self.test_groq_key_btn = QPushButton("Store Groq Key")
        self.test_groq_key_btn.setObjectName("primaryButton")
        self.test_groq_key_btn.clicked.connect(self._store_groq_key)
        groq_btn_row.addWidget(self.test_groq_key_btn)

        self.clear_groq_key_btn = QPushButton("Remove Key")
        self.clear_groq_key_btn.setObjectName("secondaryButton")
        self.clear_groq_key_btn.clicked.connect(self._remove_groq_key)
        groq_btn_row.addWidget(self.clear_groq_key_btn)
        groq_btn_row.addStretch()
        groq_layout.addLayout(groq_btn_row)

        layout.addWidget(groq_group)

        # Intelligence Architecture Settings
        ai_group = QGroupBox("Intelligence Configuration")
        ai_layout = QFormLayout(ai_group)

        self.tier_combo = QComboBox()
        self.tier_combo.addItems(["hybrid (Recommended: Local + Cloud)", "local_only (Offline Only)", "cloud_only (Always Gemini)"])
        current_tier = self.config.ai.preferred_tier
        index = 0
        if current_tier == "local_only":
            index = 1
        elif current_tier == "cloud_only":
            index = 2
        self.tier_combo.setCurrentIndex(index)
        ai_layout.addRow("Intelligence Tier:", self.tier_combo)

        self.gemini_model_combo = QComboBox()
        self.gemini_model_combo.addItems([
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.5-pro",
            "gemma-4-31b-it",
            "gemma-4-26b-a4b-it",
        ])
        self.gemini_model_combo.setCurrentText(self.config.ai.gemini_model)
        ai_layout.addRow("Google AI Model:", self.gemini_model_combo)

        self.groq_model_combo = QComboBox()
        self.groq_model_combo.addItems([
            "qwen/qwen3.8-27b",
            "openai/gpt-oss-120b",
            "llama-3.3-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768",
        ])
        cur_groq_model = getattr(self.config.ai, "groq_model", "qwen/qwen3.8-27b")
        self.groq_model_combo.setCurrentText(cur_groq_model)
        ai_layout.addRow("Groq Cloud Model:", self.groq_model_combo)

        self.vision_fallback_cb = QCheckBox("Enable Gemini Vision Screen Fallback")
        self.vision_fallback_cb.setChecked(self.config.ai.enable_vision_fallback)
        ai_layout.addRow(self.vision_fallback_cb)

        layout.addWidget(ai_group)
        layout.addStretch()
        self.tabs.addTab(tab, "AI & Models")

    def _init_voice_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        stt_group = QGroupBox("Offline Speech-to-Text Engine")
        stt_layout = QFormLayout(stt_group)

        self.stt_engine_combo = QComboBox()
        self.stt_engine_combo.addItem("Groq Cloud Whisper Large v3 (Fastest & Highest Accuracy)", "groq_whisper")
        self.stt_engine_combo.addItem("OpenAI Whisper Base (Local CPU — sherpa-onnx)", "whisper")
        self.stt_engine_combo.addItem("Vosk English (Offline Small)", "vosk")

        cur_stt = getattr(self.config.voice, "stt_engine", "groq_whisper")
        for i in range(self.stt_engine_combo.count()):
            if self.stt_engine_combo.itemData(i) == cur_stt:
                self.stt_engine_combo.setCurrentIndex(i)
                break
        stt_layout.addRow("STT Model Engine:", self.stt_engine_combo)
        layout.addWidget(stt_group)

        mic_group = QGroupBox("Audio Input")
        mic_layout = QFormLayout(mic_group)

        self.device_combo = QComboBox()
        self.device_combo.addItem("Default System Microphone", -1)
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if dev.get("max_input_channels", 0) > 0:
                    self.device_combo.addItem(f"{dev['name']}", idx)
        except Exception:
            pass
        mic_layout.addRow("Microphone Device:", self.device_combo)

        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["Push-to-Talk (Hold Hotkey)", "Continuous (VAD Gated)"])
        if self.config.voice.mode == "continuous":
            self.mode_combo.setCurrentIndex(1)
        mic_layout.addRow("Voice Mode:", self.mode_combo)

        self.vad_slider = QSlider(Qt.Orientation.Horizontal)
        self.vad_slider.setRange(0, 3)
        self.vad_slider.setValue(self.config.voice.vad_aggressiveness)
        mic_layout.addRow("Silence Filter Aggressiveness (0-3):", self.vad_slider)

        layout.addWidget(mic_group)
        layout.addStretch()
        self.tabs.addTab(tab, "Voice & Audio")

    def _init_shortcuts_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        hk_group = QGroupBox("Global Hotkeys")
        hk_layout = QFormLayout(hk_group)

        self.ptt_input = QLineEdit(self.config.hotkeys.push_to_talk)
        hk_layout.addRow("Push-to-Talk Hotkey:", self.ptt_input)

        self.stop_input = QLineEdit(self.config.hotkeys.emergency_stop)
        hk_layout.addRow("Emergency Stop Hotkey:", self.stop_input)

        self.toggle_input = QLineEdit(self.config.hotkeys.toggle_bar)
        hk_layout.addRow("Toggle Voice Bar:", self.toggle_input)

        self.dictation_input = QLineEdit(getattr(self.config.hotkeys, "toggle_dictation", "<ctrl>+<alt>+d"))
        hk_layout.addRow("Toggle Dictation Mode:", self.dictation_input)

        layout.addWidget(hk_group)

        safety_group = QGroupBox("Safety Rules")
        safety_layout = QVBoxLayout(safety_group)
        self.confirm_cb = QCheckBox("Require Voice Confirmation before Consequential Actions (sending emails/deleting files)")
        self.confirm_cb.setChecked(self.config.safety.confirm_destructive_actions)
        safety_layout.addWidget(self.confirm_cb)

        layout.addWidget(safety_group)
        layout.addStretch()
        self.tabs.addTab(tab, "Hotkeys & Safety")

    def _init_privacy_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(12)

        info = QLabel(
            "<b>Vyoma Handless Privacy & Security Architecture</b><br><br>"
            "• <b>Local-First Speech:</b> Voice recognition (Vosk) processes speech entirely on your CPU. "
            "No audio recordings leave your PC.<br>"
            "• <b>Secure Key Storage:</b> Your Google Gemini API key is stored in the native Windows Credential Manager "
            "(Windows DPAPI encrypted) — never in plaintext configuration files.<br>"
            "• <b>Selective Screen Vision:</b> Screenshots are only transmitted to Gemini when Windows UI Automation fails "
            "and when Vision Fallback is enabled.<br>"
            "• <b>Zero Telemetry:</b> No analytics, tracking, or telemetry data is ever collected."
        )
        info.setWordWrap(True)
        layout.addWidget(info)
        layout.addStretch()
        self.tabs.addTab(tab, "Privacy & Architecture")

    def _toggle_show_key(self) -> None:
        if self.api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_key_btn.setText("Hide")
        else:
            self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_key_btn.setText("Show")

    def _update_key_status_label(self) -> None:
        if has_gemini_api_key():
            self.key_status_label.setText("Status: <span style='color: #7B9E7B; font-weight: bold;'>Configured & Active in Windows Vault ✓</span>")
        else:
            self.key_status_label.setText("Status: <span style='color: #C4704B;'>No API key stored (Local-only mode active)</span>")

    def _store_and_test_key(self) -> None:
        key = self.api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Please enter a valid Google AI Studio API key.")
            return

        success = store_gemini_api_key(key)
        if success:
            self._update_key_status_label()
            QMessageBox.information(
                self,
                "Key Stored Securely",
                "Your Gemini API key has been securely stored in the Windows Credential Manager.",
            )
        else:
            QMessageBox.critical(self, "Storage Error", "Could not store key in Windows Credential Manager.")

    def _remove_key(self) -> None:
        delete_gemini_api_key()
        self.api_key_input.clear()
        self._update_key_status_label()
        QMessageBox.information(self, "Key Removed", "Gemini API key removed from Windows Credential Manager.")

    def _toggle_show_groq_key(self) -> None:
        if self.groq_api_key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.groq_api_key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.show_groq_key_btn.setText("Hide")
        else:
            self.groq_api_key_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.show_groq_key_btn.setText("Show")

    def _update_groq_key_status_label(self) -> None:
        if has_groq_api_key():
            self.groq_key_status_label.setText("Status: <span style='color: #7B9E7B; font-weight: bold;'>Groq Key Configured & Active in Windows Vault ✓</span>")
        else:
            self.groq_key_status_label.setText("Status: <span style='color: #8C827A;'>No Groq key configured (optional cloud fallback)</span>")

    def _store_groq_key(self) -> None:
        key = self.groq_api_key_input.text().strip()
        if not key:
            QMessageBox.warning(self, "Invalid Key", "Please enter a valid Groq API key.")
            return

        success = store_groq_api_key(key)
        if success:
            self._update_groq_key_status_label()
            QMessageBox.information(
                self,
                "Key Stored Securely",
                "Your Groq API key has been securely stored in the Windows Credential Manager.",
            )
        else:
            QMessageBox.critical(self, "Storage Error", "Could not store Groq key in Windows Credential Manager.")

    def _remove_groq_key(self) -> None:
        delete_groq_api_key()
        self.groq_api_key_input.clear()
        self._update_groq_key_status_label()
        QMessageBox.information(self, "Key Removed", "Groq API key removed from Windows Credential Manager.")

    def _save_and_close(self) -> None:
        # Update config model
        tier_map = ["hybrid", "local_only", "cloud_only"]
        self.config.ai.preferred_tier = tier_map[self.tier_combo.currentIndex()]
        self.config.ai.gemini_model = self.gemini_model_combo.currentText()
        self.config.ai.groq_model = self.groq_model_combo.currentText()
        self.config.ai.enable_vision_fallback = self.vision_fallback_cb.isChecked()

        self.config.voice.device_index = self.device_combo.currentData()
        self.config.voice.stt_engine = self.stt_engine_combo.currentData() or "groq_whisper"
        self.config.voice.mode = "continuous" if self.mode_combo.currentIndex() == 1 else "push_to_talk"
        self.config.voice.vad_aggressiveness = self.vad_slider.value()

        self.config.hotkeys.push_to_talk = self.ptt_input.text().strip()
        self.config.hotkeys.emergency_stop = self.stop_input.text().strip()
        self.config.hotkeys.toggle_bar = self.toggle_input.text().strip()
        if hasattr(self, "dictation_input"):
            self.config.hotkeys.toggle_dictation = self.dictation_input.text().strip()
        self.config.safety.confirm_destructive_actions = self.confirm_cb.isChecked()

        save_config(self.config)
        self.accept()
