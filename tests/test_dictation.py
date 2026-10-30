import pytest
from unittest.mock import patch, MagicMock
from handless.dictation.text_cleaner import (
    clean_spoken_text,
    format_spoken_punctuation,
    remove_filler_words,
    fix_capitalization,
)
from handless.dictation.paste_controller import (
    is_terminal_window,
    PasteController,
    paste_text,
)
from handless.intelligence.groq_client import GroqInterpreter
from handless.intelligence.models import ActionType


def test_format_spoken_punctuation():
    raw = "hello comma world period how are you question mark"
    formatted = format_spoken_punctuation(raw)
    assert formatted == "hello, world. how are you?"


def test_remove_filler_words():
    raw = "um so like I was uh thinking you know about this"
    cleaned = remove_filler_words(raw)
    assert "um" not in cleaned.split()
    assert "uh" not in cleaned.split()
    assert "you know" not in cleaned


def test_fix_capitalization():
    raw = "hello world. this is a test! is it working? yes it is."
    fixed = fix_capitalization(raw)
    assert fixed.startswith("Hello")
    assert "This is" in fixed
    assert "Is it working?" in fixed
    assert "Yes it is." in fixed


def test_clean_spoken_text_end_to_end():
    spoken = "um hello world comma this is vyoma handless period new line are you ready question mark"
    result = clean_spoken_text(spoken)
    assert "Hello world," in result
    assert "this is vyoma handless." in result
    assert "\n" in result
    assert "Are you ready?" in result


def test_terminal_detection():
    # True for known terminal executables
    assert is_terminal_window("cmd.exe", "ConsoleWindowClass") is True
    assert is_terminal_window("powershell.exe", "ConsoleWindowClass") is True
    assert is_terminal_window("windowsterminal.exe", "CASCADIA_HOSTING_WINDOW_CLASS") is True
    assert is_terminal_window("wt.exe", "") is True

    # False for standard apps
    assert is_terminal_window("notepad.exe", "Notepad") is False
    assert is_terminal_window("chrome.exe", "Chrome_WidgetWin_1") is False


def test_paste_controller_clipboard_preservation():
    controller = PasteController()

    with patch.object(controller, "_read_clipboard", return_value="existing clipboard content"):
        with patch.object(controller, "_write_clipboard") as mock_write:
            with patch.object(controller, "_send_paste_shortcut") as mock_send:
                success = controller.paste("new spoken text", preserve_clipboard=True)
                assert success is True
                # Should write new text, then restore old text
                assert mock_write.call_count == 2
                assert mock_write.call_args_list[0][0][0] == "new spoken text"
                assert mock_write.call_args_list[1][0][0] == "existing clipboard content"
                mock_send.assert_called_once()


def test_groq_interpreter_is_available():
    groq = GroqInterpreter()
    with patch("handless.intelligence.groq_client.get_groq_api_key", return_value="gsk_test_key_12345678"):
        assert groq.is_available() is True

    with patch("handless.intelligence.groq_client.get_groq_api_key", return_value=None):
        assert groq.is_available() is False


def test_groq_interpreter_parse_actions():
    groq = GroqInterpreter()
    raw = [
        {"action_type": "launch_app", "target": "chrome"},
        {"action_type": "type", "text": "how are you doing"},
    ]
    actions = groq._parse_actions(raw)
    assert len(actions) == 2
    assert actions[0].action_type == ActionType.LAUNCH_APP
    assert actions[0].target == "chrome"
    assert actions[1].action_type == ActionType.TYPE
    assert actions[1].text == "how are you doing"
