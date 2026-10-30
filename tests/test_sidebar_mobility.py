"""Unit and integration tests for Sidebar mobility, docking, dynamic sizing, and unified settings."""

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication

from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType
from handless.ui.floating_widget import FloatingCopilotWidget
from handless.ui.sidebar import SidebarWindow


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sidebar_docking_and_mobility(qapp):
    sidebar = SidebarWindow(width=440)
    sidebar.show()

    # 1. Default dock side is right
    assert sidebar._dock_side == "right"
    assert sidebar._is_wide_mode is False

    # 2. Dock to Left
    dock_events = []
    sidebar.dock_side_changed.connect(lambda side: dock_events.append(side))
    sidebar.dock_to_left(animated=False)
    assert sidebar._dock_side == "left"
    assert "left" in dock_events
    assert sidebar.geometry().x() < 100  # Docked near left edge

    # 3. Dock to Right
    sidebar.dock_to_right(animated=False)
    assert sidebar._dock_side == "right"
    assert "right" in dock_events

    # 4. Toggle Dock Side
    sidebar.toggle_dock_side(animated=False)
    assert sidebar._dock_side == "left"
    sidebar.toggle_dock_side(animated=False)
    assert sidebar._dock_side == "right"

    # 5. Wide Mode Sizing
    w_normal = sidebar.geometry().width()
    sidebar.set_wide_mode(True, animated=False)
    assert sidebar._is_wide_mode is True
    w_wide = sidebar.geometry().width()
    assert w_wide > w_normal  # Expanded width

    sidebar.set_wide_mode(False, animated=False)
    assert sidebar._is_wide_mode is False
    assert sidebar.geometry().width() <= w_wide

    sidebar.close()


def test_sidebar_header_mobility_buttons(qapp):
    sidebar = SidebarWindow(width=440)
    assert hasattr(sidebar, "dock_side_btn")
    assert hasattr(sidebar, "wide_btn")
    assert hasattr(sidebar, "min_btn")
    assert hasattr(sidebar, "settings_btn")
    assert hasattr(sidebar, "close_btn")

    # Click dock side button
    initial_side = sidebar._dock_side
    sidebar.dock_side_btn.click()
    assert sidebar._dock_side != initial_side

    # Click wide view button
    sidebar.wide_btn.click()
    assert sidebar._is_wide_mode is True
    sidebar.wide_btn.click()
    assert sidebar._is_wide_mode is False

    # Click settings button - toggles page 6
    assert sidebar.view_stack.currentIndex() == 0
    sidebar.settings_btn.click()
    assert sidebar.view_stack.currentIndex() == 6
    sidebar.settings_btn.click()
    assert sidebar.view_stack.currentIndex() == 0

    sidebar.close()


def test_floating_widget_dock_side_sync(qapp):
    floating = FloatingCopilotWidget()
    assert floating._dock_side == "right"

    floating.set_dock_side("left")
    assert floating._dock_side == "left"
    assert floating.x() < 100  # Positioned near left edge

    floating.set_dock_side("right")
    assert floating._dock_side == "right"

    floating.close()


def test_local_parser_sidebar_mobility_commands():
    parser = LocalRuleParser()

    # Docking
    res = parser.interpret("dock left")
    assert res.actions[0].system_action == "sidebar_dock_left"

    res = parser.interpret("move sidebar to left")
    assert res.actions[0].system_action == "sidebar_dock_left"

    res = parser.interpret("dock to right")
    assert res.actions[0].system_action == "sidebar_dock_right"

    res = parser.interpret("move out of the way")
    assert res.actions[0].system_action == "sidebar_toggle_dock"

    res = parser.interpret("switch sides")
    assert res.actions[0].system_action == "sidebar_toggle_dock"

    # Sizing
    res = parser.interpret("make wider")
    assert res.actions[0].system_action == "sidebar_expand"

    res = parser.interpret("expand sidebar")
    assert res.actions[0].system_action == "sidebar_expand"

    res = parser.interpret("make narrower")
    assert res.actions[0].system_action == "sidebar_compact"

    res = parser.interpret("compact mode")
    assert res.actions[0].system_action == "sidebar_compact"

    # Floating
    res = parser.interpret("minimize sidebar")
    assert res.actions[0].system_action == "sidebar_float"

    res = parser.interpret("shrink to bot")
    assert res.actions[0].system_action == "sidebar_float"

    # Unified settings
    res = parser.interpret("open settings")
    assert res.actions[0].system_action == "sidebar_settings"

    res = parser.interpret("show settings")
    assert res.actions[0].system_action == "sidebar_settings"

    res = parser.interpret("settings")
    assert res.actions[0].system_action == "sidebar_settings"

    # Auto-fit & Adjust
    res = parser.interpret("fit to side")
    assert res.actions[0].system_action == "sidebar_auto_fit"

    res = parser.interpret("adjust to side")
    assert res.actions[0].system_action == "sidebar_auto_fit"

    res = parser.interpret("snap to side")
    assert res.actions[0].system_action == "sidebar_auto_fit"


def test_sidebar_drag_drop_auto_fit(qapp):
    sidebar = SidebarWindow(width=440)
    sidebar.show()

    screen = qapp.primaryScreen()
    avail = screen.availableGeometry() if screen else None
    screen_w = avail.width() if avail else 1920

    # Move window arbitrarily towards the right half
    sidebar.move(screen_w - 500, 100)
    sidebar._snap_to_nearest_edge(animated=False)
    assert sidebar._dock_side == "right"
    assert sidebar.geometry().y() >= 0

    # Move window arbitrarily towards the left
    sidebar.move(50, 100)
    sidebar._snap_to_nearest_edge(animated=False)
    assert sidebar._dock_side == "left"
    assert sidebar.geometry().x() < 50

    # auto_fit_to_side explicit calls
    sidebar.auto_fit_to_side("right", animated=False)
    assert sidebar._dock_side == "right"

    sidebar.auto_fit_to_side("left", animated=False)
    assert sidebar._dock_side == "left"

    sidebar.close()

