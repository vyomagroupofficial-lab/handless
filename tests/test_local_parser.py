import pytest
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType, WindowActionType


@pytest.fixture
def parser():
    return LocalRuleParser()


def test_open_application(parser):
    res = parser.interpret("Open Chrome")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "chrome"

    res = parser.interpret("launch notepad")
    assert res is not None
    assert res.actions[0].action_type == ActionType.LAUNCH_APP
    assert res.actions[0].target == "notepad"


def test_click_element(parser):
    res = parser.interpret("Click the search button")
    assert res is not None
    assert res.actions[0].action_type == ActionType.CLICK
    assert res.actions[0].target == "search"
    assert res.actions[0].target_type == "button"

    res = parser.interpret("double click the folder")
    assert res is not None
    assert res.actions[0].action_type == ActionType.DOUBLE_CLICK
    assert res.actions[0].target == "folder"


def test_type_text(parser):
    res = parser.interpret("Type Minecraft")
    assert res is not None
    assert res.actions[0].action_type == ActionType.TYPE
    assert res.actions[0].text == "minecraft"


def test_window_management(parser):
    res = parser.interpret("close this application")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.CLOSE

    res = parser.interpret("minimize window")
    assert res is not None
    assert res.actions[0].action_type == ActionType.WINDOW_ACTION
    assert res.actions[0].window_action == WindowActionType.MINIMIZE


def test_emergency_stop(parser):
    res = parser.interpret("stop")
    assert res is not None
    assert res.actions[0].target == "emergency_stop"


def test_shortcuts(parser):
    res = parser.interpret("copy that")
    assert res is not None
    assert res.actions[0].action_type == ActionType.SHORTCUT
    assert res.actions[0].keys == "ctrl+c"

    res = parser.interpret("press enter")
    assert res is not None
    assert res.actions[0].action_type == ActionType.KEY_PRESS
    assert res.actions[0].keys == "enter"
