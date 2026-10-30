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
    MIDDLE_CLICK = "middle_click"
    HOVER = "hover"
    MOVE_MOUSE = "move_mouse"
    TYPE = "type"
    TYPE_TEXT = "type"
    KEY_PRESS = "key_press"
    SHORTCUT = "shortcut"
    SCROLL = "scroll"
    LAUNCH_APP = "launch_app"
    WINDOW_ACTION = "window_action"
    SYSTEM_ACTION = "system_action"
    SELECT = "select"
    EXPAND = "expand"
    COLLAPSE = "collapse"
    WAIT = "wait"
    NONE = "none"


class WindowActionType(str, Enum):
    MINIMIZE = "minimize"
    MAXIMIZE = "maximize"
    RESTORE = "restore"
    CLOSE = "close"
    SWITCH = "switch"
    SNAP_LEFT = "snap_left"
    SNAP_RIGHT = "snap_right"
    CENTER = "center"
    POPUP = "popup"
    TOP_LEFT = "top_left"
    TOP_RIGHT = "top_right"
    BOTTOM_LEFT = "bottom_left"
    BOTTOM_RIGHT = "bottom_right"
    TOP_HALF = "top_half"
    BOTTOM_HALF = "bottom_half"


class ActionRequest(BaseModel):
    """Specification of an individual action to execute on the desktop."""
    action_type: ActionType
    target: Optional[str] = Field(default=None, description="UI element name, text, or target app")
    target_type: Optional[str] = Field(default=None, description="Control type hint e.g. button, edit, menu")
    text: Optional[str] = Field(default=None, description="Text to type into focused field")
    keys: Optional[str] = Field(default=None, description="Shortcut or key sequence, e.g. ctrl+c, enter")
    window_action: Optional[WindowActionType] = None
    system_action: Optional[str] = Field(default=None, description="Fundamental PC action (volume_up, mute, lock, etc.)")
    menu_path: Optional[str] = Field(default=None, description="Path for menu navigation, e.g. File->Save As or File")
    select_value: Optional[str] = Field(default=None, description="Item or value to select in a combobox, list, or dropdown")
    target_app: Optional[str] = Field(default=None, description="Target application name or regex for targeted window connection")
    scroll_direction: Optional[str] = Field(default=None, description="up, down, left, right")
    scroll_amount: int = Field(default=3, description="Units/clicks to scroll")
    coordinates: Optional[Tuple[int, int]] = Field(default=None, description="Physical screen (x, y) if vision based")
    spatial_landmark: Optional[str] = Field(default=None, description="Spatial zone hint: top_right, top_left, bottom_right, bottom_left, top, bottom, center, left, right")
    relative_anchor: Optional[str] = Field(default=None, description="Anchor element name for relative proximity search")
    relative_relation: Optional[str] = Field(default=None, description="Spatial relation: near, next_to, right_of, left_of, below, above")
    requires_confirmation: bool = Field(default=False, description="Whether action requires user confirmation before execution")



class IntentResult(BaseModel):
    """Result of interpreting a voice command transcript."""
    raw_transcript: str
    source: str = Field(description="local_rule, local_llm, or gemini")
    confidence: float = Field(ge=0.0, le=1.0)
    actions: List[ActionRequest] = Field(default_factory=list)
    reasoning: Optional[str] = None
    clarification_question: Optional[str] = None
    answer_text: Optional[str] = Field(default=None, description="Direct conversational response or screen insight")
