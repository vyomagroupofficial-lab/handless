"""Main Application Entry Point for Vyoma Handless.

Orchestrates the PySide6 UI (VoiceBar, SettingsPanel, TrayIcon),
voice capture pipeline, multi-tier intent router, global hotkey manager,
and desktop action dispatcher.
"""

from __future__ import annotations

import logging
import sys
import threading
from typing import Optional

from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication

from handless.actions.dispatcher import ActionDispatcher
from handless.config import AppConfig, load_config
from handless.intelligence.router import IntentRouter
from handless.safety.emergency_stop import emergency_stop
from handless.safety.hotkeys import GlobalHotkeyManager
from handless.ui.settings_panel import SettingsPanel
from handless.ui.tray_icon import HandlessTrayIcon
from handless.ui.voice_bar import VoiceBar
from handless.voice.microphone import MicrophonePipeline
from handless.voice.recognizer import VoskSpeechRecognizer

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("handless")


class SpeechBridge(QObject):
    """Bridge background speech threads to Qt UI main thread via signals."""
    partial_received = Signal(str)
    final_received = Signal(str)


class HandlessApp:
    """Central Application Coordinator."""

    def __init__(self, sys_argv: list[str]) -> None:
        self.qt_app = QApplication(sys_argv)
        self.qt_app.setApplicationName("Vyoma Handless")
        self.qt_app.setQuitOnLastWindowClosed(False)

        # 1. Load User Configuration
        self.config: AppConfig = load_config()

        # 2. Initialize Intelligence & Dispatch Subsystems
        self.router = IntentRouter(mode=self.config.ai.preferred_tier)
        self.dispatcher = ActionDispatcher(
            enable_vision_fallback=self.config.ai.enable_vision_fallback
        )

        # 3. Qt Thread-safe Speech Bridge
        self.bridge = SpeechBridge()
        self.bridge.partial_received.connect(self._handle_partial_ui)
        self.bridge.final_received.connect(self._handle_final_ui)

        # 4. Initialize User Interface
        self.voice_bar = VoiceBar(
            on_mic_toggled=self._on_mic_toggled,
            on_open_settings=self.open_settings,
            on_emergency_stop=self._on_emergency_stop,
        )

        self.tray_icon = HandlessTrayIcon(
            on_toggle_bar=self.toggle_voice_bar,
            on_open_settings=self.open_settings,
            on_exit=self.exit_app,
        )

        self.settings_dialog: Optional[SettingsPanel] = None

        # 5. Initialize Speech Pipeline
        self.recognizer = VoskSpeechRecognizer(
            model_path=self.config.voice.vosk_model_path,
            auto_download=False,
        )
        self.mic = MicrophonePipeline(
            recognizer=self.recognizer,
            vad_aggressiveness=self.config.voice.vad_aggressiveness,
            on_partial=lambda text: self.bridge.partial_received.emit(text),
            on_final=lambda text: self.bridge.final_received.emit(text),
            device_index=self.config.voice.device_index,
        )

        # 6. Global Hotkey Manager
        self.hotkeys = GlobalHotkeyManager(
            on_ptt_pressed=self._on_ptt_pressed,
            on_ptt_released=self._on_ptt_released,
            on_toggle_bar=self.toggle_voice_bar,
        )

    def run(self) -> int:
        """Start all services and run Qt main event loop."""
        logger.info("Starting Vyoma Handless...")

        # Start microphone and global hotkeys
        self.mic.start()
        self.hotkeys.start()

        # Show UI
        self.voice_bar.show()
        self.tray_icon.show()

        logger.info("Vyoma Handless running. Voice bar visible.")
        return self.qt_app.exec()

    def toggle_voice_bar(self) -> None:
        """Show or hide the floating voice control bar."""
        if self.voice_bar.isVisible():
            self.voice_bar.hide()
        else:
            self.voice_bar.show()
            self.voice_bar.raise_()
            self.voice_bar.activateWindow()

    def open_settings(self) -> None:
        """Open the Settings panel dialog."""
        if self.settings_dialog is None:
            self.settings_dialog = SettingsPanel(self.config, parent=None)
            self.settings_dialog.finished.connect(self._on_settings_closed)

        self.settings_dialog.show()
        self.settings_dialog.raise_()
        self.settings_dialog.activateWindow()

    def _on_settings_closed(self) -> None:
        self.settings_dialog = None
        # Re-apply mode and tier
        self.router.mode = self.config.ai.preferred_tier
        self.dispatcher.enable_vision_fallback = self.config.ai.enable_vision_fallback

    def _on_mic_toggled(self, active: bool) -> None:
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

    def _on_emergency_stop(self) -> None:
        self.voice_bar.set_status("⛔ Emergency Stop Active")
        self.mic.set_listening(False)

    def _handle_partial_ui(self, text: str) -> None:
        """Update VoiceBar with streaming partial transcription."""
        self.voice_bar.set_transcript(text)

    def _handle_final_ui(self, text: str) -> None:
        """Process finalized speech transcript and execute actions."""
        if not text:
            return

        self.voice_bar.set_transcript(f'"{text}"')
        self.voice_bar.set_status("Interpreting...")

        # Run interpretation and execution in a worker thread so UI never freezes
        threading.Thread(target=self._process_command_worker, args=(text,), daemon=True).start()

    def _process_command_worker(self, text: str) -> None:
        """Background worker thread for intent routing and desktop execution."""
        try:
            # 1. Gather active context summary for intelligence layer
            summary = self.dispatcher.uia.get_visible_elements_summary(max_elements=15)
            context = {"visible_elements": summary}

            # 2. Interpret intent
            intent = self.router.interpret(text, context=context)
            if not intent or not intent.actions:
                self.voice_bar.set_status("Didn't understand command")
                return

            # Check if emergency stop command
            if intent.actions[0].target == "emergency_stop":
                emergency_stop.trigger(reason="Voice command 'stop'")
                self.voice_bar.set_status("⛔ Stopped")
                return

            # 3. Execute actions via Dispatcher
            def status_cb(status_msg: str) -> None:
                self.voice_bar.set_status(status_msg)

            self.dispatcher.execute_plan(intent.actions, status_callback=status_cb)

        except Exception as exc:
            logger.error("Error executing command '%s': %s", text, exc)
            self.voice_bar.set_status(f"Error: {exc}")

    def exit_app(self) -> None:
        """Clean shutdown of background threads and audio streams."""
        logger.info("Exiting Vyoma Handless...")
        self.mic.stop()
        self.hotkeys.stop()
        self.voice_bar.close()
        self.tray_icon.hide()
        self.qt_app.quit()


def main() -> None:
    app = HandlessApp(sys.argv)
    sys.exit(app.run())


if __name__ == "__main__":
    main()
