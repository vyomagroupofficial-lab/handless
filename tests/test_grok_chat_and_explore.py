"""Unit and Integration Tests for Grok Chat, In-Chat Self-Configuration, and Explore Screen Overhaul.
"""

import os
import pytest
from PySide6.QtWidgets import QApplication

from handless.config import AppConfig
from handless.intelligence.grok_persona import (
    ConfigProposal,
    detect_config_proposal,
    generate_grok_chat_reply,
    get_offline_grok_reply,
    is_casual_chitchat,
)
from handless.ui.screens.chat_view import (
    ChatHistoryDrawer,
    ChatScreenView,
    HandlessConfigActionCard,
)
from handless.ui.screens.explore_view import (
    CATALOG_DATA,
    ExploreScreenView,
    PromoBannerCard,
)


@pytest.fixture(scope="session")
def qapp():
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# 1. Grok Persona & Chit-Chat Tests
# ---------------------------------------------------------------------------

def test_grok_persona_chitchat_detection():
    # Casual greetings
    assert is_casual_chitchat("hi")
    assert is_casual_chitchat("hello")
    assert is_casual_chitchat("hey!")
    assert is_casual_chitchat("how are you?")
    assert is_casual_chitchat("roast me")
    assert is_casual_chitchat("who are you")
    assert is_casual_chitchat("thank you")

    # Action commands should NOT be detected as chit-chat
    assert not is_casual_chitchat("open chrome")
    assert not is_casual_chitchat("take a screenshot")
    assert not is_casual_chitchat("change shortcut to Ctrl+Alt+D")
    assert not is_casual_chitchat("transcribe meeting")


def test_grok_persona_offline_replies():
    # Verify emojis and savage humor in offline replies
    reply_hi = get_offline_grok_reply("hi")
    assert len(reply_hi) > 10

    reply_roast = get_offline_grok_reply("roast me")
    assert any(w in reply_roast.lower() for w in ("tabs", "wrist", "wall-e", "task manager", "procrastinate", "pc", "desktop"))

    reply_gen = generate_grok_chat_reply("how are you")
    assert len(reply_gen) > 10


# ---------------------------------------------------------------------------
# 2. In-Chat Handless Self-Configuration Detection Tests
# ---------------------------------------------------------------------------

def test_detect_config_proposal_shortcuts():
    cfg = AppConfig()

    # Shortcut proposal
    p1 = detect_config_proposal("change shortcut to Ctrl+Alt+D", cfg)
    assert p1 is not None
    assert p1.setting_key == "hotkeys.toggle_dictation"
    assert "CTRL+ALT+D" in p1.proposed_value.upper()
    assert len(p1.roast_comment) > 5

    # Transform shortcut proposal
    p2 = detect_config_proposal("change rewrite shortcut to Alt+Shift+T", cfg)
    assert p2 is not None
    assert p2.setting_key == "hotkeys.transform_shortcut"
    assert "ALT+SHIFT+T" in p2.proposed_value.upper()


def test_detect_config_proposal_cleanup_level():
    cfg = AppConfig()

    p_clean = detect_config_proposal("set cleanup to high", cfg)
    assert p_clean is not None
    assert p_clean.setting_key == "dictation.cleanup_level"
    assert p_clean.proposed_value == "High"

    p_clean_none = detect_config_proposal("switch cleanup level to none", cfg)
    assert p_clean_none is not None
    assert p_clean_none.proposed_value == "None"


def test_detect_config_proposal_language_and_ui():
    cfg = AppConfig()

    # Language
    p_lang = detect_config_proposal("change dictation language to Spanish", cfg)
    assert p_lang is not None
    assert p_lang.setting_key == "dictation.language"
    assert p_lang.proposed_value == "Spanish"

    # Sidebar width
    p_wide = detect_config_proposal("make sidebar wide", cfg)
    assert p_wide is not None
    assert p_wide.setting_key == "ui.sidebar_width"
    assert "Wide" in p_wide.proposed_value


# ---------------------------------------------------------------------------
# 3. Explore View Dynamic Filtering & Catalog Tests
# ---------------------------------------------------------------------------

