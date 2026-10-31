import pytest
from handless.intelligence.router import IntentRouter
from handless.actions.dispatcher import ActionDispatcher
from handless.safety.emergency_stop import emergency_stop
from tests.test_actions import DummyLauncher, DummyKeyboard, DummyMouse, DummyWindow


def test_end_to_end_open_app():
    emergency_stop.reset()
    router = IntentRouter()
    launcher = DummyLauncher()
    # DummyWindow has no switch_to_app, so a Chrome already open on this machine isn't focused instead
    dispatcher = ActionDispatcher(launcher=launcher, window=DummyWindow())

    transcript = "Open Chrome"
    intent = router.interpret(transcript)
    assert intent is not None
    assert len(intent.actions) == 1

    dispatcher.execute_plan(intent.actions)
    assert launcher.launched == ["chrome"]


def test_end_to_end_type_text():
    emergency_stop.reset()
    router = IntentRouter()
    kb = DummyKeyboard()
    dispatcher = ActionDispatcher(keyboard=kb)

    transcript = "Type Minecraft"
    intent = router.interpret(transcript)
    assert intent is not None

    dispatcher.execute_plan(intent.actions)
    assert kb.typed == ["minecraft"]


def test_end_to_end_emergency_stop_voice_command():
    emergency_stop.reset()
    router = IntentRouter()

    transcript = "emergency stop"
    intent = router.interpret(transcript)
    assert intent is not None
    assert intent.actions[0].target == "emergency_stop"
