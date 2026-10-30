"""Unit tests for SystemTools, desktop volume & brightness controls, sidebar docking, and sector tracking.
"""

import pytest
from unittest.mock import MagicMock, patch

from handless.actions.system_tools import SystemTools
from handless.actions.dispatcher import ActionDispatcher
from handless.dictation.history_journal import HistoryJournal, HistoryEntry
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType
from handless.intelligence.groq_client import GroqInterpreter, SYSTEM_PROMPT as GROQ_SYSTEM_PROMPT
from handless.intelligence.gemini_client import GeminiInterpreter, GeminiSingleAction


# ---------------------------------------------------------------------------
# 1. SystemTools Hardware & OS Action Tests
# ---------------------------------------------------------------------------

def test_system_tools_volume_controls():
    with patch("pyautogui.press") as mock_press:
        res = SystemTools.volume_up(steps=3)
        assert res is True
        assert mock_press.call_count == 3
        mock_press.assert_called_with("volumeup")

    with patch("pyautogui.press") as mock_press:
        res = SystemTools.volume_down(steps=2)
        assert res is True
        assert mock_press.call_count == 2
        mock_press.assert_called_with("volumedown")

    with patch("pyautogui.press") as mock_press:
        res = SystemTools.toggle_mute()
        assert res is True
        mock_press.assert_called_with("volumemute")


def test_system_tools_brightness():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = SystemTools.set_brightness(80)
        assert res is True


def test_system_tools_power():
    with patch("ctypes.windll.user32.LockWorkStation") as mock_lock:
        res = SystemTools.lock_pc()
        assert res is True
        assert mock_lock.called

    with patch("ctypes.windll.PowrProf.SetSuspendState") as mock_sleep:
        res = SystemTools.sleep_pc()
        assert res is True
        assert mock_sleep.called


def test_system_tools_theme_and_layout():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        res = SystemTools.set_dark_mode(True)
        assert res is True

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert SystemTools.show_desktop() is True
        mock_hotkey.assert_called_with("win", "d")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert SystemTools.snap_left() is True
        mock_hotkey.assert_called_with("win", "left")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert SystemTools.snap_right() is True
        mock_hotkey.assert_called_with("win", "right")


# ---------------------------------------------------------------------------
# 2. LocalRuleParser Natural Voice Intent Matching
# ---------------------------------------------------------------------------

@pytest.fixture
def parser():
    return LocalRuleParser()


def test_parser_desktop_volume_variations(parser):
    commands = [
        ("set my desktop volume to 100", "set_volume", 100),
        ("set my pc volume to 80%", "set_volume", 80),
        ("turn the desktop volume to 50", "set_volume", 50),
        ("volume 75", "set_volume", 75),
        ("put volume at 40", "set_volume", 40),
        ("zero volume", "set_volume", 0),
        ("min volume", "set_volume", 0),
        ("turn my volume up", "volume_up", 5),
        ("increase desktop volume", "volume_up", 5),
        ("make it louder", "volume_up", 5),
        ("turn my volume down", "volume_down", 5),
        ("lower the desktop volume", "volume_down", 5),
        ("quieter", "volume_down", 5),
        ("mute desktop volume", "mute", None),
        ("unmute", "unmute", None),
    ]
    for phrase, expected_action, expected_amount in commands:
        res = parser.interpret(phrase)
        assert res is not None, f"Failed to match: {phrase}"
        assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
        assert res.actions[0].system_action == expected_action
        if expected_amount is not None:
            assert res.actions[0].scroll_amount == expected_amount


