"""Tier 3: Cloud Gemini Intelligence Client.

Integrates with Google AI Studio Gemini API (Gemini 2.5 Flash) using the
official `google-genai` Python SDK. Resolves complex multi-step reasoning,
ambiguous commands, follow-up interactions, and screen vision analysis.
Uses Windows Credential Manager to retrieve the API key securely.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from handless.security.credentials import get_gemini_api_key

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)


class GeminiSingleAction(BaseModel):
    action_type: str = Field(description="click, double_click, right_click, type, key_press, shortcut, scroll, launch_app, window_action, none")
    target: Optional[str] = Field(default=None, description="Target element name, label, or application")
    target_type: Optional[str] = Field(default=None, description="button, edit, menu, tab, window")
    text: Optional[str] = Field(default=None, description="Text string if typing")
    keys: Optional[str] = Field(default=None, description="Key combinations if shortcut or key_press")
    window_action: Optional[str] = Field(default=None, description="minimize, maximize, close, switch")
    scroll_direction: Optional[str] = Field(default=None, description="up or down")
    scroll_amount: int = Field(default=3)
    requires_confirmation: bool = Field(default=False)


class GeminiActionPlan(BaseModel):
    actions: List[GeminiSingleAction] = Field(description="Ordered sequence of actions to perform")
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = Field(description="Explanation of the planned actions")
    clarification_question: Optional[str] = Field(default=None, description="Question if command is too ambiguous")


class GeminiInterpreter(BaseIntentInterpreter):
    """Interprets complex voice commands using Google Gemini 2.5 Flash."""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        self.model_name = model_name
        self._client = None

    @property
    def name(self) -> str:
        return "gemini"

    def is_available(self) -> bool:
        """Check if Gemini API key exists in Windows Credential Manager or environment."""
        key = get_gemini_api_key()
        return bool(key and len(key) > 5)

    def _get_client(self):
        key = get_gemini_api_key()
        if not key:
            return None
        try:
            from google import genai
            return genai.Client(api_key=key)
        except Exception as exc:
            logger.error("Failed to initialize Google GenAI Client: %s", exc)
            return None

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        if not self.is_available():
            logger.debug("Gemini not available: API key not set.")
            return None

        client = self._get_client()
        if not client:
            return None

        from google.genai import types

        prompt = (
            f"You are the brain of Vyoma Handless, a voice-controlled desktop assistant on Windows 11.\n"
            f"Translate the user's natural language command into precise desktop actions.\n"
            f"User command: \"{transcript}\"\n"
        )
        if context:
            visible_elements = context.get("visible_elements")
            if visible_elements:
                prompt += f"Currently visible UI elements on active screen: {visible_elements}\n"
            recent_history = context.get("history")
            if recent_history:
                prompt += f"Recent command history: {recent_history}\n"

        contents: list = [prompt]
        screenshot_image = context.get("screenshot") if context else None
        if screenshot_image:
            contents.append(screenshot_image)
            prompt += "Analyze the attached screenshot to locate the relevant controls.\n"

        try:
            response = client.models.generate_content(
                model=self.model_name,
                contents=contents,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=GeminiActionPlan,
                    temperature=0.1,
                ),
            )

            plan: GeminiActionPlan = response.parsed
            actions: List[ActionRequest] = []
            for a in plan.actions:
                act_type = ActionType(a.action_type) if a.action_type in ActionType._value2member_map_ else ActionType.NONE
                win_act = WindowActionType(a.window_action) if a.window_action in WindowActionType._value2member_map_ else None
                actions.append(
                    ActionRequest(
                        action_type=act_type,
                        target=a.target,
                        target_type=a.target_type,
                        text=a.text,
                        keys=a.keys,
                        window_action=win_act,
                        scroll_direction=a.scroll_direction,
                        scroll_amount=a.scroll_amount,
                        requires_confirmation=a.requires_confirmation,
                    )
                )

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=plan.confidence,
                actions=actions,
                reasoning=plan.reasoning,
                clarification_question=plan.clarification_question,
            )
        except Exception as exc:
            logger.error("Gemini API call failed: %s", exc)
            return None
