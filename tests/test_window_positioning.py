"""Unit tests for window positioning, centering, popup mode, multi-app layouts,
and exact volume audio controls.
"""

from unittest.mock import MagicMock, patch
import pytest

from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType, WindowActionType, ActionRequest
from handless.actions.window import WindowController
from handless.actions.system import SystemController
from handless.actions.dispatcher import ActionDispatcher


@pytest.fixture
def parser():
    return LocalRuleParser()


class DummyWindowController:
    def __init__(self):
        self.centered = []
        self.popups = []
        self.positioned = []
        self.minimized = []
        self.maximized = []
        self.restored = []
        self.two_app_layouts = []

    def center_window(self, target=None, width=None, height=None, uia=None):
        self.centered.append(target)
        return True

    def make_popup_window(self, target=None, width=780, height=520, uia=None):
        self.popups.append(target)
        return True

    def position_window(self, position, target=None, uia=None):
        self.positioned.append((position, target))
        return True

    def minimize(self, target=None, uia=None):
        self.minimized.append(target)
        return True

    def maximize(self, target=None, uia=None):
        self.maximized.append(target)
        return True

    def restore(self, target=None, uia=None):
        self.restored.append(target)
        return True

    def layout_two_apps(self, app1, app2, layout="side_by_side", uia=None):
        self.two_app_layouts.append((app1, app2, layout))
        return True

    def close(self, win=None):
        return True

    def switch_window(self):
        return True


class DummySystemController:
    def __init__(self):
        self.volumes = []
        self.snaps = []

    def set_volume(self, level):
        self.volumes.append(level)
        return True

    def snap_left(self):
        self.snaps.append("left")
        return True

    def snap_right(self):
        self.snaps.append("right")
        return True

    def snap_top_left(self):
        self.snaps.append("top_left")
        return True

    def snap_top_right(self):
        self.snaps.append("top_right")
        return True

    def snap_bottom_left(self):
        self.snaps.append("bottom_left")
        return True

    def snap_bottom_right(self):
        self.snaps.append("bottom_right")
        return True

    def toggle_mute(self):
        return True


# ---------------------------------------------------------------------------
# 1. Local Parser Tests
# ---------------------------------------------------------------------------

def test_parser_target_minimize(parser):
    res = parser.interpret("minimize chrome")
    assert res is not None
    assert len(res.actions) == 1
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.MINIMIZE
    assert res.actions[0].target == "chrome"


def test_parser_target_maximize(parser):
    res = parser.interpret("maximize vscode")
    assert res is not None
    assert len(res.actions) == 1
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.MAXIMIZE
    assert res.actions[0].target == "vscode"


def test_parser_target_restore(parser):
    res = parser.interpret("restore notepad")
    assert res is not None
    assert len(res.actions) == 1
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.RESTORE
    assert res.actions[0].target == "notepad"


def test_parser_center_window(parser):
    res1 = parser.interpret("center window")
    assert res1 is not None
    assert res1.actions[0].window_action == WindowActionType.CENTER
    assert res1.actions[0].target is None

    res2 = parser.interpret("center chrome")
    assert res2 is not None
    assert res2.actions[0].window_action == WindowActionType.CENTER
    assert res2.actions[0].target == "chrome"

    res3 = parser.interpret("put in center")
    assert res3 is not None
    assert res3.actions[0].window_action == WindowActionType.CENTER


def test_parser_popup_window(parser):
    res1 = parser.interpret("make a small popup window of it")
    assert res1 is not None
    assert res1.actions[0].window_action == WindowActionType.POPUP
    assert res1.actions[0].target is None

    res2 = parser.interpret("make chrome a popup")
    assert res2 is not None
    assert res2.actions[0].window_action == WindowActionType.POPUP
    assert res2.actions[0].target == "chrome"


