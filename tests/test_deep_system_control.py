"""Unit tests for deep hardware, browser, and system control features in Vyoma Handless.
"""

from unittest.mock import MagicMock, patch
import pytest

from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType, ActionRequest
from handless.actions.system import SystemController
from handless.actions.dispatcher import ActionDispatcher


@pytest.fixture
def parser():
    return LocalRuleParser()


@pytest.fixture
def system():
    return SystemController()


# ---------------------------------------------------------------------------
# 1. Local Parser Parsing Tests
# ---------------------------------------------------------------------------

def test_parser_brightness(parser):
    res = parser.interpret("set brightness to 60%")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res.actions[0].system_action == "set_brightness"
    assert res.actions[0].scroll_amount == 60

    res_dim = parser.interpret("dim screen")
    assert res_dim.actions[0].system_action == "set_brightness"
    assert res_dim.actions[0].scroll_amount == 30

    res_max = parser.interpret("max brightness")
    assert res_max.actions[0].system_action == "set_brightness"
    assert res_max.actions[0].scroll_amount == 100

    res_user = parser.interpret("set my brigthenes to 100 now")
    assert res_user is not None
    assert res_user.actions[0].system_action == "set_brightness"
    assert res_user.actions[0].scroll_amount == 100


def test_parser_themes_and_display(parser):
    res_dark = parser.interpret("switch to dark mode")
    assert res_dark.actions[0].system_action == "dark_mode"

    res_light = parser.interpret("enable light mode")
    assert res_light.actions[0].system_action == "light_mode"

    res_toggle = parser.interpret("toggle dark mode")
    assert res_toggle.actions[0].system_action == "toggle_dark_mode"

    res_night = parser.interpret("turn on night light")
    assert res_night.actions[0].system_action == "night_light"

    res_clone = parser.interpret("duplicate displays")
    assert res_clone.actions[0].system_action == "display_mode"
    assert res_clone.actions[0].target == "clone"

    res_ext = parser.interpret("extend desktop")
    assert res_ext.actions[0].system_action == "display_mode"
    assert res_ext.actions[0].target == "extend"


def test_parser_health_and_processes(parser):
    res_bat = parser.interpret("what's my battery percentage")
    assert res_bat.actions[0].system_action == "battery_status"

    res_ram = parser.interpret("which app is using the most ram")
    assert res_ram.actions[0].system_action == "system_health"

    res_kill = parser.interpret("force quit notion")
    assert res_kill.actions[0].system_action == "kill_process"
    assert res_kill.actions[0].target == "notion"

    res_exp = parser.interpret("restart explorer")
    assert res_exp.actions[0].system_action == "restart_explorer"


def test_parser_files_and_folders(parser):
    res_dl = parser.interpret("open latest download")
    assert res_dl.actions[0].system_action == "open_latest_download"

    res_ss = parser.interpret("open latest screenshot")
    assert res_ss.actions[0].system_action == "open_latest_screenshot"

    res_f = parser.interpret("open downloads folder")
    assert res_f.actions[0].system_action == "open_folder"
    assert res_f.actions[0].target == "downloads"

    res_bin = parser.interpret("empty recycle bin")
    assert res_bin.actions[0].system_action == "empty_recycle_bin"


def test_parser_caffeine_and_boss_mode(parser):
    res_caf = parser.interpret("keep screen awake")
    assert res_caf.actions[0].system_action == "keep_awake"

    res_slp = parser.interpret("allow sleep")
    assert res_slp.actions[0].system_action == "allow_sleep"

    res_boss = parser.interpret("boss mode")
    assert res_boss.actions[0].system_action == "boss_mode"

    res_net = parser.interpret("what is my ip address")
    assert res_net.actions[0].system_action == "network_info"


def test_parser_clipboard_and_browser(parser):
    res_paste = parser.interpret("paste as plain text")
    assert res_paste.actions[0].system_action == "paste_plain_text"

    res_clr = parser.interpret("clear clipboard")
    assert res_clr.actions[0].system_action == "clear_clipboard"

    res_tab = parser.interpret("switch to youtube tab")
    assert res_tab.actions[0].system_action == "switch_to_tab"
    assert res_tab.actions[0].target == "youtube"

    res_url = parser.interpret("copy current url")
    assert res_url.actions[0].system_action == "copy_current_url"


