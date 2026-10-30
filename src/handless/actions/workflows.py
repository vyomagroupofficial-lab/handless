"""Multi-step automation workflows and custom voice macros for Vyoma Handless.

Provides built-in desktop productivity workflows and an AI-powered natural language
workflow generator using Google Gemini 2.5 Flash. Workflows can be triggered via
voice alias, keyboard shortcut, or browser one-click execution.
"""

from __future__ import annotations

import json
import logging
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from handless.actions.dispatcher import ActionDispatcher
from handless.intelligence.models import ActionRequest, ActionType, WindowActionType

logger = logging.getLogger(__name__)

WORKFLOWS_FILE = Path.home() / ".vyoma-handless" / "workflows.json"


class Workflow(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str
    description: str
    icon: str = "⚡"
    trigger_phrases: List[str] = Field(default_factory=list)
    actions: List[ActionRequest] = Field(default_factory=list)
    is_builtin: bool = False


# Default built-in productivity workflows
BUILTIN_WORKFLOWS: List[Workflow] = [
    Workflow(
        id="dev_stack",
        name="Developer Stack",
        description="Launch VS Code, Windows Terminal, and Chrome side-by-side",
        icon="🚀",
        trigger_phrases=["dev setup", "start coding", "open my dev stack", "launch developer environment"],
        actions=[
            ActionRequest(action_type=ActionType.LAUNCH_APP, target="code", target_app="Code"),
            ActionRequest(action_type=ActionType.LAUNCH_APP, target="wt", target_app="WindowsTerminal"),
            ActionRequest(action_type=ActionType.LAUNCH_APP, target="chrome", target_app="chrome"),
        ],
        is_builtin=True,
    ),
    Workflow(
        id="focus_mode",
        name="Focus Mode",
        description="Minimize all clutter to reveal a clean desktop workspace",
        icon="🧘",
        trigger_phrases=["focus mode", "clean desktop", "minimize everything", "clear workspace"],
        actions=[
            ActionRequest(action_type=ActionType.SHORTCUT, keys="win+d"),
        ],
        is_builtin=True,
    ),
    Workflow(
        id="web_research",
        name="Web Research Session",
        description="Open Chrome ready for search with a clean new tab",
        icon="🌐",
        trigger_phrases=["web research", "browse internet", "open research tab"],
        actions=[
            ActionRequest(action_type=ActionType.LAUNCH_APP, target="chrome", target_app="chrome"),
            ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+t"),
        ],
        is_builtin=True,
    ),
    Workflow(
        id="quick_notes",
        name="Meeting & Quick Notes",
        description="Open Notepad and prepare a fresh timestamped note",
        icon="📝",
        trigger_phrases=["quick notes", "take notes", "meeting notes", "open notepad note"],
        actions=[
            ActionRequest(action_type=ActionType.LAUNCH_APP, target="notepad", target_app="Notepad"),
            ActionRequest(action_type=ActionType.TYPE, text="--- Vyoma Quick Notes ---\n"),
        ],
        is_builtin=True,
    ),
    Workflow(
        id="tile_windows",
        name="Side-by-Side Tiling",
        description="Snap active window to the left and prepare companion window",
        icon="📑",
        trigger_phrases=["tile left", "snap window", "side by side", "tile screen"],
        actions=[
            ActionRequest(action_type=ActionType.SHORTCUT, keys="win+left"),
        ],
        is_builtin=True,
    ),
]


class WorkflowManager:
    """Manages built-in and user-saved custom automation workflows."""

    def __init__(self, file_path: Optional[Path] = None) -> None:
        self.file_path = file_path or WORKFLOWS_FILE

    def _ensure_dir(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def load_user_workflows(self) -> List[Workflow]:
        """Load user-saved custom workflows from disk."""
        if not self.file_path.exists():
            return []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return [Workflow.model_validate(w) for w in data]
        except Exception as exc:
            logger.warning("Failed to load workflows from %s: %s", self.file_path, exc)
            return []

    def get_all(self) -> List[Workflow]:
        """Return combined list of built-in and user workflows."""
        user_wfs = self.load_user_workflows()
        user_ids = {w.id for w in user_wfs}
        # Built-ins that haven't been overwritten
        active_builtins = [w for w in BUILTIN_WORKFLOWS if w.id not in user_ids]
        return active_builtins + user_wfs

    def list_workflows(self) -> List[Workflow]:
        """Convenience alias for get_all."""
        return self.get_all()

    def get(self, workflow_id: str) -> Optional[Workflow]:
        """Get a workflow by its unique ID."""
        for wf in self.get_all():
            if wf.id == workflow_id:
                return wf
        return None

    def save(self, workflow: Workflow) -> bool:
        """Save or update a custom workflow."""
        try:
            self._ensure_dir()
            current = self.load_user_workflows()
            # Replace if existing, else append
            updated = [w for w in current if w.id != workflow.id]
            updated.append(workflow)
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([w.model_dump() for w in updated], f, indent=2)
            return True
        except Exception as exc:
            logger.error("Failed to save workflow %s: %s", workflow.id, exc)
            return False

    def delete(self, workflow_id: str) -> bool:
        """Delete a custom workflow by ID."""
        try:
            self._ensure_dir()
            current = self.load_user_workflows()
            updated = [w for w in current if w.id != workflow_id]
            with open(self.file_path, "w", encoding="utf-8") as f:
                json.dump([w.model_dump() for w in updated], f, indent=2)
            return True
        except Exception as exc:
            logger.error("Failed to delete workflow %s: %s", workflow_id, exc)
            return False

    def find_by_trigger(self, transcript: str) -> Optional[Workflow]:
        """Check if user speech transcript matches any workflow trigger phrase."""
        clean = transcript.strip().lower()
        for wf in self.get_all():
            for phrase in wf.trigger_phrases:
                if phrase.lower() in clean or clean in phrase.lower():
                    return wf
        return None

    def execute(self, workflow: Workflow, dispatcher: ActionDispatcher) -> bool:
        """Execute all steps in the workflow through the ActionDispatcher."""
        logger.info("Executing workflow '%s' (%d actions)", workflow.name, len(workflow.actions))
        return dispatcher.execute_plan(workflow.actions)