def test_explore_dynamic_categories(qapp):
    view = ExploreScreenView()
    view.show()
    submitted = []
    view.command_submitted.connect(lambda cmd: submitted.append(cmd))

    # Initial state is "All"
    assert view.active_category == "All"
    assert not view.promo.isHidden()

    # Switch to "Apps" category
    apps_btn = next(b for b in view.filter_buttons if b.property("category_name") == "Apps")
    view._set_active_filter(apps_btn)
    assert view.active_category == "Apps"
    assert view.promo.isHidden()  # Hero is hidden in specific category view

    # Switch to "Productivity"
    prod_btn = next(b for b in view.filter_buttons if b.property("category_name") == "Productivity")
    view._set_active_filter(prod_btn)
    assert view.active_category == "Productivity"

    # Switch to "Content"
    cont_btn = next(b for b in view.filter_buttons if b.property("category_name") == "Content")
    view._set_active_filter(cont_btn)
    assert view.active_category == "Content"

    # Switch to "System"
    sys_btn = next(b for b in view.filter_buttons if b.property("category_name") == "System")
    view._set_active_filter(sys_btn)
    assert view.active_category == "System"

    # Switch to "Automation"
    auto_btn = next(b for b in view.filter_buttons if b.property("category_name") == "Automation")
    view._set_active_filter(auto_btn)
    assert view.active_category == "Automation"

    # Return to "All"
    view._set_category_by_name("All")
    assert view.active_category == "All"
    assert not view.promo.isHidden()


def test_explore_live_search(qapp):
    view = ExploreScreenView()
    view.show()
    view.explore_search.setText("chrome")
    # Search should show matching cards
    assert view.dynamic_layout.count() > 0

    view.explore_search.setText("")
    # Empty search should restore active category
    assert view.active_category == "All"


# ---------------------------------------------------------------------------
# 4. Chat View Incognito, Drawer, and Allow Proposal Card Tests
# ---------------------------------------------------------------------------

def test_chat_incognito_mode_toggle(qapp):
    chat = ChatScreenView()
    chat.show()
    assert not chat.incognito_mode
    assert chat.incognito_banner.isHidden()

    chat._toggle_incognito()
    assert chat.incognito_mode
    assert not chat.incognito_banner.isHidden()

    chat._toggle_incognito()
    assert not chat.incognito_mode
    assert chat.incognito_banner.isHidden()


def test_chat_history_drawer(qapp):
    chat = ChatScreenView()
    chat.show()
    assert chat.history_drawer.isHidden()

    chat._toggle_history_drawer()
    assert not chat.history_drawer.isHidden()

    chat._toggle_history_drawer()
    assert chat.history_drawer.isHidden()


def test_chat_config_proposal_card_allow(qapp):
    chat = ChatScreenView()
    chat.show()
    applied_events = []
    chat.config_change_applied.connect(lambda k, v: applied_events.append((k, v)))

    proposal = ConfigProposal(
        setting_key="hotkeys.toggle_dictation",
        setting_label="Dictation Shortcut",
        current_value="Ctrl + Shift",
        proposed_value="Ctrl + Alt + D",
        summary="Rebind dictation shortcut",
        roast_comment="Rewiring so you don't break your fingers 💀",
    )

    card = chat.add_config_proposal_card(proposal)
    assert isinstance(card, HandlessConfigActionCard)
    assert not card.btn_row.isHidden()
    assert card.applied_lbl.isHidden()

    # User clicks "Allow & Apply"
    card.allow_btn.click()
    assert len(applied_events) == 1
    assert applied_events[0] == ("hotkeys.toggle_dictation", "Ctrl + Alt + D")
    assert card.btn_row.isHidden()
    assert not card.applied_lbl.isHidden()
    assert "✓" in card.applied_lbl.text()


def test_chat_config_proposal_card_dismiss(qapp):
    chat = ChatScreenView()
    chat.show()
    proposal = ConfigProposal(
        setting_key="dictation.cleanup_level",
        setting_label="Auto Cleanup",
        current_value="Medium",
        proposed_value="High",
        summary="Change cleanup to High",
        roast_comment="Grammar surgery incoming",
    )

    card = chat.add_config_proposal_card(proposal)
    card.dismiss_btn.click()
    assert card.btn_row.isHidden()
    assert "dismissed" in card.applied_lbl.text().lower()