# ---------------------------------------------------------------------------
# 2. SystemController Implementation Tests
# ---------------------------------------------------------------------------

def test_system_brightness(system):
    res = system.set_brightness(75)
    assert res is True


def test_system_dark_mode(system):
    # Test checking dark mode without error
    is_dark = system.get_dark_mode()
    assert isinstance(is_dark, bool)


def test_system_battery_status(system):
    status = system.get_battery_status()
    assert isinstance(status, str)
    assert len(status) > 0


def test_system_ram_processes(system):
    info = system.get_top_ram_processes(count=2)
    assert isinstance(info, str)
    assert len(info) > 0


def test_system_health(system):
    health = system.get_system_health()
    assert isinstance(health, str)
    assert len(health) > 0


def test_system_display_mode(system):
    with patch("subprocess.Popen") as mock_popen:
        res = system.set_display_mode("clone")
        assert res is True
        mock_popen.assert_called_once()
        args = mock_popen.call_args[0][0]
        assert "DisplaySwitch.exe" in args
        assert "/clone" in args


def test_system_recycle_bin(system):
    with patch("ctypes.windll.shell32.SHEmptyRecycleBinW", return_value=0) as mock_empty:
        res = system.empty_recycle_bin()
        assert res is True
        mock_empty.assert_called_once()


def test_system_caffeine_mode(system):
    res_on = system.set_keep_awake(True)
    assert res_on is True
    res_off = system.set_keep_awake(False)
    assert res_off is True


def test_system_network_info(system):
    info = system.get_network_info()
    assert isinstance(info, str)
    assert "IP" in info or "Network" in info


def test_system_clipboard_tools(system):
    # Test clear clipboard
    res = system.clear_clipboard()
    assert isinstance(res, bool)


def test_system_switch_to_tab(system):
    with patch("pyautogui.hotkey") as mock_hotkey:
        with patch("pyautogui.write") as mock_write:
            res = system.switch_to_tab("github")
            assert res is True
            mock_hotkey.assert_called_with("ctrl", "shift", "a")
            mock_write.assert_called_with("github")


# ---------------------------------------------------------------------------
# 3. ActionDispatcher Routing Tests
# ---------------------------------------------------------------------------

def test_dispatcher_deep_system_routing():
    mock_sys = MagicMock()
    mock_sys.get_battery_status.return_value = "Battery is at 95%."
    mock_sys.get_system_health.return_value = "Top RAM: Chrome (450 MB)."
    mock_sys.get_network_info.return_value = "Local IP: 192.168.1.100."

    dispatcher = ActionDispatcher(
        mouse=MagicMock(),
        keyboard=MagicMock(),
        window=MagicMock(),
        system=mock_sys,
        enable_vision_fallback=False,
    )

    actions = [
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_brightness", scroll_amount=70),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="dark_mode"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="battery_status"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="system_health"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="network_info"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="empty_recycle_bin"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="keep_awake"),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="switch_to_tab", target="gmail"),
    ]

    status_updates = []
    success = dispatcher.execute_plan(actions, status_callback=status_updates.append)
    assert success is True

    mock_sys.set_brightness.assert_called_with(70)
    mock_sys.set_dark_mode.assert_called_with(True)
    mock_sys.get_battery_status.assert_called_once()
    mock_sys.get_system_health.assert_called_once()
    mock_sys.get_network_info.assert_called_once()
    mock_sys.empty_recycle_bin.assert_called_once()
    mock_sys.set_keep_awake.assert_called_with(True)
    mock_sys.switch_to_tab.assert_called_with("gmail", uia=dispatcher.uia)

    assert "Battery is at 95%." in status_updates
    assert "Top RAM: Chrome (450 MB)." in status_updates
    assert "Local IP: 192.168.1.100." in status_updates

