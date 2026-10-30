"""Unit tests for SystemController and fundamental PC actions."""

from unittest.mock import MagicMock, patch
import pytest
from handless.actions.system import SystemController


@pytest.fixture
def system():
    return SystemController()


def test_volume_controls(system):
    with patch("pyautogui.press") as mock_press:
        assert system.volume_up(steps=2) is True
        assert mock_press.call_count == 2
        mock_press.assert_called_with("volumeup")

    with patch("pyautogui.press") as mock_press:
        assert system.volume_down(steps=3) is True
        assert mock_press.call_count == 3
        mock_press.assert_called_with("volumedown")

    with patch("pyautogui.press") as mock_press:
        assert system.toggle_mute() is True
        mock_press.assert_called_once_with("volumemute")


def test_media_controls(system):
    with patch("pyautogui.press") as mock_press:
        assert system.play_pause() is True
        mock_press.assert_called_once_with("playpause")

    with patch("pyautogui.press") as mock_press:
        assert system.next_track() is True
        mock_press.assert_called_once_with("nexttrack")

    with patch("pyautogui.press") as mock_press:
        assert system.prev_track() is True
        mock_press.assert_called_once_with("prevtrack")

    with patch("pyautogui.press") as mock_press:
        assert system.stop_media() is True
        mock_press.assert_called_once_with("stop")


def test_desktop_and_shell_controls(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.show_desktop() is True
        mock_hotkey.assert_called_once_with("win", "d")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.open_task_manager() is True
        mock_hotkey.assert_called_once_with("ctrl", "shift", "esc")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.open_file_explorer() is True
        mock_hotkey.assert_called_once_with("win", "e")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.take_screenshot() is True
        mock_hotkey.assert_called_once_with("win", "shift", "s")


def test_window_snapping_and_desktops(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_left() is True
        mock_hotkey.assert_called_once_with("win", "left")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_right() is True
        mock_hotkey.assert_called_once_with("win", "right")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.next_desktop() is True
        mock_hotkey.assert_called_once_with("ctrl", "win", "right")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.prev_desktop() is True
        mock_hotkey.assert_called_once_with("ctrl", "win", "left")


def test_browser_navigation(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.go_back() is True
        mock_hotkey.assert_called_once_with("alt", "left")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.go_forward() is True
        mock_hotkey.assert_called_once_with("alt", "right")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.address_bar() is True
        mock_hotkey.assert_called_once_with("ctrl", "l")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.next_tab() is True
        mock_hotkey.assert_called_once_with("ctrl", "tab")


def test_mouse_utilities(system):
    with patch("pyautogui.moveTo") as mock_move, patch("pyautogui.size", return_value=(1920, 1080)):
        assert system.move_mouse("center") is True
        mock_move.assert_called_once_with(960, 540)

    with patch("pyautogui.middleClick") as mock_mc:
        assert system.middle_click(coordinates=(400, 300)) is True
        mock_mc.assert_called_once_with(400, 300)

    with patch("pyautogui.moveTo") as mock_mv:
        assert system.hover(coordinates=(500, 600)) is True
        mock_mv.assert_called_once_with(500, 600)


def test_window_corner_snapping_and_monitors(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_top_left() is True
        assert mock_hotkey.call_count == 2

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_top_right() is True
        assert mock_hotkey.call_count == 2

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_bottom_left() is True
        assert mock_hotkey.call_count == 2

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.snap_bottom_right() is True
        assert mock_hotkey.call_count == 2

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.next_monitor() is True
        mock_hotkey.assert_called_once_with("win", "shift", "right")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.prev_monitor() is True
        mock_hotkey.assert_called_once_with("win", "shift", "left")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.minimize_others() is True
        mock_hotkey.assert_called_once_with("win", "home")


def test_browser_extensions(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.duplicate_tab() is True
        assert mock_hotkey.call_count == 2

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.incognito_window() is True
        mock_hotkey.assert_called_once_with("ctrl", "shift", "n")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.hard_refresh() is True
        mock_hotkey.assert_called_once_with("ctrl", "f5")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.view_source() is True
        mock_hotkey.assert_called_once_with("ctrl", "u")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.toggle_bookmarks_bar() is True
        mock_hotkey.assert_called_once_with("ctrl", "shift", "b")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.switch_to_tab(3) is True
        mock_hotkey.assert_called_once_with("ctrl", "3")


def test_media_extensions(system):
    with patch("pyautogui.press") as mock_press:
        assert system.rewind_media(10) is True
        mock_press.assert_called_once_with("left")

    with patch("pyautogui.press") as mock_press:
        assert system.forward_media(10) is True
        mock_press.assert_called_once_with("right")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.playback_faster() is True
        mock_hotkey.assert_called_once_with("shift", ">")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.playback_slower() is True
        mock_hotkey.assert_called_once_with("shift", "<")

    with patch("pyautogui.press") as mock_press:
        assert system.toggle_captions() is True
        mock_press.assert_called_once_with("c")

    with patch("pyautogui.press") as mock_press:
        assert system.theater_mode() is True
        mock_press.assert_called_once_with("t")

    with patch("pyautogui.press") as mock_press:
        assert system.full_screen_media() is True
        mock_press.assert_called_once_with("f")

    with patch("pyautogui.press") as mock_press:
        assert system.mute_media() is True
        mock_press.assert_called_once_with("m")


def test_text_cursor_controls(system):
    with patch("pyautogui.press") as mock_press, patch("pyautogui.hotkey") as mock_hotkey:
        assert system.delete_line() is True
        mock_press.assert_any_call("home")
        mock_hotkey.assert_called_once_with("shift", "end")
        mock_press.assert_any_call("backspace")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.delete_word() is True
        mock_hotkey.assert_called_once_with("ctrl", "backspace")

    with patch("pyautogui.press") as mock_press, patch("pyautogui.hotkey") as mock_hotkey:
        assert system.select_line() is True
        mock_press.assert_called_once_with("home")
        mock_hotkey.assert_called_once_with("shift", "end")

    with patch("pyautogui.press") as mock_press:
        assert system.line_start() is True
        mock_press.assert_called_once_with("home")

    with patch("pyautogui.press") as mock_press:
        assert system.line_end() is True
        mock_press.assert_called_once_with("end")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.page_top() is True
        mock_hotkey.assert_called_once_with("ctrl", "home")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.page_bottom() is True
        mock_hotkey.assert_called_once_with("ctrl", "end")


def test_shell_utilities(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.open_run() is True
        mock_hotkey.assert_called_once_with("win", "r")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.emoji_panel() is True
        mock_hotkey.assert_called_once_with("win", ".")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.game_bar() is True
        mock_hotkey.assert_called_once_with("win", "g")

    with patch("pyautogui.hotkey") as mock_hotkey:
        assert system.quick_settings() is True
        mock_hotkey.assert_called_once_with("win", "a")