def test_parser_directional_snapping(parser):
    res_l = parser.interpret("put chrome on left")
    assert res_l.actions[0].window_action == WindowActionType.SNAP_LEFT
    assert res_l.actions[0].target == "chrome"

    res_tl = parser.interpret("put in top left")
    assert res_tl.actions[0].window_action == WindowActionType.TOP_LEFT
    assert res_tl.actions[0].target is None

    res_br = parser.interpret("put chrome in bottom right")
    assert res_br.actions[0].window_action == WindowActionType.BOTTOM_RIGHT
    assert res_br.actions[0].target == "chrome"


def test_parser_multi_app_layout(parser):
    res1 = parser.interpret("put chrome on left and vscode on right")
    assert res1 is not None
    assert len(res1.actions) == 2
    assert res1.actions[0].target == "chrome"
    assert res1.actions[0].window_action == WindowActionType.SNAP_LEFT
    assert res1.actions[1].target == "vscode"
    assert res1.actions[1].window_action == WindowActionType.SNAP_RIGHT

    res2 = parser.interpret("put chrome on top and terminal below it")
    assert res2 is not None
    assert len(res2.actions) == 2
    assert res2.actions[0].target == "chrome"
    assert res2.actions[0].window_action == WindowActionType.TOP_HALF
    assert res2.actions[1].target == "terminal"
    assert res2.actions[1].window_action == WindowActionType.BOTTOM_HALF

    res3 = parser.interpret("put chrome on left top and notepad down of it")
    assert res3 is not None
    assert len(res3.actions) == 2
    assert res3.actions[0].target == "chrome"
    assert res3.actions[0].window_action == WindowActionType.TOP_LEFT
    assert res3.actions[1].target == "notepad"
    assert res3.actions[1].window_action == WindowActionType.BOTTOM_LEFT


def test_parser_volume_control(parser):
    res1 = parser.interpret("set volume to 50%")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res1.actions[0].system_action == "set_volume"
    assert res1.actions[0].scroll_amount == 50

    res2 = parser.interpret("volume 80%")
    assert res2 is not None
    assert res2.actions[0].scroll_amount == 80

    res3 = parser.interpret("turn volume to 30")
    assert res3 is not None
    assert res3.actions[0].scroll_amount == 30

    res4 = parser.interpret("unmute")
    assert res4 is not None
    assert res4.actions[0].system_action == "unmute"


# ---------------------------------------------------------------------------
# 2. WindowController Geometry & Layout Tests
# ---------------------------------------------------------------------------

def test_window_controller_get_work_area():
    wc = WindowController()
    work = wc.get_work_area()
    assert len(work) == 4
    assert work[2] > work[0]
    assert work[3] > work[1]


@patch("handless.actions.window.win32gui")
@patch("handless.actions.window.win32con")
def test_window_controller_center(mock_con, mock_gui):
    wc = WindowController()
    mock_gui.IsWindow.return_value = True
    mock_gui.IsWindowVisible.return_value = True
    mock_gui.GetWindowText.return_value = "Google Chrome"
    mock_gui.GetWindowRect.return_value = (100, 100, 900, 700)

    with patch.object(wc, "resolve_window_hwnd", return_value=12345):
        with patch.object(wc, "get_work_area", return_value=(0, 0, 1920, 1080)):
            res = wc.center_window(target="chrome")
            assert res is True
            mock_gui.MoveWindow.assert_called_once()
            # Check MoveWindow arguments
            args, _ = mock_gui.MoveWindow.call_args
            hwnd, x, y, w, h, repaint = args
            assert hwnd == 12345
            assert x > 0
            assert y > 0
            assert w > 0
            assert h > 0


