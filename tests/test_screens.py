"""Unit and integration tests for all 6 screens in Vyoma Handless.

Tests:
1. ChatScreenView & MultiStepPlanCard
2. ExploreScreenView & PromoBannerCard
3. ThunderScreenView & ModernMiniToggle
4. FilesScreenView & StorageProgressBar
5. HistoryScreenView & TimelineNodeWidget & TimelineRowWidget
6. 3D Illustrations (Hero, Thunder, Files, History)
7. SidebarWindow multi-screen navigation and command routing
"""

import os
import pytest
from PySide6.QtWidgets import QApplication

from handless.ui.screens import (
    ChatScreenView,
    ExploreScreenView,
    Files3DIllustration,
    FilesScreenView,
    Hero3DIllustration,
    History3DIllustration,
    HistoryScreenView,
    MultiStepPlanCard,
    SettingsScreenView,
    Thunder3DIllustration,
    ThunderScreenView,
)
from handless.ui.screens.history_view import TimelineNodeWidget, TimelineRowWidget
from handless.ui.screens.thunder_view import ModernMiniToggle
from handless.ui.sidebar import SidebarWindow


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_illustrations(qapp):
    hero = Hero3DIllustration()
    assert hero.width() == 110
    p0 = hero._phase
    hero._on_tick()
    assert hero._phase != p0

    thunder = Thunder3DIllustration()
    assert thunder.width() == 110
    p0 = thunder._phase
    thunder._on_tick()
    assert thunder._phase != p0

    files = Files3DIllustration()
    assert files.width() == 110
    p0 = files._phase
    files._on_tick()
    assert files._phase != p0

    history = History3DIllustration()
    assert history.width() == 110
    p0 = history._phase
    history._on_tick()
    assert history._phase != p0


def test_chat_screen_view(qapp):
    submitted = []
    view = ChatScreenView()
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Add messages
    view.add_user_message("Open Chrome")
    view.add_assistant_message("Opening Chrome now")
    assert view.chat_layout.count() >= 4

    # Test MultiStepPlanCard
    plan_cards = view.findChildren(MultiStepPlanCard)
    assert len(plan_cards) >= 1
    plan = plan_cards[0]
    assert plan is not None

    # Test prompt field submission
    view.input_field.setText("new search")
    view._handle_enter()
    assert "new search" in submitted


def test_explore_screen_view(qapp):
    submitted = []
    view = ExploreScreenView()
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Verify category pills
    assert len(view.filter_buttons) == 6
    view._set_active_filter(view.filter_buttons[1])

    # Verify search input
    view._handle_search("Chrome")
    assert any("Chrome" in s for s in submitted)

    # Verify prompt submission
    view.input_field.setText("explore more")
    view._handle_enter()
    assert "explore more" in submitted


def test_thunder_screen_view(qapp):
    submitted = []
    view = ThunderScreenView()
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Verify filter tabs
    assert len(view.tab_buttons) == 4
    view._select_tab("Templates")

    # Verify toggle switch
    toggle = view.findChild(ModernMiniToggle)
    assert toggle is not None
    initial = toggle.is_checked()
    toggle.set_checked(not initial)
    assert toggle.is_checked() != initial

    # Verify prompt submission
    view.input_field.setText("automate clean downloads")
    view._handle_enter()
    assert "automate clean downloads" in submitted


def test_files_screen_view(qapp):
    submitted = []
    view = FilesScreenView()
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Verify category buttons
    assert len(view.pill_btns) == 6
    view._select_pill(view.pill_btns[1])

    # Verify file action click
    view._handle_file_click("Project_Proposal.pdf")
    assert any("Project_Proposal.pdf" in s for s in submitted)

    # Verify prompt submission
    view.input_field.setText("compress intro video")
    view._handle_enter()
    assert "compress intro video" in submitted


def test_history_screen_view(qapp):
    submitted = []
    view = HistoryScreenView()
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Verify category buttons (All, Dictation, Apps, Files, Web, System, Automation)
    assert len(view.cat_buttons) == 7
    view._filter_category("Apps")

    # Verify timeline row clicks
    timeline_rows = view.findChildren(TimelineRowWidget)
    assert len(timeline_rows) >= 10  # 8 today + 3 yesterday
    first_row = timeline_rows[0]
    first_row.clicked.emit(first_row.task_title)
    assert first_row.task_title in submitted

    # Verify prompt submission
    view.input_field.setText("show past errors")
    view._handle_enter()
    assert "show past errors" in submitted


