"""Unit tests for Modern Textured and Animated AI Copilot Sidebar."""

import os
import sys
import pytest
from PySide6.QtWidgets import QApplication

from handless.ui.sidebar import (
    ActionCardWidget,
    AnimatedThinkingWidget,
    GradientOrbWidget,
    MessageToolbar,
    SidebarWindow,
    SoundWaveVisualizer,
)


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_gradient_orb_widget(qapp):
    orb = GradientOrbWidget(size=36)
    assert orb.width() == 36
    assert orb.height() == 36
    orb.set_active(True)
    assert orb._is_active is True
    orb.set_active(False)
    assert orb._is_active is False


def test_sound_wave_visualizer(qapp):
    vis = SoundWaveVisualizer(bar_count=4)
    assert vis.bar_count == 4
    vis.set_active(True)
    assert vis._is_active is True
    vis.set_active(False)
    assert vis._is_active is False


def test_action_card_widget(qapp):
    clicked = []
    card = ActionCardWidget(
        title="Top_20_SaaS_Companies.csv",
        subtitle="CSV Generated",
        icon_category="csv",
        btn_label="download",
        on_action=lambda: clicked.append(True),
    )
    assert card is not None
    # Trigger action button click
    btn = card.findChild(ActionCardWidget, "actionCardBtn") or card.layout().itemAt(2).widget()
    btn.click()
    assert len(clicked) == 1


def test_animated_thinking_widget(qapp):
    widget = AnimatedThinkingWidget()
    assert widget.width() == 54
    assert widget.height() == 26
    # Verify animation frame advances
    p0 = widget._phase
    widget._on_tick()
    assert widget._phase != p0


def test_message_toolbar(qapp):
    edited = []
    retried = []
    toolbar = MessageToolbar(
        text="test command",
        on_edit=lambda t: edited.append(t),
        on_retry=lambda t: retried.append(t),
    )
    toolbar._edit()
    assert edited == ["test command"]
    toolbar._retry()
    assert retried == ["test command"]


def test_sidebar_window_creation(qapp):
    submitted = []
    sidebar = SidebarWindow(
        on_command_submitted=lambda cmd: submitted.append(cmd),
        width=380,
    )
    assert sidebar._sidebar_width == 380

    # Add messages
    sidebar.add_user_message("Create a spreadsheet")
    sidebar.add_assistant_message("Here is your sheet")
    sidebar.add_action_card("Sheet.xlsx", "Created", "sheet", "download")

    # Verify thinking indicator toggle
    sidebar.show_thinking(True)
    assert sidebar._thinking_widget is not None
    sidebar.show_thinking(False)
    assert sidebar._thinking_widget is None

    # Test text submission
    sidebar._submit_text_command("open chrome")
    assert "open chrome" in submitted

    # Mode toggle
    sidebar.set_dictation_mode(True)
    assert sidebar._is_dictation is True
    sidebar.set_dictation_mode(False)
    assert sidebar._is_dictation is False

    # Clear chat
    sidebar.clear_chat()
    assert sidebar.chat_layout.count() >= 1


def test_sidebar_revamp_components(qapp):
    from handless.ui.sidebar import (
        ModernToggleSwitch,
        Hero3DIllustration,
        LeftNavRail,
        PromptInputCard,
        RecentActivityWidget,
        BottomStatusPill,
    )

    # 1. Modern Toggle Switch
    sw = ModernToggleSwitch(checked=True)
    assert sw.is_checked() is True
    sw.set_checked(False)
    assert sw.is_checked() is False

    # 2. Hero 3D Illustration
    hero = Hero3DIllustration()
    assert hero.width() == 115
    assert hero.height() == 115

    # 3. Left Navigation Rail
    rail = LeftNavRail()
    assert rail.width() == 52
    assert rail._active_tab == "home"
    rail.set_active_tab("chat")
    assert rail._active_tab == "chat"

    # 4. Prompt Input Card
    card_cmds = []
    card = PromptInputCard()
    card.command_submitted.connect(lambda c: card_cmds.append(c))
    card.input_field.setText("take a screenshot")
    card._handle_enter()
    assert card_cmds == ["take a screenshot"]

    # 5. Recent Activity Feed
    recent = RecentActivityWidget()
    assert recent.empty_label is not None
    recent.add_recent("Opened YouTube", "Just now", "open youtube")
    assert recent.empty_label is None
    assert recent.items_layout.count() == 1

    # 6. Bottom Status Pill
    modes = []
    pill = BottomStatusPill()
    pill.mode_toggled.connect(lambda m: modes.append(m))
    pill.set_listening_state(True)
    assert pill.listen_label.text() == "Listening"
    pill.set_listening_state(False)
    assert pill.listen_label.text() == "Ready"

