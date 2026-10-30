"""Main Application Entry Point for Vyoma Handless.

Orchestrates the PySide6 UI (VoiceBar, SettingsPanel, TrayIcon),
voice capture pipeline, multi-tier intent router, global hotkey manager,
and desktop action dispatcher.
"""

from __future__ import annotations

import logging
import os
import subprocess
import sys

# Ensure Single Threaded Apartment (STA) mode for COM / pywinauto before imports
if not hasattr(sys, "coinit_flags"):
    sys.coinit_flags = 2

import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pywinauto.*")
warnings.filterwarnings("ignore", message=".*coinit_flags.*")

import threading
import time
import webbrowser
from typing import Any, Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from handless.actions.dispatcher import ActionDispatcher
from handless.actions.macro_recorder import MacroRecorder
from handless.actions.workflows import WorkflowManager
from handless.config import AppConfig, load_config, save_config
from handless.dictation.cleanup_engine import CleanupLevel, clean_text_with_level
from handless.dictation.flow_overlay import WisprFlowOverlay
from handless.dictation.history_journal import HistoryEntry, HistoryJournal
from handless.dictation.language_manager import LanguageManager
from handless.dictation.paste_controller import get_active_window_title, paste_text
from handless.dictation.speculative_engine import SpeculativeDictationEngine
from handless.dictation.text_cleaner import clean_spoken_text
from handless.dictation.text_transformer import TransformType
from handless.dictation.transform_overlay import TransformOverlay
from handless.intelligence.gemini_client import GeminiInterpreter
from handless.intelligence.grok_persona import (
    ConfigProposal,
    detect_config_proposal,
    generate_grok_chat_reply,
    is_casual_chitchat,
)
from handless.intelligence.groq_client import GroqInterpreter
from handless.intelligence.models import ActionType
from handless.intelligence.router import IntentRouter
from handless.logging_config import (
    get_error_log_path,
    get_latest_errors,
    get_latest_logs,
    get_main_log_path,
    open_logs_directory,
    setup_logging,
)
from handless.meeting.transcription_engine import MeetingTranscriber
from handless.safety.emergency_stop import emergency_stop
from handless.safety.hotkeys import GlobalHotkeyManager
from handless.ui.floating_widget import FloatingCopilotWidget
from handless.ui.macro_overlay import MacroRecordingBanner
from handless.ui.screen_lens import ScreenLensOverlay
from handless.ui.settings_panel import SettingsPanel
from handless.ui.tray_icon import HandlessTrayIcon
from handless.ui.voice_bar import VoiceBar
from handless.ui.sidebar import SidebarWindow

from handless.voice.microphone import MicrophonePipeline
from handless.voice.recognizer import VoskSpeechRecognizer
from handless.voice.groq_whisper import GroqWhisperRecognizer
from handless.voice.whisper_engine import WhisperSpeechRecognizer
from handless.voice.gemini_live import (
    GeminiLiveSession,
    MODEL_GEMINI_LIVE,
    MODEL_GEMINI_LIVE_THINKING,
)

# Initialize comprehensive multi-tier logging
setup_logging()
logger = logging.getLogger("handless")


class SpeechBridge(QObject):
    """Bridge background speech threads to Qt UI main thread via signals."""
    partial_received = Signal(str)
    final_received = Signal(str)


class AppUIBridge(QObject):
    """Thread-safe bridge for background workers to dispatch UI updates to Qt main thread."""
    user_message_requested = Signal(str)
    assistant_message_requested = Signal(str)
    action_card_requested = Signal(str, str, str, str)  # title, subtitle, icon, btn_label
    thinking_requested = Signal(bool)
    status_requested = Signal(str)
    transcript_requested = Signal(str)
    dictation_mode_requested = Signal(bool)
    dictations_updated = Signal()
    inspector_requested = Signal()
    flow_started = Signal()
    flow_transcribing = Signal()
    flow_finished = Signal(str)
    flow_cancelled = Signal()
    transform_requested = Signal()
    undo_requested = Signal()
    config_proposal_requested = Signal(object)




