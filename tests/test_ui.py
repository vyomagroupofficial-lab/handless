import os
import pytest
from PySide6.QtWidgets import QApplication
from handless.config import AppConfig
from handless.ui.voice_bar import VoiceBar
from handless.ui.settings_panel import SettingsPanel
from handless.ui.styles import CREAM_PALETTE


@pytest.fixture(scope="session")
def qapp():
    # Set offscreen platform for headless CI / testing environment
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_voice_bar_instantiation(qapp):
    toggled = []
    stopped = []

    bar = VoiceBar(
        on_mic_toggled=lambda active: toggled.append(active),
        on_emergency_stop=lambda: stopped.append(True),
    )

    assert bar.transcript_label.text() == "Hold Ctrl+Space to speak"
    assert bar.status_label.text() == "Ready"

    # Test thread-safe signals
    bar.set_transcript("Testing live transcription...")
    qapp.processEvents()
    assert bar.transcript_label.text() == "Testing live transcription..."

    bar.set_status("Executing action...")
    qapp.processEvents()
    assert bar.status_label.text() == "Executing action..."

    bar.set_listening(True)
    qapp.processEvents()
    assert bar._is_listening is True

    # Test typed command submission
    submitted = []
    bar.on_command_submitted = lambda cmd: submitted.append(cmd)
    bar.cmd_input.setText("close whatsapp")
    bar._handle_cmd_enter()
    assert submitted == ["close whatsapp"]

    bar.close()


def test_sidebar_window_instantiation(qapp):
    from handless.ui.sidebar import SidebarWindow
    submitted = []
    sidebar = SidebarWindow(
        on_command_submitted=lambda cmd: submitted.append(cmd),
    )
    assert sidebar.windowTitle() == "Vyoma Handless — Desktop Copilot"
    sidebar.add_user_message("hello")
    sidebar.add_assistant_message("hi there")
    sidebar.close()


def test_settings_panel_instantiation(qapp):
    cfg = AppConfig()
    panel = SettingsPanel(cfg)
    assert panel.windowTitle() == "Vyoma Handless — Settings"
    assert panel.tabs.count() == 4
    panel.close()
