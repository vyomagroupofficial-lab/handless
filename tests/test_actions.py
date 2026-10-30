import pytest
from handless.intelligence.models import ActionRequest, ActionType, WindowActionType
from handless.actions.dispatcher import ActionDispatcher
from handless.safety.emergency_stop import emergency_stop


class DummyLauncher:
    def __init__(self):
        self.launched = []

    def launch(self, name: str) -> bool:
        self.launched.append(name)
        return True


class DummyMouse:
    def __init__(self):
        self.clicks = []
        self.scrolls = []

    def click(self, element=None, coordinates=None):
        self.clicks.append((element, coordinates))
        return True

    def double_click(self, element=None, coordinates=None):
        return True

    def right_click(self, element=None, coordinates=None):
        return True

    def scroll(self, direction="down", amount=3):
        self.scrolls.append((direction, amount))
        return True


class DummyKeyboard:
    def __init__(self):
        self.typed = []
        self.keys = []
        self.shortcuts = []

    def type_text(self, text, element=None):
        self.typed.append(text)
        return True

    def press_key(self, key):
        self.keys.append(key)
        return True

    def execute_shortcut(self, shortcut):
        self.shortcuts.append(shortcut)
        return True


class DummyWindow:
    def __init__(self):
        self.closed = False
        self.minimized = False

    def close(self, win=None):
        self.closed = True
        return True

    def minimize(self, win=None):
        self.minimized = True
        return True

    def maximize(self, win=None):
        return True

    def switch_window(self):
        return True


def test_action_dispatcher_execution():
    emergency_stop.reset()
    mouse = DummyMouse()
    kb = DummyKeyboard()
    launcher = DummyLauncher()
    win = DummyWindow()

    dispatcher = ActionDispatcher(
        mouse=mouse,
        keyboard=kb,
        window=win,
        launcher=launcher,
        enable_vision_fallback=False,
    )

    actions = [
        ActionRequest(action_type=ActionType.LAUNCH_APP, target="notepad"),
        ActionRequest(action_type=ActionType.TYPE, text="Hello Vyoma"),
        ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
        ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s"),
        ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.CLOSE),
    ]

    status_updates = []
    success = dispatcher.execute_plan(actions, status_callback=status_updates.append)

    assert success is True
    assert launcher.launched == ["notepad"]
    assert kb.typed == ["Hello Vyoma"]
    assert kb.keys == ["enter"]
    assert kb.shortcuts == ["ctrl+s"]
    assert win.closed is True
    assert "Done ✓" in status_updates


def test_emergency_stop_halts_dispatcher():
    emergency_stop.reset()
    mouse = DummyMouse()
    kb = DummyKeyboard()
    launcher = DummyLauncher()

    dispatcher = ActionDispatcher(
        mouse=mouse,
        keyboard=kb,
        launcher=launcher,
    )

    # Trigger emergency stop before action execution
    emergency_stop.trigger(reason="Test stop")

    actions = [
        ActionRequest(action_type=ActionType.LAUNCH_APP, target="notepad"),
        ActionRequest(action_type=ActionType.TYPE, text="Should not type"),
    ]

    status_updates = []
    success = dispatcher.execute_plan(actions, status_callback=status_updates.append)

    assert success is False
    assert len(launcher.launched) == 0
    assert len(kb.typed) == 0
    assert any("Emergency Stop" in s for s in status_updates)
    emergency_stop.reset()


class DummyElementOps:
    def __init__(self):
        self.menus = []
        self.combos = []
        self.expanded = []
        self.collapsed = []

    def select_menu_item(self, elem, path):
        self.menus.append((elem, path))
        return True

    def select_combo_item(self, elem, val):
        self.combos.append((elem, val))
        return True

    def expand_tree_item(self, elem):
        self.expanded.append(elem)
        return True

    def collapse_tree_item(self, elem):
        self.collapsed.append(elem)
        return True


def test_dispatcher_rich_element_operations():
    emergency_stop.reset()
    ops = DummyElementOps()
    dispatcher = ActionDispatcher(
        element_ops=ops,
        enable_vision_fallback=False,
    )

    actions = [
        ActionRequest(action_type=ActionType.SELECT, menu_path="File"),
        ActionRequest(action_type=ActionType.SELECT, target="font", select_value="Arial"),
        ActionRequest(action_type=ActionType.EXPAND, target="project_tree"),
        ActionRequest(action_type=ActionType.COLLAPSE, target="project_tree"),
    ]

    success = dispatcher.execute_plan(actions)
    assert success is True
    assert len(ops.menus) == 1
    assert ops.menus[0][1] == "File"
    assert len(ops.combos) == 1
    assert ops.combos[0][1] == "Arial"
    assert len(ops.expanded) == 1
    assert len(ops.collapsed) == 1


def test_dispatcher_target_app_connection():
    emergency_stop.reset()
    from unittest.mock import MagicMock
    mock_uia = MagicMock()
    dispatcher = ActionDispatcher(
        uia_inspector=mock_uia,
        mouse=DummyMouse(),
        enable_vision_fallback=False,
    )

    action = ActionRequest(action_type=ActionType.CLICK, target="btn", target_app="Notepad")
    success = dispatcher.execute_action(action)
    assert success is True
    mock_uia.connect_to_app.assert_called_once_with("Notepad")