def test_sidebar_multi_screen_navigation(qapp):
    submitted = []
    sidebar = SidebarWindow(
        on_command_submitted=lambda cmd: submitted.append(cmd),
        width=400,
    )

    # 1. Default page is Home (index 0)
    assert sidebar.view_stack.currentIndex() == 0
    assert sidebar.left_rail._active_tab == "home"

    # 2. Switch to Chat (index 1)
    sidebar._show_chat_view()
    assert sidebar.view_stack.currentIndex() == 1
    assert sidebar.left_rail._active_tab == "chat"
    assert sidebar.cmd_input == sidebar.chat_screen_view.input_field

    # 3. Switch to Explore (index 2)
    sidebar._show_explore_view()
    assert sidebar.view_stack.currentIndex() == 2
    assert sidebar.left_rail._active_tab == "apps"
    assert sidebar.cmd_input == sidebar.explore_screen_view.input_field

    # 4. Switch to Thunder (index 3)
    sidebar._show_thunder_view()
    assert sidebar.view_stack.currentIndex() == 3
    assert sidebar.left_rail._active_tab == "lightning"
    assert sidebar.cmd_input == sidebar.thunder_screen_view.input_field

    # 5. Switch to Files (index 4)
    sidebar._show_files_view()
    assert sidebar.view_stack.currentIndex() == 4
    assert sidebar.left_rail._active_tab == "folder"
    assert sidebar.cmd_input == sidebar.files_screen_view.input_field

    # 6. Switch to History (index 5)
    sidebar._show_history_view()
    assert sidebar.view_stack.currentIndex() == 5
    assert sidebar.left_rail._active_tab == "clock"
    assert sidebar.cmd_input == sidebar.history_screen_view.input_field

    # 7. Switch to Settings (index 6)
    sidebar._show_settings_view()
    assert sidebar.view_stack.currentIndex() == 6
    assert sidebar.cmd_input == sidebar.settings_screen_view.input_field

    # 8. Submitting a command auto-switches to Chat view
    sidebar._submit_text_command("Launch edge browser")
    assert sidebar.view_stack.currentIndex() == 1
    assert "Launch edge browser" in submitted


def test_settings_screen_view(qapp, monkeypatch):
    from PySide6.QtWidgets import QLineEdit

    saved_keys = {}

    def mock_store_gemini(key):
        saved_keys["gemini"] = key
        return True

    def mock_store_groq(key):
        saved_keys["groq"] = key
        return True

    monkeypatch.setattr("handless.ui.screens.settings_view.store_gemini_api_key", mock_store_gemini)
    monkeypatch.setattr("handless.ui.screens.settings_view.store_groq_api_key", mock_store_groq)

    view = SettingsScreenView()

    # 1. Verify Sub-nav items
    assert len(view.nav_buttons) == 9

    # Switch to Voice sub-nav (index 1)
    view._select_nav_tab(1)
    assert view.content_stack.currentIndex() == 1
    assert view.nav_buttons[1].is_active is True

    # Switch to About sub-nav (index 8)
    view._select_nav_tab(8)
    assert view.content_stack.currentIndex() == 8
    assert view.nav_buttons[8].is_active is True

    # Switch back to AI Models (index 0)
    view._select_nav_tab(0)
    assert view.content_stack.currentIndex() == 0
    assert view.nav_buttons[0].is_active is True

    # 2. Test Gemini API Key Show/Hide toggle
    assert view.gemini_input.echoMode() == QLineEdit.EchoMode.Password
    view._toggle_show_gemini_key()
    assert view.gemini_input.echoMode() == QLineEdit.EchoMode.Normal
    view._toggle_show_gemini_key()
    assert view.gemini_input.echoMode() == QLineEdit.EchoMode.Password

    # 3. Test Groq API Key Show/Hide toggle
    assert view.groq_input.echoMode() == QLineEdit.EchoMode.Password
    view._toggle_show_groq_key()
    assert view.groq_input.echoMode() == QLineEdit.EchoMode.Normal
    view._toggle_show_groq_key()
    assert view.groq_input.echoMode() == QLineEdit.EchoMode.Password

    # 4. Test storing Gemini Key
    view.gemini_input.setText("AIzaSyTestGeminiKey12345")
    view._handle_store_gemini_key()
    assert saved_keys.get("gemini") == "AIzaSyTestGeminiKey12345"

    # 5. Test storing Groq Key
    view.groq_input.setText("gsk_TestGroqKey67890")
    view._handle_store_groq_key()
    assert saved_keys.get("groq") == "gsk_TestGroqKey67890"

    # 6. Test combo boxes and toggles
    assert view.tier_combo.count() >= 3
    assert view.gemini_combo.count() >= 3
    assert view.groq_combo.count() >= 3
    assert view.vision_toggle.is_checked() is True
    assert view.autofallback_toggle.is_checked() is True

    # 7. Test prompt bar submission
    submitted = []
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))
    view.input_field.setText("switch to fast mode")
    view._handle_enter()
    assert "switch to fast mode" in submitted

