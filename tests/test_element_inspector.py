"""Unit tests for Desktop UI Element Inspector and Highlighting Overlay."""

import os
import pytest
from unittest.mock import MagicMock
from PySide6.QtWidgets import QApplication

from handless.ui.element_inspector import DesktopElementInspector, ElementHighlightOverlay


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_element_highlight_overlay(qapp):
    overlay = ElementHighlightOverlay()
    assert not overlay.isVisible()

    rect = {"left": 150, "top": 250, "width": 200, "height": 45}
    overlay.show_element(rect, label="[Button] Send")

    assert overlay.isVisible()
    assert overlay._label == "[Button] Send"
    assert overlay._rect is not None
    assert overlay._rect.width() == 200
    assert overlay._rect.height() == 45

    overlay.hide_overlay()
    assert not overlay.isVisible()
    assert overlay._rect is None


def test_desktop_element_inspector_init_and_windows(qapp):
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = [
        {"title": "Google Chrome", "handle": 12345, "pid": 1111, "wrapper": MagicMock()},
        {"title": "Antigravity IDE", "handle": 67890, "pid": 2222, "wrapper": MagicMock()},
    ]

    inspector = DesktopElementInspector(uia=mock_uia)
    assert "Desktop Element Inspector" in inspector.windowTitle()
    assert inspector.window_combo.count() == 3  # Auto-Detect + 2 windows
    assert "Active Focused Window" in inspector.window_combo.itemText(0)
    assert "Google Chrome" in inspector.window_combo.itemText(1)
    assert "Antigravity IDE" in inspector.window_combo.itemText(2)


def test_desktop_element_inspector_populate_and_filter(qapp):
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = []
    inspector = DesktopElementInspector(uia=mock_uia)

    sample_elements = [
        {
            "name": "Send Button",
            "auto_id": "btn_send",
            "control_type": "Button",
            "is_visible": True,
            "is_enabled": True,
            "rect": {"left": 100, "top": 100, "width": 80, "height": 30},
            "wrapper": MagicMock(),
        },
        {
            "name": "Search Query",
            "auto_id": "txt_search",
            "control_type": "Edit",
            "is_visible": True,
            "is_enabled": True,
            "rect": {"left": 200, "top": 100, "width": 250, "height": 30},
            "wrapper": MagicMock(),
        },
        {
            "name": "Hidden Cancel",
            "auto_id": "btn_cancel",
            "control_type": "Button",
            "is_visible": False,
            "is_enabled": False,
            "rect": {"left": 0, "top": 0, "width": 0, "height": 0},
            "wrapper": MagicMock(),
        },
    ]

    inspector._elements_cache = sample_elements
    inspector._apply_filters()

    # Default is visible_only=True, so 2 visible items
    assert inspector.table.rowCount() == 2
    assert inspector.table.item(0, 1).text() == "Send Button"
    assert inspector.table.item(1, 1).text() == "Search Query"

    # Filter by type: Button
    inspector.type_filter_combo.setCurrentText("Button")
    assert inspector.table.rowCount() == 1
    assert inspector.table.item(0, 1).text() == "Send Button"

    # Search filter
    inspector.type_filter_combo.setCurrentText("All Types")
    inspector.search_input.setText("search")
    assert inspector.table.rowCount() == 1
    assert inspector.table.item(0, 1).text() == "Search Query"

    # Include hidden
    inspector.search_input.clear()
    inspector.cb_visible_only.setChecked(False)
    assert inspector.table.rowCount() == 3


def test_desktop_element_inspector_copy_helpers(qapp):
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = []
    inspector = DesktopElementInspector(uia=mock_uia)

    inspector._selected_element = {
        "name": "Send",
        "auto_id": "btn_send_prompt",
        "control_type": "Button",
        "is_visible": True,
        "is_enabled": True,
        "rect": {"left": 500, "top": 600, "width": 75, "height": 32},
        "wrapper": MagicMock(),
    }

    inspector.copy_voice_command()
    qapp.processEvents()
    assert (QApplication.clipboard().text() or getattr(inspector, "last_copied", "")) == 'click "Send"'

    inspector.copy_automation_id()
    qapp.processEvents()
    assert (QApplication.clipboard().text() or getattr(inspector, "last_copied", "")) == "btn_send_prompt"

    inspector.copy_python_locator()
    qapp.processEvents()
    clip_text = QApplication.clipboard().text() or getattr(inspector, "last_copied", "")
    assert 'auto_id="btn_send_prompt"' in clip_text
    assert 'control_type="Button"' in clip_text


def test_desktop_element_inspector_hover_toggle(qapp):
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = []
    inspector = DesktopElementInspector(uia=mock_uia)

    assert not inspector._hover_timer.isActive()
    inspector.btn_hover.setChecked(True)
    inspector._toggle_hover_mode(True)
    assert inspector._hover_timer.isActive()

    inspector.btn_hover.setChecked(False)
    inspector._toggle_hover_mode(False)
    assert not inspector._hover_timer.isActive()