def test_dispatcher_prioritizes_uia_component_tracking():
    emergency_stop.reset()
    from unittest.mock import MagicMock
    mock_uia = MagicMock()
    mock_elem = MagicMock()
    mock_elem.window_text.return_value = "Submit Button"
    mock_elem.automation_id.return_value = "btnSubmit"
    mock_elem.friendly_class_name.return_value = "Button"
    mock_uia.find_element.return_value = mock_elem

    mouse = DummyMouse()
    dispatcher = ActionDispatcher(
        uia_inspector=mock_uia,
        mouse=mouse,
        enable_vision_fallback=True,
    )

    # Even if coordinates are provided (e.g. from an LLM prompt), UIA component tracking is tried first
    action = ActionRequest(action_type=ActionType.CLICK, target="Submit Button", coordinates=(800, 450))
    success = dispatcher.execute_action(action)

    assert success is True
    mock_uia.find_element.assert_called_once_with("Submit Button", target_type=None)
    # Click received the UIA element
    assert mouse.clicks[0][0] == mock_elem


def test_dispatcher_vision_fallback_when_uia_stuck():
    emergency_stop.reset()
    from unittest.mock import MagicMock
    mock_uia = MagicMock()
    mock_uia.find_element.return_value = None  # UIA found nothing

    mock_vision = MagicMock()
    mock_vision.locate_element_coordinates.return_value = (950, 520)

    mouse = DummyMouse()
    dispatcher = ActionDispatcher(
        uia_inspector=mock_uia,
        vision_analyzer=mock_vision,
        mouse=mouse,
        enable_vision_fallback=True,
    )

    action = ActionRequest(action_type=ActionType.CLICK, target="Canvas Icon")
    success = dispatcher.execute_action(action)

    assert success is True
    mock_vision.locate_element_coordinates.assert_called_once_with("Canvas Icon")
    assert mouse.clicks[0][1] == (950, 520)


def test_dispatcher_system_actions():
    emergency_stop.reset()
    from unittest.mock import MagicMock
    mock_sys = MagicMock()
    mock_sys.volume_up.return_value = True
    mock_sys.show_desktop.return_value = True
    mock_sys.snap_left.return_value = True

    dispatcher = ActionDispatcher(
        system=mock_sys,
    )

    assert dispatcher.execute_action(ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="volume_up")) is True
    mock_sys.volume_up.assert_called_once()

    assert dispatcher.execute_action(ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="show_desktop")) is True
    mock_sys.show_desktop.assert_called_once()

    assert dispatcher.execute_action(ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.SNAP_LEFT)) is True
    mock_sys.snap_left.assert_called_once()


def test_dispatcher_window_action_safety():
    """Verify that unspecified or 'open' window actions never inadvertently close applications."""
    emergency_stop.reset()
    from unittest.mock import MagicMock

    mock_win = MagicMock()
    mock_win.switch_to_app.return_value = True
    mock_launcher = MagicMock()

    dispatcher = ActionDispatcher(
        window=mock_win,
        launcher=mock_launcher,
    )

    # 1. WINDOW_ACTION with target and no explicit close should switch/focus, NOT close!
    action_open = ActionRequest(action_type=ActionType.WINDOW_ACTION, target="Google Chrome", window_action=None)
    res = dispatcher.execute_action(action_open)
    assert res is True
    mock_win.switch_to_app.assert_called_with(target="Google Chrome", uia=dispatcher.uia)
    mock_win.close.assert_not_called()
    mock_win.close_window_or_app.assert_not_called()

    # 2. Unrecognized action without target should return False and never close active window
    mock_win.reset_mock()
    action_unknown = ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=None, target=None)
    res = dispatcher.execute_action(action_unknown)
    assert res is False
    mock_win.close.assert_not_called()
    mock_win.close_window_or_app.assert_not_called()

    # 3. Explicit CLOSE must close
    mock_win.reset_mock()
    action_close = ActionRequest(action_type=ActionType.WINDOW_ACTION, target="Google Chrome", window_action=WindowActionType.CLOSE)
    mock_win.close_window_or_app.return_value = True
    res = dispatcher.execute_action(action_close)
    assert res is True
    mock_win.close_window_or_app.assert_called_once_with(target="Google Chrome", uia=dispatcher.uia)


def test_dispatcher_send_button_fallback():
    """Verify that clicking 'send' falls back to Enter when element is not found."""
    emergency_stop.reset()
    from unittest.mock import MagicMock

    mock_uia = MagicMock()
    mock_uia.find_element.return_value = None
    mock_keyboard = DummyKeyboard()

    dispatcher = ActionDispatcher(
        uia_inspector=mock_uia,
        keyboard=mock_keyboard,
        enable_vision_fallback=False,
    )

    action = ActionRequest(action_type=ActionType.CLICK, target="send")
    res = dispatcher.execute_action(action)

    assert res is True
    assert "enter" in mock_keyboard.keys



def test_dispatcher_open_inspector_action():
    """Verify that open_inspector system action triggers ui_bridge signal."""
    emergency_stop.reset()
    from unittest.mock import MagicMock

    mock_bridge = MagicMock()
    dispatcher = ActionDispatcher(
        ui_bridge=mock_bridge,
    )

    action = ActionRequest(action_type=ActionType.SYSTEM_ACTION, system_action="open_inspector")
    res = dispatcher.execute_action(action)

    assert res is True
    mock_bridge.inspector_requested.emit.assert_called_once()




