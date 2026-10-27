"""Tier 1: Deterministic Local Rule-Based Command Parser.

Executes offline in <10ms with zero latency for standard voice commands.
Covers app launching, clicking, typing, scrolling, window control, and shortcuts.
"""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)


class LocalRuleParser(BaseIntentInterpreter):
    """Deterministic local rule parser."""

    @property
    def name(self) -> str:
        return "local_rule"

    def is_available(self) -> bool:
        return True

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        cleaned = transcript.strip().lower()
        if not cleaned:
            return None

        # Clean filler words often prepended in speech
        cleaned = re.sub(r"^(please|can you|could you|just|handless|hey handless)\s+", "", cleaned)

        # 1. Emergency stop / cancel
        if cleaned in ("stop", "emergency stop", "halt", "cancel", "cancel that"):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=1.0,
                actions=[ActionRequest(action_type=ActionType.NONE, target="emergency_stop")],
                reasoning="Emergency stop command recognized",
            )

        # 2. Key presses & Shortcuts (checked before generic verbs so "press enter" isn't treated as click)
        key_mappings = {
            "enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "press enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "hit enter": ActionRequest(action_type=ActionType.KEY_PRESS, keys="enter"),
            "press space": ActionRequest(action_type=ActionType.KEY_PRESS, keys="space"),
            "press tab": ActionRequest(action_type=ActionType.KEY_PRESS, keys="tab"),
            "press escape": ActionRequest(action_type=ActionType.KEY_PRESS, keys="esc"),
            "press backspace": ActionRequest(action_type=ActionType.KEY_PRESS, keys="backspace"),
            "copy": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+c"),
            "copy that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+c"),
            "paste": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+v"),
            "paste that": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+v"),
            "cut": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+x"),
            "select all": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+a"),
            "undo": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+z"),
            "save": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s"),
            "save this": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+s"),
            "new tab": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+t"),
            "close tab": ActionRequest(action_type=ActionType.SHORTCUT, keys="ctrl+w"),
        }

        if cleaned in key_mappings:
            req = key_mappings[cleaned]
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[req],
                reasoning=f"Shortcut/Key '{req.keys}' recognized",
            )

        # 3. Window actions (close, minimize, maximize, switch)
        m_close = re.match(r"^(close|exit|quit)(\s+(this|the))?(\s+(application|app|window|program))?$", cleaned)
        if m_close:
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.CLOSE)],
                reasoning="Close active window",
            )

        m_close_target = re.match(r"^(close|exit|quit)\s+([a-zA-Z0-9_\-\s]+)$", cleaned)
        if m_close_target and m_close_target.group(2) not in ("this", "the", "window", "app"):
            target_app = m_close_target.group(2).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, target=target_app, window_action=WindowActionType.CLOSE)],
                reasoning=f"Close application '{target_app}'",
            )

        if re.match(r"^(minimize)(\s+(this|the))?(\s+(application|app|window))?$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.MINIMIZE)],
                reasoning="Minimize active window",
            )

        if re.match(r"^(maximize|full\s*screen)(\s+(this|the))?(\s+(application|app|window))?$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.WINDOW_ACTION, window_action=WindowActionType.MAXIMIZE)],
                reasoning="Maximize active window",
            )

        if re.match(r"^(switch\s+window|next\s+window|alt\s+tab)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SHORTCUT, keys="alt+tab")],
                reasoning="Switch window",
            )

        # 4. Application Launching
        m_launch = re.match(r"^(open|launch|start|run)\s+(.+)$", cleaned)
        if m_launch:
            app_name = m_launch.group(2).strip()
            if app_name not in ("new tab", "tab"):
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.95,
                    actions=[ActionRequest(action_type=ActionType.LAUNCH_APP, target=app_name)],
                    reasoning=f"Launch application '{app_name}'",
                )

        # 5. Typing Text
        m_type = re.match(r"^(type|write|enter text|input)\s+(.+)$", cleaned)
        if m_type:
            text_to_type = m_type.group(2).strip()
            m_in_target = re.match(r"^(this\s+in\s+the\s+([a-zA-Z0-9_\s]+)\s*[:]\s*)(.+)$", text_to_type)
            if m_in_target:
                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=0.9,
                    actions=[
                        ActionRequest(action_type=ActionType.CLICK, target=m_in_target.group(2).strip(), target_type="edit"),
                        ActionRequest(action_type=ActionType.TYPE, text=m_in_target.group(3).strip()),
                    ],
                    reasoning="Click target field and type text",
                )

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.TYPE, text=text_to_type)],
                reasoning=f"Type '{text_to_type}' into focused control",
            )

        # 6. Clicking Elements
        m_double_click = re.match(r"^(double\s+click)(\s+(on|the))?\s+(.+)$", cleaned)
        if m_double_click:
            target = m_double_click.group(4).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.DOUBLE_CLICK, target=target)],
                reasoning=f"Double-click element '{target}'",
            )

        m_right_click = re.match(r"^(right\s+click)(\s+(on|the))?\s+(.+)$", cleaned)
        if m_right_click:
            target = m_right_click.group(4).strip()
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.RIGHT_CLICK, target=target)],
                reasoning=f"Right-click element '{target}'",
            )

        m_click = re.match(r"^(click|press|tap|hit|select)(\s+(on|the))?\s+(.+)$", cleaned)
        if m_click:
            target = m_click.group(4).strip()
            target_type = None
            if target.endswith(" button"):
                target_type = "button"
                target = target[:-7].strip()
            elif target.endswith(" menu"):
                target_type = "menu"
                target = target[:-5].strip()
            elif target.endswith(" tab"):
                target_type = "tab"
                target = target[:-4].strip()

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.9,
                actions=[ActionRequest(action_type=ActionType.CLICK, target=target, target_type=target_type)],
                reasoning=f"Click element '{target}'",
            )

        # 7. Scrolling
        if re.match(r"^(scroll\s+down|page\s+down)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SCROLL, scroll_direction="down", scroll_amount=3)],
                reasoning="Scroll down",
            )

        if re.match(r"^(scroll\s+up|page\s+up)$", cleaned):
            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=0.95,
                actions=[ActionRequest(action_type=ActionType.SCROLL, scroll_direction="up", scroll_amount=3)],
                reasoning="Scroll up",
            )

        # If no deterministic rule matched, return None to trigger LLM tier
        return None