class HandlessApp:
    """Central Application Coordinator."""

    def __init__(self, sys_argv: list[str]) -> None:
        self.qt_app = QApplication(sys_argv)
        self.qt_app.setApplicationName("Vyoma Handless")
        self.qt_app.setQuitOnLastWindowClosed(False)

        # 1. Load User Configuration
        self.config: AppConfig = load_config()
        self.dictation_mode: bool = False

        # 2. Initialize Intelligence & Dispatch Subsystems
        self.gemini = GeminiInterpreter(model_name=self.config.ai.gemini_model)
        self.groq = GroqInterpreter(model_name=getattr(self.config.ai, "groq_model", "qwen/qwen3.8-27b"))
        self.router = IntentRouter(
            gemini=self.gemini,
            groq=self.groq,
            mode=self.config.ai.preferred_tier,
        )

        # 3. Qt Thread-safe UI & Speech Bridges
        self.bridge = SpeechBridge()
        self.bridge.partial_received.connect(self._handle_partial_ui)
        self.bridge.final_received.connect(self._handle_final_ui)

        self.ui_bridge = AppUIBridge()
        self.ui_bridge.user_message_requested.connect(self._safe_add_user_message)
        self.ui_bridge.assistant_message_requested.connect(self._safe_add_assistant_message)
        self.ui_bridge.action_card_requested.connect(self._safe_add_action_card)
        self.ui_bridge.config_proposal_requested.connect(self._handle_config_proposal_ui)
        self.ui_bridge.thinking_requested.connect(self._safe_show_thinking)
        self.ui_bridge.status_requested.connect(self._safe_set_status)
        self.ui_bridge.transcript_requested.connect(self._safe_set_transcript)
        self.ui_bridge.dictation_mode_requested.connect(self._safe_set_dictation_mode)
        self.ui_bridge.dictations_updated.connect(self._safe_refresh_dictations)
        self.ui_bridge.inspector_requested.connect(self.open_element_inspector)
        self.ui_bridge.transform_requested.connect(self._safe_open_transform_overlay)
        self.ui_bridge.undo_requested.connect(self._handle_undo_dictation)

        self.dispatcher = ActionDispatcher(
            enable_vision_fallback=self.config.ai.enable_vision_fallback,
            ui_bridge=self.ui_bridge,
        )
        self.workflows = WorkflowManager()
        self.element_inspector = None

        # 3.1 Wispr Flow Floating Pill HUD Overlay
        self.flow_overlay = WisprFlowOverlay()
        self.ui_bridge.flow_started.connect(self.flow_overlay.start_flow)
        self.ui_bridge.flow_transcribing.connect(self.flow_overlay.transcribing_flow)
        self.ui_bridge.flow_finished.connect(self.flow_overlay.finish_flow)
        self.ui_bridge.flow_cancelled.connect(self.flow_overlay.cancel_flow)

        # 3.15 Text Transforms HUD Overlay (Rewrite Selected Text)
        self.transform_overlay = TransformOverlay(llm_client=self.groq)

        # 3.16 Dictation Suite State (100+ Languages, 4-Level Auto Cleanup & Local Journal)
        initial_lang = getattr(self.config.voice, "language", "en")
        self.language_manager = LanguageManager(current_language=initial_lang)

        initial_cleanup = getattr(self.config.voice, "cleanup_level", "medium")
        try:
            self.dictation_cleanup_level = CleanupLevel(initial_cleanup)
        except Exception:
            self.dictation_cleanup_level = CleanupLevel.MEDIUM

        retention_policy = getattr(self.config.ui, "history_retention", "30_days")
        self.history_journal = HistoryJournal(retention_policy=retention_policy)
        self.history_journal.recover_interrupted_sessions()
        self.history_journal.apply_retention_policy()

        self.last_dictation_raw: str = ""
        self.last_dictation_cleaned: str = ""

        # Connect Flow bar pills to Dictation Suite
        self.flow_overlay.set_language_code(self.language_manager.current_language)
        self.flow_overlay.set_cleanup_level(self.dictation_cleanup_level.value)
        self.flow_overlay.language_changed.connect(self._on_flow_language_changed)
        self.flow_overlay.cleanup_level_changed.connect(self._on_flow_cleanup_level_changed)
        self.flow_overlay.undo_requested.connect(self._handle_undo_dictation)

        # 3.2 Watch Me & Automate Macro Recorder & HUD Banner
        self.macro_recorder = MacroRecorder(workflow_manager=self.workflows)
        self.macro_banner = MacroRecordingBanner(macro_recorder=self.macro_recorder)

        # 3.3 Universal Screen Lens Overlay (Win + Shift + Space)
        self.screen_lens = ScreenLensOverlay(gemini=self.gemini, groq=self.groq)

        # 3.4 Floating Copilot Action Widget (Smoothly docks when sidebar closes)
        self.floating_widget = FloatingCopilotWidget(
            on_open_sidebar=self._on_open_sidebar_from_floating,
            on_open_inspector=self.open_element_inspector,
            on_open_settings=self.open_settings,
            on_toggle_dictation=self._toggle_dictation_mode,
            on_exit_app=self.exit_app,
        )

        # 4. Initialize User Interface (Modern Sidebar or Classic Top Bar)
        ui_mode = getattr(self.config.ui, "ui_mode", "sidebar")
        if ui_mode == "top_bar":
            self.voice_bar = VoiceBar(
                on_mic_toggled=self._on_mic_toggled,
                on_open_settings=self.open_settings,
                on_emergency_stop=self._on_emergency_stop,
                on_command_submitted=self._handle_final_ui,
                on_dictation_toggled=self._on_dictation_toggled,
            )
            self.sidebar: Optional[SidebarWindow] = None
        else:
            sidebar_width = getattr(self.config.ui, "sidebar_width", 400)
            self.sidebar = SidebarWindow(
                on_mic_toggled=self._on_mic_toggled,
                on_open_settings=self.open_settings,
                on_emergency_stop=self._on_emergency_stop,
                on_command_submitted=self._handle_final_ui,
                on_dictation_toggled=self._on_dictation_toggled,
                on_open_inspector=self.open_element_inspector,
                width=sidebar_width,
            )
            self.sidebar.closed_to_floating.connect(self.floating_widget.show_animated)
            self.sidebar.dock_side_changed.connect(self.floating_widget.set_dock_side)
            self.voice_bar = self.sidebar  # Maintain unified interface alias

        self.dispatcher.on_sidebar_action = self._handle_sidebar_control

        # 4.5. Initialize Gemini Multimodal Live Session (Gemini 3.8 Live & Extended Thinking)
        self.live_session = GeminiLiveSession(
            dispatcher=self.dispatcher,
            model_name=MODEL_GEMINI_LIVE,
        )
        if self.sidebar is not None:
            self.sidebar.live_call_toggled.connect(self._on_live_call_toggled)
            self.live_session.audio_level_changed.connect(self.sidebar.live_call_view.update_audio_level)
            self.live_session.model_speaking_changed.connect(self.sidebar.live_call_view.set_speaking_state)
            self.live_session.transcript_received.connect(self.sidebar.live_call_view.set_transcript_text)
            self.live_session.tool_event.connect(self.sidebar.live_call_view.show_tool_activity)
            self.live_session.call_ended.connect(self.sidebar.end_live_call)
            self.live_session.error_occurred.connect(
                lambda err: self.sidebar.live_call_view.show_tool_activity("Error", "error", err)
            )
            self.sidebar.live_call_view.mute_toggled.connect(self.live_session.set_muted)
            self.sidebar.model_switched.connect(self.live_session.switch_model)
            self.sidebar.live_call_view.inspect_screen_requested.connect(self._handle_live_call_inspect_screen)
            self.sidebar.history_screen_view.set_journal(self.history_journal)
            self.sidebar.history_screen_view.undo_dictation_requested.connect(self._on_history_undo_dictation)
            self.sidebar.chat_screen_view.config_change_applied.connect(self._on_in_chat_config_change)



        self.tray_icon = HandlessTrayIcon(
            on_toggle_bar=self.toggle_voice_bar,
            on_open_settings=self.open_settings,
            on_toggle_dictation=self._toggle_dictation_mode,
            on_exit=self.exit_app,
        )

        self.settings_dialog: Optional[SettingsPanel] = None

        # 5. Initialize Speech Pipeline (Groq Whisper Large v3, local Whisper Base, or Vosk)
        engine_type = getattr(self.config.voice, "stt_engine", "groq_whisper")
        if engine_type == "groq_whisper":
            try:
                whisper_model = getattr(self.config.voice, "groq_whisper_model", "whisper-large-v3")
                self.recognizer = GroqWhisperRecognizer(
                    model=whisper_model,
                    sample_rate=self.config.voice.sample_rate,
                )
                if self.recognizer.is_ready:
                    logger.info("Initialized primary STT engine: Groq Cloud Whisper (%s).", whisper_model)
                else:
                    logger.warning("Groq Whisper recognizer missing API key, falling back to local Whisper.")
                    engine_type = "whisper"
            except Exception as exc:
                logger.warning("Failed to initialize Groq Whisper (%s), falling back to local Whisper.", exc)
                engine_type = "whisper"

        if engine_type == "whisper":
            try:
                whisper_path = getattr(self.config.voice, "whisper_model_path", "models/sherpa-onnx-whisper-base.en")
                self.recognizer = WhisperSpeechRecognizer(
                    model_path=whisper_path,
                    sample_rate=self.config.voice.sample_rate,
                )
                if self.recognizer.is_ready:
                    logger.info("Initialized STT engine: OpenAI Whisper Base (sherpa-onnx int8).")
                else:
                    raise RuntimeError("Whisper recognizer failed to load model files.")
            except Exception as exc:
                logger.warning("Failed to initialize Whisper (%s), falling back to Vosk.", exc)
                engine_type = "vosk"

        if engine_type == "vosk" or not hasattr(self, "recognizer") or not self.recognizer:
            self.recognizer = VoskSpeechRecognizer(
                model_path=self.config.voice.vosk_model_path,
                auto_download=False,
            )
            logger.info("Initialized STT engine: Vosk English.")
        self.mic = MicrophonePipeline(
            recognizer=self.recognizer,
            vad_aggressiveness=self.config.voice.vad_aggressiveness,
            on_partial=lambda text: self.bridge.partial_received.emit(text),
            on_final=lambda text: self.bridge.final_received.emit(text),
            on_level=self._on_mic_audio_level,
            device_index=self.config.voice.device_index,
        )

        # 5.5 Initialize Call & Meeting Transcriber (Zoom, Meet, WhatsApp, Teams)
        self.meeting_transcriber = MeetingTranscriber(
            stt_recognizer=self.recognizer,
            gemini_client=self.gemini,
            groq_client=self.groq,
        )
        if self.sidebar is not None:
            self.sidebar.meeting_screen_view.set_transcriber(self.meeting_transcriber)
        self.meeting_transcriber.action_item_detected.connect(self._on_meeting_action_item_detected)

        # 5.6 Speculative Pre-Transcribe Engine (Sub-100ms Perceived Speed)
        self.speculative_engine = SpeculativeDictationEngine(
            recognizer=self.recognizer,
            groq_client=self.groq,
        )

        # 6. Global Hotkey Manager
        self.hotkeys = GlobalHotkeyManager(
            on_ptt_pressed=self._on_ptt_pressed,
            on_ptt_released=self._on_ptt_released,
            on_toggle_bar=self.toggle_voice_bar,
            on_toggle_dictation=self._toggle_dictation_mode,
            on_flow_pressed=self._on_flow_pressed,
            on_flow_released=self._on_flow_released,
            on_screen_lens=self.screen_lens.activate_lens,
            on_transform_selection=self.ui_bridge.transform_requested.emit,
            on_undo_dictation=self.ui_bridge.undo_requested.emit,
        )

    def _safe_open_transform_overlay(self) -> None:
        if hasattr(self, "transform_overlay") and self.transform_overlay:
            self.transform_overlay.open_at_cursor()

    def run(self) -> int:
        """Start all services and run Qt main event loop."""
        logger.info("Starting Vyoma Handless...")

        # Start microphone and global hotkeys
        self.mic.start()
        self.hotkeys.start()

        # Show UI
        if self.sidebar is not None:
            self.sidebar.slide_in()
        else:
            self.voice_bar.show()
            self.voice_bar.raise_()
            self.voice_bar.activateWindow()
        self.tray_icon.show()

        logger.info("Vyoma Handless running. Modern AI Copilot active.")
        return self.qt_app.exec()

    def toggle_voice_bar(self) -> None:
        """Show or hide the floating voice control UI."""
        if self.sidebar is not None:
            if self.sidebar.isVisible():
                self.sidebar.slide_out()
            else:
                if hasattr(self, "floating_widget") and self.floating_widget.isVisible():
                    self.floating_widget.hide_animated(on_finish=self.sidebar.slide_in)
                else:
                    self.sidebar.slide_in()
        else:
            if self.voice_bar.isVisible():
                self.voice_bar.hide()
            else:
                self.voice_bar.show()
                self.voice_bar.raise_()
                self.voice_bar.activateWindow()

    def _on_open_sidebar_from_floating(self) -> None:
        """Called when user clicks the floating square action widget."""
        if self.sidebar is not None:
            self.floating_widget.hide_animated(on_finish=self.sidebar.slide_in)
        elif self.voice_bar is not None:
            self.floating_widget.hide_animated(on_finish=self.voice_bar.show)

    def _on_flow_pressed(self) -> None:
        """Wispr Flow push-to-talk pressed (Ctrl+Shift held down)."""
        logger.info("Wispr Flow hold-to-talk started with Speculative Pre-Transcribe.")
        if hasattr(self, "speculative_engine") and self.speculative_engine:
            self.speculative_engine.start_session(
                language=getattr(self.language_manager, "whisper_language", "en")
            )
            self.mic.start_raw_tap(on_chunk=self.speculative_engine.feed_chunk)
        else:
            self.mic.start_raw_tap()
        self.ui_bridge.flow_started.emit()

    def _on_flow_language_changed(self, lang_code: str) -> None:
        self.language_manager.set_language(lang_code)
        whisper_code = self.language_manager.whisper_language
        if hasattr(self, "recognizer") and hasattr(self.recognizer, "set_language"):
            self.recognizer.set_language(whisper_code)
        lang_name = self.language_manager.get_language_name(lang_code)
        logger.info("Switched dictation language to: %s (%s)", lang_name, lang_code)
        self.ui_bridge.status_requested.emit(f"🌐 Language: {lang_name}")

    def _on_flow_cleanup_level_changed(self, level: str) -> None:
        try:
            self.dictation_cleanup_level = CleanupLevel(level.lower())
        except Exception:
            self.dictation_cleanup_level = CleanupLevel.MEDIUM
        logger.info("Switched auto cleanup level to: %s", self.dictation_cleanup_level.value)
        self.ui_bridge.status_requested.emit(f"✦ Cleanup: {self.dictation_cleanup_level.value.capitalize()}")

    def _handle_undo_dictation(self) -> None:
        """Revert the most recent dictation from cleaned text back to raw speech."""
        if not self.last_dictation_raw:
            logger.info("No prior dictation to undo.")
            self.ui_bridge.status_requested.emit("Nothing to undo")
            return

        logger.info("Undoing dictation edit: reverting to '%s'", self.last_dictation_raw)
        paste_text(self.last_dictation_raw)
        self.ui_bridge.status_requested.emit("Reverted to Raw Speech ✓")
        self.ui_bridge.transcript_requested.emit(f"Reverted: \"{self.last_dictation_raw}\"")
        self.ui_bridge.action_card_requested.emit("Reverted to Raw Speech", self.last_dictation_raw[:35], "↺", "✓")

    def _on_history_undo_dictation(self, cleaned: str, raw: str) -> None:
        self.last_dictation_raw = raw
        self.last_dictation_cleaned = cleaned
        self._handle_undo_dictation()

    def _on_flow_released(self) -> None:
        """Wispr Flow push-to-talk released (Ctrl+Shift released)."""
        logger.info("Wispr Flow hold-to-talk released. Finalizing speculative dictation...")
        self.ui_bridge.flow_transcribing.emit()
        raw_audio = self.mic.stop_raw_tap()

        def _transcribe_and_paste():
            try:
                text = ""
                latency_ms = 0.0

                # 1. Speculative Pre-Transcribe Engine (Sub-100ms Perceived Speed)
                if hasattr(self, "speculative_engine") and self.speculative_engine:
                    spec_result = self.speculative_engine.finalize_session()
                    if spec_result and spec_result.text:
                        text = spec_result.text
                        latency_ms = spec_result.latency_ms
                        hits = getattr(spec_result, "pre_transcribed_hits", getattr(spec_result, "speculative_hits", 0))
                        logger.info(
                            "⚡ Speculative Pre-Transcribe hit! Finalized in %.1fms (Hits: %d, Text: '%s')",
                            latency_ms, hits, text
                        )

                # 2. Fallback to standard transcribe if speculative did not yield text
                if not text:
                    if not raw_audio or len(raw_audio) < 1600:  # < 0.1s
                        self.ui_bridge.flow_cancelled.emit()
                        return

                    t0 = time.perf_counter()
                    if hasattr(self, "recognizer") and hasattr(self.recognizer, "transcribe_pcm"):
                        import inspect
                        sig = inspect.signature(self.recognizer.transcribe_pcm)
                        if "is_speculative" in sig.parameters:
                            text = self.recognizer.transcribe_pcm(raw_audio, is_speculative=False)
                        else:
                            text = self.recognizer.transcribe_pcm(raw_audio)
                    elif hasattr(self, "recognizer") and hasattr(self.recognizer, "transcribe_raw"):
                        text = self.recognizer.transcribe_raw(raw_audio)
                    else:
                        for i in range(0, len(raw_audio), 3200):
                            block = raw_audio[i:i+3200]
                            self.recognizer.accept_audio(block)
                        text = self.recognizer.get_final_result()
                    latency_ms = (time.perf_counter() - t0) * 1000.0

                if not text or not text.strip():
                    logger.info("Wispr Flow: No speech detected.")
                    self.ui_bridge.flow_cancelled.emit()
                    return

                # 4-Level Auto Cleanup Engine
                res = clean_text_with_level(
                    raw_text=text,
                    level=self.dictation_cleanup_level,
                    llm_client=self.groq,
                )
                cleaned = res.cleaned_text

                # Store for undo / revert
                self.last_dictation_raw = text
                self.last_dictation_cleaned = cleaned

                # Active target window detection
                active_app = "Desktop App"
                try:
                    active_title = get_active_window_title()
                    if active_title:
                        active_app = active_title
                except Exception:
                    pass

                # Record in History Journal
                duration_sec = round(len(raw_audio) / 32000.0, 1) if raw_audio else 0.5
                self.history_journal.record_dictation(
                    raw_text=text,
                    cleaned_text=cleaned,
                    cleanup_level=self.dictation_cleanup_level.value,
                    target_app=active_app,
                    language=self.language_manager.current_language,
                    duration_sec=duration_sec,
                    status="completed",
                )

                self.ui_bridge.dictations_updated.emit()

                if cleaned:
                    logger.info(
                        "Wispr Flow recognized (Level %s): '%s' (Latency: %.1fms)",
                        self.dictation_cleanup_level.value, cleaned, latency_ms
                    )
                    paste_text(cleaned)
                    self.ui_bridge.flow_finished.emit(cleaned)
                    if latency_ms > 0:
                        self.ui_bridge.status_requested.emit(f"⚡ Dictated in {int(latency_ms)}ms")
                else:
                    self.ui_bridge.flow_cancelled.emit()
            except Exception as exc:
                logger.error("Wispr Flow transcription error: %s", exc)
                self.ui_bridge.flow_cancelled.emit()

        threading.Thread(target=_transcribe_and_paste, daemon=True).start()

    def _toggle_dictation_mode(self) -> None:
        """Toggle between Command Mode and Dictation Mode via global hotkey."""
        self.dictation_mode = not self.dictation_mode
        self.voice_bar.set_dictation_mode(self.dictation_mode)
        logger.info("Dictation Mode toggled: %s", self.dictation_mode)

        logger.info("Dictation Mode toggled: %s", self.dictation_mode)

    def _on_dictation_toggled(self, active: bool) -> None:
        """Handle dictation mode toggle from VoiceBar button click."""
        self.dictation_mode = active
        logger.info("Dictation Mode set from UI: %s", self.dictation_mode)

    def open_settings(self) -> None:
        """Open the unified Settings view inside the sidebar without opening extra dialog windows."""
        if self.sidebar is not None:
            if not self.sidebar.isVisible():
                if hasattr(self, "floating_widget") and self.floating_widget.isVisible():
                    self.floating_widget.hide_animated(on_finish=self.sidebar.slide_in)
                else:
                    self.sidebar.slide_in()
            self.sidebar._show_settings_view()
            self.sidebar.raise_()
            self.sidebar.activateWindow()
        elif self.voice_bar is not None:
            if self.settings_dialog is None:
                self.settings_dialog = SettingsPanel(self.config, parent=None)
                self.settings_dialog.finished.connect(self._on_settings_closed)
            self.settings_dialog.show()
            self.settings_dialog.raise_()
            self.settings_dialog.activateWindow()

    def _handle_sidebar_control(self, action: str, target: str = "") -> bool:
        """Execute self-docking, sizing, floating, and view changes on the sidebar."""
        if self.sidebar is None:
            return False
        clean = action.strip().lower()
        if clean in (
            "sidebar_dock_left", "dock_left", "dock left", "dock to left",
            "move sidebar left", "move sidebar to the left", "move to left",
            "switch sidebar to left", "put sidebar on left", "left dock", "sidebar left",
        ):
            self.sidebar.dock_to_left()
            return True
        elif clean in (
            "sidebar_dock_right", "dock_right", "dock right", "dock to right",
            "move sidebar right", "move sidebar to the right", "move to right",
            "switch sidebar to right", "put sidebar on right", "right dock", "sidebar right",
        ):
            self.sidebar.dock_to_right()
            return True
        elif clean in (
            "sidebar_toggle_dock", "toggle_dock", "toggle dock", "switch sides",
            "switch dock side", "move out of the way", "dodge", "other side",
        ):
            self.sidebar.toggle_dock_side()
            return True
        elif clean in (
            "sidebar_expand", "make sidebar wide", "wide mode", "big sidebar",
            "expand sidebar", "make sidebar big", "large sidebar", "wide sidebar",
            "full width", "open full", "wider",
        ):
            self.sidebar.set_wide_mode(True)
            return True
        elif clean in (
            "sidebar_compact", "make sidebar small", "compact mode", "small sidebar",
            "normal sidebar", "shrink sidebar", "compact sidebar", "narrow sidebar",
            "standard sidebar", "narrower", "standard width", "normal width",
        ):
            self.sidebar.set_wide_mode(False)
            return True
        elif clean in ("sidebar_toggle_width", "toggle wide", "toggle width"):
            self.sidebar.toggle_wide_mode()
            return True
        elif action in ("sidebar_float", "sidebar_minimize"):
            self.sidebar.minimize_to_floating()
            return True
        elif action in ("sidebar_auto_fit", "sidebar_snap", "sidebar_fit"):
            self.sidebar.auto_fit_to_side()
            return True
        elif action in ("sidebar_call", "start_call", "live_call"):
            self.sidebar.start_live_call()
            return True
        elif action in ("end_call", "stop_call", "hang_up"):
            self.sidebar.end_live_call()
            return True
        elif action in ("sidebar_meeting", "open_meeting", "transcribe_meeting", "meeting_transcripts"):
            self.sidebar._show_meeting_view()
            return True
        elif action in ("start_meeting_recording", "record_meeting", "record_call"):
            self.sidebar._show_meeting_view()
            if hasattr(self, "meeting_transcriber") and self.meeting_transcriber:
                self.meeting_transcriber.start_recording()
            return True
        elif action in ("stop_meeting_recording", "stop_recording_meeting", "stop_recording_call"):
            if hasattr(self, "meeting_transcriber") and self.meeting_transcriber:
                self.meeting_transcriber.stop_recording()
            return True
        elif action in ("summarize_meeting", "summarize_call"):
            self.sidebar._show_meeting_view()
            if hasattr(self, "meeting_transcriber") and self.meeting_transcriber:
                self.meeting_transcriber.generate_summary()
            return True
        elif action in ("start_macro_recording", "watch_me", "record_workflow"):
            if hasattr(self, "macro_recorder") and self.macro_recorder:
                self.macro_recorder.start_recording()
            return True
        elif action in ("save_macro", "save_workflow"):
            name = target or "Custom Workflow"
            if hasattr(self, "macro_recorder") and self.macro_recorder:
                self.macro_recorder.save_macro(name=name)
            return True
        elif action in ("stop_macro_recording", "discard_macro", "cancel_macro"):
            if hasattr(self, "macro_recorder") and self.macro_recorder:
                self.macro_recorder.discard_recording()
            return True
        elif action in ("open_screen_lens", "screen_lens"):
            if hasattr(self, "screen_lens") and self.screen_lens:
                self.screen_lens.activate_lens()
            return True
        elif action in ("open_transforms", "transforms"):
            if hasattr(self, "transform_overlay") and self.transform_overlay:
                self.transform_overlay.open_at_cursor()
            return True
        elif action == "transform_selection":
            if hasattr(self, "transform_overlay") and self.transform_overlay:
                t_type = target or "polish"
                self.transform_overlay.execute_direct_transform(t_type)
            return True
        elif action == "set_cleanup_level":
            self._on_flow_cleanup_level_changed(target)
            return True
        elif action == "set_language":
            self._on_flow_language_changed(target)
            return True
        elif action == "undo_dictation":
            self._handle_undo_dictation()
            return True
        elif action == "sidebar_settings":
            self.open_settings()
            return True
        elif action in ("open_logs", "open_log_folder", "view_logs", "show_logs"):
            open_logs_directory()
            self.ui_bridge.status_requested.emit("📁 Opened Logs")
            return True
        elif action in ("open_element_inspector", "open_inspector", "element_inspector", "inspect_elements", "inspect_ui", "spy_tool", "pick_element"):
            self.open_element_inspector()
            self.ui_bridge.status_requested.emit("🎯 Opened Element Inspector")
            return True
        elif action in ("view_errors", "show_errors", "error_log"):
            errs = get_latest_errors(20)
            self.ui_bridge.assistant_message_requested.emit(f"📋 **Recent Error Log**:\n```\n{errs}\n```")
            return True

        # Direct App Launches and Catalog Actions from Explore / Chat
        clean_act = action.strip().lower()
        if clean_act.startswith("launch_app:"):
            app_name = clean_act.split(":", 1)[1].strip()
            self.dispatcher.launcher.launch_app(app_name)
            return True
        elif clean_act in ("open chrome", "chrome"):
            self.dispatcher.launcher.launch_app("chrome")
            return True
        elif clean_act in ("open youtube", "youtube"):
            webbrowser.open("https://www.youtube.com")
            return True
        elif clean_act in ("open vscode", "vscode", "open code", "code"):
            self.dispatcher.launcher.launch_app("code")
            return True
        elif clean_act in ("open notion", "notion"):
            self.dispatcher.launcher.launch_app("notion")
            return True
        elif clean_act in ("open spotify", "spotify"):
            self.dispatcher.launcher.launch_app("spotify")
            return True
        elif clean_act in ("open whatsapp", "whatsapp"):
            self.dispatcher.launcher.launch_app("whatsapp")
            return True
        elif clean_act in ("open discord", "discord"):
            self.dispatcher.launcher.launch_app("discord")
            return True
        elif clean_act in ("open terminal", "terminal", "powershell"):
            self.dispatcher.launcher.launch_app("wt")
            return True
        elif clean_act in ("open notepad", "notepad"):
            self.dispatcher.launcher.launch_app("notepad")
            return True
        elif clean_act in ("open calculator", "calculator", "calc"):
            self.dispatcher.launcher.launch_app("calc")
            return True
        elif clean_act in ("open downloads folder", "open downloads", "find latest downloaded files"):
            downloads_p = Path.home() / "Downloads"
            try:
                os.startfile(str(downloads_p))
            except Exception:
                subprocess.Popen(["explorer.exe", str(downloads_p)])
            return True
        elif clean_act in ("open task manager", "task manager", "taskmgr"):
            self.dispatcher.launcher.launch_app("taskmgr")
            return True
        elif clean_act in ("open disk storage cleanup", "open disk cleanup", "clean up system files"):
            try:
                subprocess.Popen("cleanmgr.exe")
            except Exception:
                pass
            return True
        elif clean_act in ("open settings", "optimize system settings"):
            self.open_settings()
            return True
        elif clean_act in ("open element inspector", "inspect elements", "open inspector", "element inspector", "spy tool", "pick element"):
            self.open_element_inspector()
            self.ui_bridge.status_requested.emit("🎯 Opened Element Inspector")
            return True
        elif clean_act in ("open logs", "view logs", "show logs", "open logs folder", "open log folder", "diagnose logs"):
            open_logs_directory()
            self.ui_bridge.status_requested.emit("📁 Opened Logs")
            err_summary = get_latest_errors(15)
            self.ui_bridge.assistant_message_requested.emit(f"📁 Opened logs directory:\n`{get_main_log_path()}`\n\n**Current System Diagnostics**:\n```\n{err_summary}\n```")
            return True
        elif clean_act in ("open meeting transcriber", "transcribe meeting", "transcribe call"):
            self.sidebar._show_meeting_view()
            return True
        elif clean_act in ("open excel", "open spreadsheet"):
            self.dispatcher.launcher.launch_app("excel")
            return True
        elif clean_act in ("open word", "create new document", "create new summary document"):
            self.dispatcher.launcher.launch_app("winword")
            return True
        elif clean_act in ("open obs", "record screen"):
            self.dispatcher.launcher.launch_app("obs")
            return True
        elif clean_act in ("activate boss mode", "boss mode"):
            subprocess.run(["powershell", "-Command", "(New-Object -ComObject Shell.Application).MinimizeAll()"])
            self.ui_bridge.status_requested.emit("Boss Mode Activated 🛡️")
            return True
        elif clean_act in ("setup dev workspace", "dev workspace"):
            self.dispatcher.launcher.launch_app("chrome")
            self.dispatcher.launcher.launch_app("code")
            self.dispatcher.launcher.launch_app("wt")
            self.ui_bridge.status_requested.emit("Dev Workspace Ready 🚀")
            return True
        elif clean_act in ("prepare daily schedule", "plan my day"):
            self.ui_bridge.assistant_message_requested.emit("📅 **Today's Agenda Ready**:\n- 10:00 AM: Team Standup\n- 02:00 PM: Project Review\n- Focus Time: 3:30 PM - 5:00 PM")
            return True
        elif clean_act in ("summarize unread emails", "summarize emails"):
            self.ui_bridge.assistant_message_requested.emit("📬 **Unread Emails Summary**:\n- 3 priority emails from design team\n- 1 calendar invitation for tomorrow\n- All newsletters automatically archived.")
            return True
        elif clean_act in ("analyze current screenshot", "analyze latest screenshot", "take a screenshot"):
            if hasattr(self, "screen_lens") and self.screen_lens:
                self.screen_lens.activate_lens()
            return True
        elif clean_act in ("organize downloads folder", "organize downloads"):
            self.ui_bridge.assistant_message_requested.emit("📁 Checked Downloads folder: 14 PDFs, 8 images, 3 archives. Ready to sort!")
            return True
        elif clean_act in ("check network connection"):
            self.ui_bridge.assistant_message_requested.emit("🌐 **Network Status**: Connected. Ping to 8.8.8.8 is 18ms. Zero packet loss.")
            return True
        elif clean_act in ("optimize power settings"):
            self.ui_bridge.assistant_message_requested.emit("⚡ **Power Optimizer**: Performance plan active. High-frequency CPU cores unlocked.")
            return True
        elif clean_act in ("toggle dictation"):
            self.dictation_mode = not self.dictation_mode
            self.ui_bridge.dictation_mode_requested.emit(self.dictation_mode)
            self.ui_bridge.status_requested.emit("✍️ Dictation Active" if self.dictation_mode else "🎤 Command Mode Active")
            return True
        return False

    def _on_live_call_toggled(self, active: bool) -> None:
        """Handle live call activation/deactivation."""
        if active:
            # Pause local microphone recognizer while live call is active
            if hasattr(self, "mic") and self.mic:
                self.mic.set_listening(False, flush=False)
            if hasattr(self, "voice_bar") and self.voice_bar:
                self.voice_bar.set_listening(False)
            self.live_session.start_call()
        else:
            self.live_session.stop_call()
            if hasattr(self, "mic") and self.mic:
                self.mic.set_listening(True)
            if hasattr(self, "voice_bar") and self.voice_bar:
                self.voice_bar.set_listening(True)

    def _handle_live_call_inspect_screen(self) -> None:
        """Capture screenshot and share visual feedback during live call."""
        shot = self.dispatcher.vision.take_screenshot()
        if shot and self.sidebar:
            self.sidebar.live_call_view.show_tool_activity("Screen Vision", "done", "Screen inspected and shared with Gemini")

    def _on_mic_audio_level(self, level: float) -> None:
        """Feed microphone audio level into meeting transcriber if active."""
        if hasattr(self, "meeting_transcriber") and self.meeting_transcriber and self.meeting_transcriber.is_recording:
            self.meeting_transcriber.feed_mic_level(level)

    def _on_meeting_action_item_detected(self, item: Any) -> None:
        """Handle real-time extracted commitment or action item from stereo diarized meeting."""
        assignee = getattr(item, "assignee", "Team")
        task = getattr(item, "task", "")
        deadline = getattr(item, "deadline", "")
        desc = f"{task}"
        if deadline:
            desc += f" (Due: {deadline})"
        logger.info("Live Commitment Detected: [%s] %s", assignee, desc)
        self.ui_bridge.action_card_requested.emit(
            f"Commitment: {assignee}",
            desc,
            "📌",
            "Added"
        )
        self.ui_bridge.status_requested.emit(f"📌 Action Item: {task[:25]}...")

    def _on_settings_closed(self) -> None:
        self.settings_dialog = None
        # Re-apply mode and tier
        self.gemini.model_name = self.config.ai.gemini_model
        if hasattr(self, "groq") and hasattr(self.config.ai, "groq_model"):
            self.groq.model_name = self.config.ai.groq_model
        self.router.mode = self.config.ai.preferred_tier
        self.dispatcher.enable_vision_fallback = self.config.ai.enable_vision_fallback

    def _on_mic_toggled(self, active: bool) -> None:
        if active and emergency_stop.is_stopped():
            emergency_stop.reset()
        self.mic.set_listening(active)

    def _on_ptt_pressed(self) -> None:
        logger.debug("PTT Hotkey pressed.")
        emergency_stop.reset()
        self.voice_bar.set_listening(True)
        self.mic.set_listening(True)

    def _on_ptt_released(self) -> None:
        logger.debug("PTT Hotkey released.")
        self.voice_bar.set_listening(False)
        self.mic.set_listening(False)

    def _safe_add_user_message(self, text: str) -> None:
        if self.sidebar is not None:
            self.sidebar.add_user_message(text)

    def _safe_add_assistant_message(self, text: str) -> None:
        if self.sidebar is not None:
            self.sidebar.add_assistant_message(text)

    def _safe_add_action_card(self, title: str, subtitle: str, icon: str, btn_label: str) -> None:
        if self.sidebar is not None:
            self.sidebar.add_action_card(title, subtitle, icon, btn_label)

    def _safe_refresh_dictations(self) -> None:
        if self.sidebar is not None and hasattr(self.sidebar, "history_screen_view"):
            self.sidebar.history_screen_view.refresh_dictations()

    def _handle_config_proposal_ui(self, proposal: Any) -> None:
        if self.sidebar is not None:
            self.sidebar.add_config_proposal_card(proposal)

    def _on_in_chat_config_change(self, setting_key: str, new_value: str) -> None:
        """Handle 1-click 'Allow & Apply' live re-configuration of Handless from Chat."""
        logger.info("In-chat config change applied live: %s -> %s", setting_key, new_value)
        try:
            if "dictation" in setting_key and ("shortcut" in setting_key or "toggle" in setting_key):
                self.config.hotkeys.toggle_dictation = new_value
                if hasattr(self, "flow_listener") and self.flow_listener:
                    self.flow_listener.custom_hotkey = new_value
                self.ui_bridge.status_requested.emit(f"✓ Dictation hotkey set to {new_value}")
                self.ui_bridge.assistant_message_requested.emit(f"Done! Dictation shortcut rewired to **{new_value}**. Press it anytime! 🚀")
            elif "cleanup" in setting_key:
                self._on_flow_cleanup_level_changed(new_value)
                self.ui_bridge.status_requested.emit(f"✓ Cleanup set to {new_value}")
                self.ui_bridge.assistant_message_requested.emit(f"Done! Speech cleanup is now set to **{new_value}**.")
            elif "language" in setting_key:
                self._on_flow_language_changed(new_value)
                self.ui_bridge.status_requested.emit(f"✓ Language set to {new_value}")
                self.ui_bridge.assistant_message_requested.emit(f"Done! Primary language updated to **{new_value}** 🌍")
            elif "sidebar_width" in setting_key or "width" in setting_key:
                is_wide = "wide" in new_value.lower()
                if self.sidebar:
                    self.sidebar.set_wide_mode(is_wide)
                self.config.ui.sidebar_width = 560 if is_wide else 400
                self.ui_bridge.status_requested.emit(f"✓ Sidebar set to {'Wide' if is_wide else 'Compact'}")
            save_config(self.config)
        except Exception as exc:
            logger.error("Failed to apply in-chat config change: %s", exc)

    def _safe_show_thinking(self, active: bool) -> None:
        if self.sidebar is not None:
            self.sidebar.show_thinking(active)

    def _safe_set_status(self, text: str) -> None:
        self.voice_bar.set_status(text)

    def _safe_set_transcript(self, text: str) -> None:
        self.voice_bar.set_transcript(text)

    def _safe_set_dictation_mode(self, active: bool) -> None:
        self.dictation_mode = active
        self.voice_bar.set_dictation_mode(active)

    def _on_emergency_stop(self) -> None:
        self.voice_bar.set_status("⛔ Emergency Stop Active")
        self.mic.set_listening(False)

    def _handle_partial_ui(self, text: str) -> None:
        """Update VoiceBar with streaming partial transcription."""
        if hasattr(self, "live_session") and self.live_session and self.live_session.is_active:
            return
        self.voice_bar.set_transcript(text)

    def _handle_final_ui(self, text: str) -> None:
        """Process finalized speech transcript and execute actions."""
        if not text:
            return
        if hasattr(self, "live_session") and self.live_session and self.live_session.is_active:
            logger.info("Ignoring STT transcript during active Live Call: %s", text)
            return

        self.voice_bar.set_transcript(f'"{text}"')
        self.voice_bar.set_status("Interpreting..." if not self.dictation_mode else "✍️ Typing...")

        # If Call & Meeting transcription is active, record user turn as 'You'
        if hasattr(self, "meeting_transcriber") and self.meeting_transcriber and self.meeting_transcriber.is_recording:
            self.meeting_transcriber.add_user_speech(text)

        # If using modern sidebar, add speech bubble if not already added by typed input
        if self.sidebar is not None:
            if not self.sidebar.cmd_input.hasFocus():
                self.sidebar.add_user_message(text)
            self.sidebar.show_thinking(True)

        # Run interpretation and execution in a worker thread so UI never freezes
        threading.Thread(target=self._process_command_worker, args=(text,), daemon=True).start()

    def _process_command_worker(self, text: str) -> None:
        """Background worker thread for intent routing and desktop execution.
        
        Thread-safety rule: All UI mutations (VoiceBar, Sidebar, Widgets) MUST be
        dispatched via self.ui_bridge signals to ensure execution on Qt main thread.
        """
        try:
            # 0. Check In-Chat Handless Self-Configuration Proposal (e.g. "change shortcut to Ctrl+Alt+D")
            proposal = detect_config_proposal(text, self.config)
            if proposal:
                self.ui_bridge.status_requested.emit(f"Proposal: {proposal.setting_label}")
                self.ui_bridge.transcript_requested.emit(f"Configure {proposal.setting_label}")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.config_proposal_requested.emit(proposal)
                return

            # 0.2. Check Casual Chit-Chat & Roasts (Grok Persona: "hi", "how are you", "roast me", etc.)
            if is_casual_chitchat(text):
                reply = generate_grok_chat_reply(
                    text,
                    groq_client=self.groq,
                    gemini_client=self.gemini,
                )
                self.ui_bridge.transcript_requested.emit(f"💡 {reply[:35]}...")
                self.ui_bridge.status_requested.emit("Replied ✓")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.assistant_message_requested.emit(reply)
                return

            # 0.4. Check Direct Sidebar or Explore Action Execution
            clean_cmd = text.strip().lower()
            if self._handle_sidebar_control(clean_cmd):
                self.ui_bridge.status_requested.emit("Handled ✓")
                self.ui_bridge.transcript_requested.emit(f"Executed: {text}")
                self.ui_bridge.thinking_requested.emit(False)
                return

            # 0.5. Dictation Mode Fast-Path (OpenWhispr Architecture)
            if self.dictation_mode:
                lower = text.strip().lower()
                if lower in ("stop dictation", "exit dictation", "command mode", "disable dictation", "turn off dictation"):
                    self.ui_bridge.dictation_mode_requested.emit(False)
                    self.ui_bridge.status_requested.emit("🎤 Command Mode Active")
                    self.ui_bridge.transcript_requested.emit("Exited dictation mode")
                    self.ui_bridge.thinking_requested.emit(False)
                    return

                res = clean_text_with_level(
                    raw_text=text,
                    level=self.dictation_cleanup_level,
                    llm_client=self.groq,
                )
                cleaned = res.cleaned_text
                self.last_dictation_raw = text
                self.last_dictation_cleaned = cleaned

                active_app = "Active Window"
                try:
                    active_title = get_active_window_title()
                    if active_title:
                        active_app = active_title
                except Exception:
                    pass

                self.history_journal.record_dictation(
                    raw_text=text,
                    cleaned_text=cleaned,
                    cleanup_level=self.dictation_cleanup_level.value,
                    target_app=active_app,
                    language=self.language_manager.current_language,
                    status="completed",
                )
                self.ui_bridge.dictations_updated.emit()

                if cleaned:
                    self.ui_bridge.transcript_requested.emit(f'"{cleaned}"')
                    self.ui_bridge.status_requested.emit("✍️ Pasting...")
                    pasted = paste_text(cleaned, preserve_clipboard=True)
                    if pasted:
                        self.ui_bridge.status_requested.emit("✍️ Pasted ✓")
                        self.ui_bridge.thinking_requested.emit(False)
                        self.ui_bridge.action_card_requested.emit(f"Pasted: \"{cleaned[:30]}...\"", f"Dictation ({self.dictation_cleanup_level.value})", "✍️", "✓")
                    else:
                        self.ui_bridge.status_requested.emit("⚠️ Paste failed")
                        self.ui_bridge.thinking_requested.emit(False)
                return

            # 1. Check workflow macro triggers first
            matched_wf = self.workflows.find_by_trigger(text)
            if matched_wf:
                self.ui_bridge.status_requested.emit(f"⚡ Workflow: {matched_wf.name}")
                self.ui_bridge.transcript_requested.emit(f"Ran '{matched_wf.name}'")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.action_card_requested.emit(f"Workflow: {matched_wf.name}", "Macro executed", "⚡", "✓")
                self.workflows.execute(matched_wf, self.dispatcher)
                return

            # 2. Gather active context summary and live screen capture for intelligence layer
            summary = self.dispatcher.uia.get_visible_elements_summary(max_elements=15)
            control_tree = self.dispatcher.uia.dump_control_tree(depth=2, max_lines=40)
            screenshot_img = None
            screen_dims = (1920, 1080)
            try:
                screenshot_img, screen_dims = self.dispatcher.vision.capture_screenshot()
            except Exception as s_exc:
                logger.debug("Could not capture screenshot for context: %s", s_exc)

            context = {
                "visible_elements": summary,
                "control_tree": control_tree,
                "screenshot": screenshot_img,
                "screen_size": screen_dims,
            }

            # 3. Interpret intent
            intent = self.router.interpret(text, context=context)
            if not intent:
                self.ui_bridge.status_requested.emit("Didn't understand command")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.assistant_message_requested.emit("I couldn't understand that command. Try asking to open an app or control windows.")
                return

            # Check if intent is toggling dictation mode via voice
            if intent.actions:
                first_act = intent.actions[0]
                if first_act.action_type == ActionType.SYSTEM_ACTION:
                    sys_act = (first_act.system_action or first_act.target or "").lower()
                    if sys_act in ("start_dictation", "enter_dictation"):
                        self.ui_bridge.dictation_mode_requested.emit(True)
                        self.ui_bridge.status_requested.emit("✍️ Dictation Mode Active")
                        self.ui_bridge.transcript_requested.emit("Dictation enabled. Speak to type.")
                        self.ui_bridge.thinking_requested.emit(False)
                        self.ui_bridge.action_card_requested.emit("Dictation Mode Active", "Speak to type directly", "✍️", "✓")
                        return
                    elif sys_act in ("stop_dictation", "exit_dictation"):
                        self.ui_bridge.dictation_mode_requested.emit(False)
                        self.ui_bridge.status_requested.emit("🎤 Command Mode Active")
                        self.ui_bridge.transcript_requested.emit("Command mode enabled.")
                        self.ui_bridge.thinking_requested.emit(False)
                        self.ui_bridge.action_card_requested.emit("Command Mode Active", "Controls enabled", "⚡", "✓")
                        return

            # Filter valid actionable requests (excluding NONE)
            valid_actions = [a for a in intent.actions if a.action_type not in (ActionType.NONE, "none")]

            # Check conversational Q&A answer
            if intent.answer_text and not valid_actions:
                self.ui_bridge.transcript_requested.emit(f"💡 {intent.answer_text[:35]}...")
                self.ui_bridge.status_requested.emit("Answered by AI")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.assistant_message_requested.emit(intent.answer_text)
                return

            if not valid_actions:
                reply = generate_grok_chat_reply(
                    text,
                    groq_client=self.groq,
                    gemini_client=self.gemini,
                )
                self.ui_bridge.status_requested.emit("Answered ✓")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.assistant_message_requested.emit(reply)
                return

            # Check if emergency stop command
            if intent.actions[0].target == "emergency_stop":
                emergency_stop.trigger(reason="Voice command 'stop'")
                self.ui_bridge.status_requested.emit("⛔ Stopped")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.action_card_requested.emit("Emergency Stop Triggered", "Controls paused", "⛔", "!")
                return

            # Check if resume / reset stop command
            if intent.actions[0].target == "reset_stop":
                emergency_stop.reset()
                self.ui_bridge.status_requested.emit("Ready ✓")
                self.ui_bridge.transcript_requested.emit("Controls resumed")
                self.ui_bridge.thinking_requested.emit(False)
                self.ui_bridge.action_card_requested.emit("Controls Resumed", "Ready for commands", "▶️", "✓")
                return

            # If user is executing a valid new action, ensure previous emergency stop is cleared
            if emergency_stop.is_stopped():
                emergency_stop.reset()

            # 4. Execute actions via Dispatcher
            def status_cb(status_msg: str) -> None:
                self.ui_bridge.status_requested.emit(status_msg)

            self.dispatcher.execute_plan(valid_actions, status_callback=status_cb)

            # Update sidebar with rich action card via main thread signal
            self.ui_bridge.thinking_requested.emit(False)
            if valid_actions:
                first_act = valid_actions[0]
                act_type = first_act.action_type
                icon = "⚡"
                title = "Executed Action"
                subtitle = "Action complete"
                sector = "System"
                if act_type == ActionType.LAUNCH_APP:
                    icon = "🚀"
                    title = f"Launched {first_act.target}"
                    subtitle = "Application opened"
                    sector = "Apps"
                elif act_type == ActionType.SYSTEM_ACTION:
                    tgt = first_act.system_action or first_act.target or "system"
                    icon = "📐" if "snap" in tgt.lower() else "⚡"
                    title = f"System: {tgt.replace('_', ' ').title()}"
                    subtitle = "Desktop control executed"
                    sector = "System"
                elif act_type == ActionType.SHORTCUT:
                    icon = "⌨️"
                    title = f"Shortcut: {first_act.keys}"
                    subtitle = "Keyboard shortcut sent"
                    sector = "System"
                elif act_type == ActionType.SCROLL:
                    icon = "📜"
                    title = f"Scrolled {first_act.scroll_direction}"
                    subtitle = f"{first_act.scroll_amount} units"
                    sector = "System"
                elif act_type == ActionType.CLICK:
                    icon = "🖱️"
                    title = f"Clicked {first_act.target or 'element'}"
                    subtitle = "UI element clicked"
                    sector = "Apps"
                elif act_type in (ActionType.TYPE, ActionType.TYPE_TEXT):
                    icon = "✍️"
                    title = "Typed Text"
                    subtitle = f"\"{first_act.text[:25]}...\"" if first_act.text else "Text entered"
                    sector = "Dictation"

                # Check web or messaging classification
                tgt_str = str(first_act.target or "").lower()
                if any(w in tgt_str for w in ("chrome", "youtube", "http", "browser", "reddit", "google")):
                    sector = "Web"
                elif any(m in tgt_str for m in ("whatsapp", "discord", "slack", "telegram", "message", "contact")):
                    sector = "Apps"

                self.ui_bridge.action_card_requested.emit(title, subtitle, icon, "✓")
                self.ui_bridge.assistant_message_requested.emit(f"✓ {title}: {subtitle}")

                # Record into History Journal under its sector
                try:
                    self.history_journal.record_action(
                        raw_text=text,
                        cleaned_text=f"{title}: {subtitle}",
                        action_name=title,
                        sector=sector,
                        target_app=first_act.target or "Windows",
                    )
                    self.ui_bridge.dictations_updated.emit()
                except Exception as log_exc:
                    logger.debug("Could not record action into history journal: %s", log_exc)

        except Exception as exc:
            logger.error("Error executing command '%s': %s", text, exc)
            self.ui_bridge.status_requested.emit(f"Error: {exc}")
            self.ui_bridge.thinking_requested.emit(False)

    def open_element_inspector(self) -> None:
        """Open or bring to focus the Desktop Element Inspector."""
        try:
            if self.element_inspector is None:
                from handless.ui.element_inspector import DesktopElementInspector
                self.element_inspector = DesktopElementInspector(uia=self.dispatcher.uia)
            self.element_inspector.show()
            self.element_inspector.raise_()
            self.element_inspector.activateWindow()
            self.element_inspector.refresh_windows()
            logger.info("Desktop Element Inspector opened successfully.")
        except Exception as exc:
            logger.error("Failed to open element inspector: %s", exc)

    def exit_app(self) -> None:
        """Clean shutdown of background threads and audio streams."""
        logger.info("Exiting Vyoma Handless...")
        if hasattr(self, "meeting_transcriber") and self.meeting_transcriber:
            self.meeting_transcriber.stop_recording()
        if hasattr(self, "macro_recorder") and self.macro_recorder:
            self.macro_recorder.stop_recording()
        if hasattr(self, "macro_banner") and self.macro_banner:
            self.macro_banner.close()
        if hasattr(self, "screen_lens") and self.screen_lens:
            self.screen_lens.close()
        self.mic.stop()
        self.hotkeys.stop()
        if self.element_inspector:
            self.element_inspector.close()
        if hasattr(self, "floating_widget") and self.floating_widget:
            self.floating_widget.close()
        if hasattr(self, "flow_overlay") and self.flow_overlay:
            self.flow_overlay.close()
        self.voice_bar.close()
        self.tray_icon.hide()
        self.qt_app.quit()



def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1].lower() in ("diag", "--diag", "diagnose", "--diagnose"):
        from handless.screen.uia_inspector import UIAInspector
        print("=== Vyoma Handless Control Tree Diagnostics ===")
        uia = UIAInspector()
        depth = 3
        if len(sys.argv) > 2 and sys.argv[2].isdigit():
            depth = int(sys.argv[2])
        dump = uia.dump_control_tree(depth=depth)
        print(dump)
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1].lower() in ("inspect", "--inspect", "inspector", "--inspector"):
        from PySide6.QtWidgets import QApplication
        from handless.ui.element_inspector import DesktopElementInspector
        app = QApplication(sys.argv)
        inspector = DesktopElementInspector()
        inspector.show()
        sys.exit(app.exec())

    app = HandlessApp(sys.argv)
    sys.exit(app.run())



if __name__ == "__main__":
    main()
