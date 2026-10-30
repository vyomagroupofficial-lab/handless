"""Integration tests for Enhanced Desktop & Browser Element Inspector."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtWidgets import QApplication

from handless.ui.element_inspector import DesktopElementInspector, ElementHighlightOverlay


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dual_view_tabs_and_web_filter(qapp):
    """Verifies TabWidget switching and Web-Only filter."""
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = []
    inspector = DesktopElementInspector(uia=mock_uia)

    # Check Dual Tabs
    assert inspector.tab_widget.count() == 2
    assert "Table View" in inspector.tab_widget.tabText(0)
    assert "Tree View" in inspector.tab_widget.tabText(1)

    # Populate elements with both [APP] and [WEB] items
    elements = [
        {
            "name": "Desktop Menu",
            "control_type": "MenuItem",
            "source_tag": "[APP]",
            "is_web_content": False,
            "is_visible": True,
            "is_enabled": True,
            "rect": {"left": 10, "top": 10, "width": 50, "height": 20},
            "wrapper": MagicMock(),
        },
        {
            "name": "WhatsApp Chat Item",
            "control_type": "ListItem",
            "source_tag": "[WEB]",
            "is_web_content": True,
            "is_visible": True,
            "is_enabled": True,
            "rect": {"left": 200, "top": 300, "width": 200, "height": 50},
            "wrapper": MagicMock(),
        },
    ]

    inspector._elements_cache = elements
    inspector._apply_filters()
    assert inspector.table.rowCount() == 2

    # Filter: Web Elements Only
    inspector.cb_web_only.setChecked(True)
    assert inspector.table.rowCount() == 1
    assert inspector.table.item(0, 1).text() == "WhatsApp Chat Item"
    assert inspector.table.item(0, 5).text() == "[WEB]"


def test_lazy_tree_view_expansion(qapp):
    """Verifies lazy child loading when tree item is expanded."""
    mock_uia = MagicMock()
    mock_uia.get_top_level_windows.return_value = []

    mock_win = MagicMock()
    mock_win.window_text.return_value = "Chrome"
    mock_win.rectangle.return_value = MagicMock(left=0, top=0, width=lambda: 1200, height=lambda: 800)

    # Mock children for lazy loading
    child_mock = MagicMock()
    child_mock.window_text.return_value = "Search Box"
    child_mock.friendly_class_name.return_value = "Edit"
    child_mock.automation_id.return_value = "search_bar"
    child_mock.is_visible.return_value = True
    child_mock.is_enabled.return_value = True
    child_mock.rectangle.return_value = MagicMock(left=100, top=100, width=lambda: 200, height=lambda: 30)

    mock_uia.get_element_children.return_value = [
        {
            "name": "Search Box",
            "auto_id": "search_bar",
            "control_type": "Edit",
            "is_visible": True,
            "is_enabled": True,
            "rect": {"left": 100, "top": 100, "width": 200, "height": 30},
            "wrapper": child_mock,
        }
    ]

    inspector = DesktopElementInspector(uia=mock_uia)
    inspector._populate_tree_view(mock_win, "Google Chrome")

    assert inspector.tree.topLevelItemCount() == 1
    root = inspector.tree.topLevelItem(0)
    assert "Google Chrome" in root.text(0)

    # Expanding root triggers lazy load
    inspector._on_tree_item_expanded(root)
    assert root.childCount() == 1
    child_item = root.child(0)
    assert "Search Box" in child_item.text(0)
    assert child_item.text(1) == "Edit"


def test_playground_actions_and_macro_copy(qapp):
    """Tests 1-click playground actions (click, scroll, highlight, copy macro)."""
    mock_uia = MagicMock()
    inspector = DesktopElementInspector(uia=mock_uia)

    elem = {
        "name": "Send Button",
        "auto_id": "btn_send",
        "control_type": "Button",
        "is_visible": True,
        "is_enabled": True,
        "rect": {"left": 400, "top": 500, "width": 80, "height": 35},
        "wrapper": MagicMock(),
    }
    inspector._selected_element = elem
    inspector._update_detail_card(elem)

    # 1. Test Click
    inspector.test_click_element()
    assert "Clicked 'Send Button'" in inspector.status_lbl.text()

    # 2. Scroll into view
    inspector.scroll_into_view()
    assert "Element" in inspector.status_lbl.text()

    # 3. Highlight on screen
    inspector.highlight_selected_element()
    assert inspector.overlay.isVisible()

    # 4. Copy Macro Action
    inspector.copy_macro_action()
    qapp.processEvents()
    clip_text = QApplication.clipboard().text() or getattr(inspector, "last_copied", "")
    assert "Send Button" in clip_text
    assert '"action": "click"' in clip_text


def test_click_to_select_freeze_in_hover_mode(qapp):
    """Verifies that left-clicking while in hover mode freezes the element and exits hover."""
    mock_uia = MagicMock()
    mock_uia.inspect_element_at_point.return_value = {
        "name": "Freeze Target",
        "auto_id": "target_1",
        "control_type": "Button",
        "is_visible": True,
        "is_enabled": True,
        "rect": {"left": 250, "top": 350, "width": 100, "height": 40},
        "wrapper": MagicMock(window_text=lambda: "App Window"),
    }

    inspector = DesktopElementInspector(uia=mock_uia)
    inspector._toggle_hover_mode(True)
    assert inspector._hover_timer.isActive()

    # Simulate mouse click (GetAsyncKeyState returns high bit set)
    with patch("ctypes.windll.user32.GetAsyncKeyState", return_value=0x8000):
        inspector._on_hover_tick()

    # Hover mode should be automatically disengaged, and element locked!
    assert not inspector._hover_timer.isActive()
    assert inspector._selected_element is not None
    assert inspector._selected_element["name"] == "Freeze Target"
    assert "Locked element" in inspector.status_lbl.text()
