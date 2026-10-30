"""Unit tests for Workflow Manager and Multi-Step Action Automations."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock

from handless.actions.workflows import Workflow, WorkflowManager
from handless.intelligence.models import ActionRequest, ActionType


def test_workflow_builtin_loading(tmp_path, monkeypatch):
    test_file = tmp_path / "test_workflows.json"
    monkeypatch.setattr("handless.actions.workflows.WORKFLOWS_FILE", test_file)

    manager = WorkflowManager()
    workflows = manager.get_all()
    assert len(workflows) >= 5

    wf_ids = [w.id for w in workflows]
    assert "dev_stack" in wf_ids
    assert "focus_mode" in wf_ids
    assert "quick_notes" in wf_ids


def test_workflow_find_by_trigger(tmp_path, monkeypatch):
    test_file = tmp_path / "test_workflows.json"
    monkeypatch.setattr("handless.actions.workflows.WORKFLOWS_FILE", test_file)

    manager = WorkflowManager()

    assert manager.find_by_trigger("start coding") is not None
    assert manager.find_by_trigger("start coding").id == "dev_stack"

    assert manager.find_by_trigger("please focus mode") is not None
    assert manager.find_by_trigger("please focus mode").id == "focus_mode"

    assert manager.find_by_trigger("unrelated query") is None


def test_workflow_custom_save_and_delete(tmp_path, monkeypatch):
    test_file = tmp_path / "test_workflows.json"
    monkeypatch.setattr("handless.actions.workflows.WORKFLOWS_FILE", test_file)

    manager = WorkflowManager()

    custom_wf = Workflow(
        id="custom_calc",
        name="Launch Calculator",
        description="Open calc and type numbers",
        icon="🧮",
        trigger_phrases=["open calculator", "calc"],
        actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target="calc")],
        is_builtin=False,
    )

    assert manager.save(custom_wf) is True
    assert any(w.id == "custom_calc" for w in manager.get_all())

    # Delete
    assert manager.delete("custom_calc") is True
    assert not any(w.id == "custom_calc" for w in manager.get_all())


def test_workflow_execute(tmp_path, monkeypatch):
    test_file = tmp_path / "test_workflows.json"
    monkeypatch.setattr("handless.actions.workflows.WORKFLOWS_FILE", test_file)

    manager = WorkflowManager()
    wf = manager.get("focus_mode")
    assert wf is not None

    mock_dispatcher = MagicMock()
    mock_dispatcher.execute_plan.return_value = True

    success = manager.execute(wf, mock_dispatcher)
    assert success is True
    mock_dispatcher.execute_plan.assert_called_once()