def test_parser_desktop_brightness_variations(parser):
    commands = [
        ("set my pc brightness to 100%", "set_brightness", 100),
        ("set desktop brightness to 80", "set_brightness", 80),
        ("screen brightness to 60", "set_brightness", 60),
        ("dim screen", "set_brightness", 30),
        ("dim the screen", "set_brightness", 30),
        ("decrease brightness", "brightness_down", 15),
        ("turn brightness up", "brightness_up", 15),
        ("make screen brighter", "brightness_up", 15),
        ("max brightness", "set_brightness", 100),
    ]
    for phrase, expected_action, expected_amount in commands:
        res = parser.interpret(phrase)
        assert res is not None, f"Failed to match: {phrase}"
        assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
        assert res.actions[0].system_action == expected_action
        if expected_amount is not None:
            assert res.actions[0].scroll_amount == expected_amount


def test_parser_sidebar_mobility_and_sizing(parser):
    commands = [
        ("dock left", "sidebar_dock_left"),
        ("dock to left", "sidebar_dock_left"),
        ("move sidebar left", "sidebar_dock_left"),
        ("move to left", "sidebar_dock_left"),
        ("put sidebar on left", "sidebar_dock_left"),
        ("dock right", "sidebar_dock_right"),
        ("dock to right", "sidebar_dock_right"),
        ("move sidebar right", "sidebar_dock_right"),
        ("move to right", "sidebar_dock_right"),
        ("put sidebar on right", "sidebar_dock_right"),
        ("make sidebar wide", "sidebar_expand"),
        ("wide mode", "sidebar_expand"),
        ("big sidebar", "sidebar_expand"),
        ("expand sidebar", "sidebar_expand"),
        ("make sidebar small", "sidebar_compact"),
        ("compact mode", "sidebar_compact"),
        ("small sidebar", "sidebar_compact"),
    ]
    for phrase, expected_action in commands:
        res = parser.interpret(phrase)
        assert res is not None, f"Failed to match: {phrase}"
        assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
        assert res.actions[0].system_action == expected_action


# ---------------------------------------------------------------------------
# 3. Cloud LLM System Action Prompt Validation
# ---------------------------------------------------------------------------

def test_groq_system_prompt_includes_system_actions():
    assert "system_action" in GROQ_SYSTEM_PROMPT
    assert "set_volume" in GROQ_SYSTEM_PROMPT
    assert "set_brightness" in GROQ_SYSTEM_PROMPT
    assert "NEVER say" in GROQ_SYSTEM_PROMPT


def test_gemini_action_schema_includes_system_action():
    fields = GeminiSingleAction.model_fields
    assert "system_action" in fields
    act = GeminiSingleAction(
        action_type="system_action",
        system_action="set_volume",
        scroll_amount=80,
    )
    assert act.system_action == "set_volume"
    assert act.scroll_amount == 80


# ---------------------------------------------------------------------------
# 4. History Journal Sector Tracking
# ---------------------------------------------------------------------------

def test_history_journal_sector_recording(tmp_path):
    journal_file = tmp_path / "test_journal.json"
    journal = HistoryJournal(file_path=journal_file)

    # 1. Record dictation
    d_entry = journal.record_dictation("hello world", "Hello world.")
    assert d_entry.sector == "Dictation"

    # 2. Record system action
    s_entry = journal.record_action(
        raw_text="set my desktop volume to 100",
        cleaned_text="System: Set Volume: Desktop control executed",
        action_name="System: Set Volume",
        sector="System",
    )
    assert s_entry.sector == "System"

    # 3. Record app action
    a_entry = journal.record_action(
        raw_text="open whatsapp",
        cleaned_text="Launched WhatsApp",
        action_name="Launched WhatsApp",
        sector="Apps",
    )
    assert a_entry.sector == "Apps"

    # 4. Sector stats computation
    stats = journal.get_sector_stats()
    assert stats["Dictation"] == 1
    assert stats["System"] == 1
    assert stats["Apps"] == 1

    # 5. Filter by sector
    sys_entries = journal.get_entries(sector_filter="System")
    assert len(sys_entries) == 1
    assert sys_entries[0].action_name if hasattr(sys_entries[0], "action_name") else sys_entries[0].sector == "System"

    app_entries = journal.get_entries(sector_filter="Apps")
    assert len(app_entries) == 1
    assert app_entries[0].sector == "Apps"

