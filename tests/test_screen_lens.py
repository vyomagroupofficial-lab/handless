"""Unit tests for Universal Screen Lens Overlay (Win + Shift + Space)."""

import pytest
from PySide6.QtWidgets import QApplication

from handless.ui.screen_lens import ScreenLensOverlay, get_foreground_window_info


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_get_foreground_window_info():
    info = get_foreground_window_info()
    assert isinstance(info, dict)
    assert "title" in info
    assert "rect" in info


def test_screen_lens_overlay_init_and_chips(qapp):
    overlay = ScreenLensOverlay()
    overlay.show()
    assert overlay.pill_bar is not None
    assert overlay.query_input is not None
    assert overlay.target_badge is not None
    assert overlay.answer_card is not None

    # Verify query submission signal
    submitted = []
    overlay.query_submitted.connect(lambda q: submitted.append(q))
    overlay.ask_question("Explain this error in my terminal")

    assert len(submitted) == 1
    assert submitted[0] == "Explain this error in my terminal"
    assert not overlay.answer_card.isHidden()
    assert "Analyzing" in overlay.answer_text.toPlainText()

    overlay.close_lens()
    assert not overlay.isVisible()
    overlay.close()
