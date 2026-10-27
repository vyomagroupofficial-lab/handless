"""Data models for intelligence, intent parsing, and actions.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional, Tuple
from pydantic import BaseModel, Field


class ActionType(str, Enum):
    """Supported low-level desktop action primitives."""
    CLICK = "click"
    DOUBLE_CLICK = "double_click"
    RIGHT_CLICK = "right_click"
    TYPE = "type"
    KEY_PRESS = "key_press"
    SHORTCUT = "shortcut"
    SCROLL = "scroll"
    LAUNCH_APP = "launch_app"
    WINDOW_ACTION = "window_action"
    WAIT = "wait"
    NONE = "none"


class WindowActionType(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    CLOSE = "close"
    SWITCH = "switch"


class ActionRequest(BaseModel):
    """Specification of an individual action to execute on the desktop."""
    action_type: ActionType
    target: Optional[str] = Field(default=None, description="UI element name, text, or target app")
    target_type: Optional[str] = Field(default=None, description="Control type hint e.g. button, edit, menu")
    text: Optional[str] = Field(default=None, description="Text to type into focused field")
    keys: Optional[str] = Field(default=None, description="Shortcut or key sequence, e.g. ctrl+c, enter")
    window_action: Optional[WindowActionType] = None
    scroll_direction: Optional[str] = Field(default=None, description="up, down, left, right")
    scroll_amount: int = Field(default=3, description="Units/clicks to scroll")
    coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Physical screen (x, y) if vision based")
    requires_confirmation: bool = Field(default=False, description="Whether action requires user confirmation before execution")


class IntentResult(BaseModel):
    """Result of interpreting a voice command transcript."""
    raw_transcript: str
    source: str = Field(description="local_rule, local_llm, or gemini")
    confidence: float = Field(ge=0.0, le=1.0)
    actions: List[ActionRequest] = Field(default_factory=list)
    reasoning: Optional[str] = None
    clarification_question: Optional[str] = None