@patch("handless.actions.window.win32gui")
def test_window_controller_popup(mock_gui):
    wc = WindowController()
    with patch.object(wc, "resolve_window_hwnd", return_value=54321):
        with patch.object(wc, "get_work_area", return_value=(0, 0, 1920, 1080)):
            res = wc.make_popup_window(target="notepad", width=780, height=520)
            assert res is True
            mock_gui.MoveWindow.assert_called_once()
            args, _ = mock_gui.MoveWindow.call_args
            hwnd, x, y, w, h, _ = args
            assert hwnd == 54321
            assert w == 780
            assert h == 520
            # Center of 1920: (1920 - 780) // 2 = 570
            assert x == 570
            # Center of 1080: (1080 - 520) // 2 = 280
            assert y == 280


@patch("handless.actions.window.win32gui")
def test_window_controller_positions(mock_gui):
    wc = WindowController()
    with patch.object(wc, "resolve_window_hwnd", return_value=11111):
        with patch.object(wc, "get_work_area", return_value=(0, 0, 1920, 1000)):
            # Left snap
            assert wc.position_window("left", target="chrome") is True
            args, _ = mock_gui.MoveWindow.call_args
            assert args == (11111, 0, 0, 960, 1000, True)

            # Right snap
            assert wc.position_window("right", target="chrome") is True
            args, _ = mock_gui.MoveWindow.call_args
            assert args == (11111, 960, 0, 960, 1000, True)

            # Top-left quadrant
            assert wc.position_window("top_left", target="chrome") is True
            args, _ = mock_gui.MoveWindow.call_args
            assert args == (11111, 0, 0, 960, 500, True)

            # Bottom-right quadrant
            assert wc.position_window("bottom_right", target="chrome") is True
            args, _ = mock_gui.MoveWindow.call_args
            assert args == (11111, 960, 500, 960, 500, True)


def test_window_controller_layout_two_apps():
    wc = WindowController()
    with patch.object(wc, "position_window", return_value=True) as mock_pos:
        res = wc.layout_two_apps("chrome", "vscode", layout="side_by_side")
        assert res is True
        assert mock_pos.call_count == 2
        mock_pos.assert_any_call("left", target="chrome", uia=None)
        mock_pos.assert_any_call("right", target="vscode", uia=None)


# ---------------------------------------------------------------------------
# 3. SystemController Exact Volume Tests
# ---------------------------------------------------------------------------

def test_system_controller_set_volume():
    sc = SystemController()
    # Test setting volume with simulated fallback or comtypes
    res = sc.set_volume(65)
    assert res is True

    # Test clamping
    res_high = sc.set_volume(150)
    assert res_high is True

    res_low = sc.set_volume(-20)
    assert res_low is True


def test_system_controller_get_volume():
    sc = SystemController()
    vol = sc.get_volume()
    assert isinstance(vol, int)
    assert 0 <= vol <= 100


# ---------------------------------------------------------------------------
# 4. ActionDispatcher Integration
# ---------------------------------------------------------------------------

def test_dispatcher_window_and_volume_actions():
    dummy_win = DummyWindowController()
    dummy_sys = DummySystemController()

    dispatcher = ActionDispatcher(
        mouse=MagicMock(),
        keyboard=MagicMock(),
        window=dummy_win,
        system=dummy_sys,
        enable_vision_fallback=False,
    )

    actions = [
        ActionRequest(action_type=ActionType.WINDOW_ACTION, target="chrome", window_action=WindowActionType.CENTER),
        ActionRequest(action_type=ActionType.WINDOW_ACTION, target="notepad", window_action=WindowActionType.POPUP),
        ActionRequest(action_type=ActionType.WINDOW_ACTION, target="vscode", window_action=WindowActionType.SNAP_LEFT),
        ActionRequest(action_type=ActionType.WINDOW_ACTION, target="terminal", window_action=WindowActionType.TOP_LEFT),
        ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="set_volume", scroll_amount=75),
    ]

    success = dispatcher.execute_plan(actions)
    assert success is True

    assert "chrome" in dummy_win.centered
    assert "notepad" in dummy_win.popups
    assert ("left", "vscode") in dummy_win.positioned
    assert ("top_left", "terminal") in dummy_win.positioned
    assert 75 in dummy_sys.volumes

