"""Unit tests for Wispr Flow Floating HUD Pill Overlay."""

import os
import pytest
from PySide6.QtWidgets import QApplication

from handless.dictation.flow_overlay import WisprFlowOverlay


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_wispr_flow_overlay_states(qapp):
    overlay = WisprFlowOverlay()
    assert overlay._state == "idle"
    assert not overlay.isVisible()

    # 1. Start Flow (Hold Ctrl+Shift)
    overlay.start_flow()
    assert overlay._state == "listening"
    assert overlay.isVisible()
    assert "Flow Dictating" in overlay.status_lbl.text()
    assert overlay.orb._is_active is True
    assert overlay.wave._is_active is True

    # 2. Transcribing Flow (Release Ctrl+Shift)
    overlay.transcribing_flow()
    assert overlay._state == "transcribing"
    assert "Transcribing" in overlay.status_lbl.text()
    assert overlay.wave._is_active is False

    # 3. Finish Flow (Pasting text)
    overlay.finish_flow("hello world")
    assert overlay._state == "done"
    assert "hello world" in overlay.status_lbl.text()

    # 4. Cancel / Dismiss
    overlay.cancel_flow()

