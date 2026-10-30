"""Unit tests for Watch Me & Automate MacroRecorder and MacroRecordingBanner."""

import pytest
from PySide6.QtWidgets import QApplication

from handless.actions.macro_recorder import MacroRecorder
from handless.actions.workflows import WorkflowManager
from handless.intelligence.models import ActionRequest, ActionType
from handless.ui.macro_overlay import MacroRecordingBanner


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_macro_recorder_start_stop(tmp_path):
    mgr = WorkflowManager(file_path=tmp_path / "workflows.json")
    recorder = MacroRecorder(workflow_manager=mgr)

    assert not recorder.is_recording
    assert recorder.action_count == 0

    started = []
    stopped = []
    recorder.recording_started.connect(lambda: started.append(True))
    recorder.recording_stopped.connect(lambda: stopped.append(True))

    recorder.start_recording()
    assert recorder.is_recording
    assert len(started) == 1

    # Record some actions
    act1 = ActionRequest(action_type=ActionType.CLICK, coordinates=(250, 400), target="Button")
    act2 = ActionRequest(action_type=ActionType.TYPE, text="Hello world")
    recorder.record_action(act1)
    recorder.record_action(act2)

    assert recorder.action_count == 2

    # Save macro
    wf = recorder.save_macro(name="Test Automation Workflow")
    assert not recorder.is_recording
    assert len(stopped) == 1
    assert wf is not None
    assert wf.name == "Test Automation Workflow"
    assert len(wf.actions) == 2
    assert wf.actions[0].action_type == ActionType.CLICK
    assert wf.actions[1].action_type == ActionType.TYPE


def test_macro_recorder_discard(tmp_path):
    mgr = WorkflowManager(file_path=tmp_path / "workflows.json")
    recorder = MacroRecorder(workflow_manager=mgr)

    recorder.start_recording()
    act = ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s")
    recorder.record_action(act)
    assert recorder.action_count == 1

    recorder.discard_recording()
    assert not recorder.is_recording
    assert recorder.action_count == 0
    assert len(mgr.load_user_workflows()) == 0


def test_macro_recording_banner_ui(qapp, tmp_path):
    mgr = WorkflowManager(file_path=tmp_path / "workflows.json")
    recorder = MacroRecorder(workflow_manager=mgr)
    banner = MacroRecordingBanner(macro_recorder=recorder)

    assert banner.title_lbl.text() == "Watch Me & Automate"
    banner.update_action_count(5)
    assert "5 actions recorded" in banner.status_lbl.text()

    banner.close()
