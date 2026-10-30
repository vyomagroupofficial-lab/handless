"""Unit and integration tests for Gemini 3.8 Live bidirectional calling and Dotted Orb."""

import os
import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPainter
from PySide6.QtWidgets import QApplication

from handless.actions.dispatcher import ActionDispatcher
from handless.intelligence.local_parser import LocalRuleParser
from handless.ui.screens.live_call_view import DottedFluidOrbWidget, LiveCallScreenView
from handless.ui.sidebar import SidebarWindow
from handless.voice.gemini_live import (
    MODEL_GEMINI_LIVE,
    MODEL_GEMINI_LIVE_THINKING,
    GeminiLiveSession,
    build_desktop_live_tools,
)


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_gemini_live_tool_declarations():
    """Verify all desktop tools are declared with proper parameter schemas."""
    tools = build_desktop_live_tools()
    assert len(tools) > 0
    fn_declarations = tools[0].function_declarations
    fn_names = {fn.name for fn in fn_declarations}

    expected_tools = {
        "launch_application",
        "close_application",
        "click_ui_element",
        "type_text",
        "press_keyboard_shortcut",
        "control_window",
        "set_volume",
        "set_brightness",
        "system_action",
        "switch_browser_tab",
        "inspect_screen",
        "search_web",
        "scroll_page",
        "open_url",
        "execute_desktop_command",
        "end_call",
    }
    for expected in expected_tools:
        assert expected in fn_names, f"Tool {expected} not found in live declarations"


def test_gemini_live_session_initialization():
    """Verify GeminiLiveSession model switching and mute states."""
    dispatcher = ActionDispatcher()
    session = GeminiLiveSession(dispatcher=dispatcher, model_name=MODEL_GEMINI_LIVE)

    assert session.model_name == MODEL_GEMINI_LIVE
    assert session.is_active is False
    assert session.is_muted is False

    # Switch to thinking model
    session.switch_model(MODEL_GEMINI_LIVE_THINKING)
    assert session.model_name == MODEL_GEMINI_LIVE_THINKING

    # Test Mute
    session.set_muted(True)
    assert session.is_muted is True
    session.set_muted(False)
    assert session.is_muted is False


def test_dotted_fluid_orb_widget(qapp):
    """Verify DottedFluidOrbWidget state changes and offscreen rendering."""
    orb = DottedFluidOrbWidget(size=160)
    orb.set_level(0.75)
    assert orb._target_level == 0.75

    orb.set_state(is_live=True, is_speaking=True, is_thinking=False)
    assert orb._is_speaking is True

    # Render on offscreen canvas to verify paintEvent stability
    img = QImage(160, 160, QImage.Format.Format_ARGB32_Premultiplied)
    orb.render(img)
    assert not img.isNull()
    orb.close()


def test_live_call_screen_view(qapp):
    """Verify LiveCallScreenView UI components, duration timer, and tool banners."""
    view = LiveCallScreenView()
    view.show()

    # Model switch toggle
    assert view._current_model == MODEL_GEMINI_LIVE
    view._toggle_model()
    assert view._current_model == MODEL_GEMINI_LIVE_THINKING
    assert "Extended Thinking" in view.model_pill.text()
    view._toggle_model()
    assert view._current_model == MODEL_GEMINI_LIVE

    # Call timer
    view.start_call_timer()
    assert view._duration_timer.isActive()
    view.stop_call_timer()
    assert not view._duration_timer.isActive()

    # Tool activity display
    view.show_tool_activity("launch_application", "running", "Chrome")
    assert view.tool_banner.isVisible()
    assert "Launch Application" in view.tool_text.text()

    view.show_tool_activity("launch_application", "done", "Opened Chrome")
    assert "Opened Chrome" in view.tool_text.text()

    # Mute toggle
    view._on_mute_clicked()
    assert view._is_muted is True
    view._on_mute_clicked()
    assert view._is_muted is False

    view.close()


def test_local_parser_live_call_intents():
    """Verify natural language voice commands for live calls."""
    parser = LocalRuleParser()

    res = parser.interpret("start live call")
    assert res is not None
    assert res.actions[0].system_action == "sidebar_call"

    res = parser.interpret("call gemini")
    assert res is not None
    assert res.actions[0].system_action == "sidebar_call"

    res = parser.interpret("live voice call")
    assert res is not None
    assert res.actions[0].system_action == "sidebar_call"

    res = parser.interpret("end call")
    assert res is not None
    assert res.actions[0].system_action == "end_call"

    res = parser.interpret("hang up")
    assert res is not None
    assert res.actions[0].system_action == "end_call"


def test_sidebar_live_call_toggle(qapp):
    """Verify SidebarWindow transitions smoothly to Page 7 during a live call."""
    sidebar = SidebarWindow(width=440)
    sidebar.show()

    # Header has call button
    assert hasattr(sidebar, "call_btn")

    # Start Call
    sidebar.start_live_call()
    assert sidebar.view_stack.currentIndex() == 7
    assert sidebar._is_live_call_active is True

    # End Call
    sidebar.end_live_call()
    assert sidebar.view_stack.currentIndex() == 0
    assert sidebar._is_live_call_active is False

    # Toggle Call
    sidebar.toggle_live_call()
    assert sidebar.view_stack.currentIndex() == 7
    sidebar.toggle_live_call()
    assert sidebar.view_stack.currentIndex() == 0

    sidebar.close()


def test_gemini_live_desktop_tools_execution():
    """Verify GeminiLiveSession can synchronously execute desktop actions."""
    dispatcher = ActionDispatcher()
    session = GeminiLiveSession(dispatcher=dispatcher, model_name=MODEL_GEMINI_LIVE)

    # Test type_text tool
    res = session._execute_tool_sync("type_text", {"text": "Hello Handless"})
    assert "Typed 'Hello Handless'" in res

    # Test system_action tool
    res = session._execute_tool_sync("system_action", {"action": "light_mode"})
    assert "Light mode" in res

    # Test execute_desktop_command tool
    res = session._execute_tool_sync("execute_desktop_command", {"command": "set volume to 40"})
    assert "volume" in res.lower() or "executed" in res.lower()


def test_sidebar_border_tracking_no_cutting(qapp):
    """Verify SidebarWindow docks within screen boundaries with 100% visibility."""
    sidebar = SidebarWindow(width=450)
    sidebar.show()
    app = QApplication.instance()
    screen = app.primaryScreen()
    avail = screen.availableGeometry()

    # Dock Right
    sidebar.dock_to_right(animated=False)
    geom_r = sidebar.geometry()
    assert geom_r.right() <= avail.right()
    assert geom_r.left() >= avail.left()

    # Dock Left
    sidebar.dock_to_left(animated=False)
    geom_l = sidebar.geometry()
    assert geom_l.left() >= avail.left()
    assert geom_l.right() <= avail.right()

    sidebar.close()
