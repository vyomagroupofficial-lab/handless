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
