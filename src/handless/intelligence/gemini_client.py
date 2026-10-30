"""Tier 3: Cloud Gemini Intelligence Client.

Integrates with Google AI Studio Gemini API (Gemini 2.5 Flash) using the
official `google-genai` Python SDK. Resolves complex multi-step reasoning,
ambiguous commands, follow-up interactions, and screen vision analysis.
Uses Windows Credential Manager to retrieve the API key securely.
"""

from __future__ import annotations

import concurrent.futures
import json
import logging
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from handless.security.credentials import get_gemini_api_key

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)


class GeminiSingleAction(BaseModel):
    action_type: str = Field(description="click, double_click, right_click, type, key_press, shortcut, scroll, launch_app, window_action, system_action, select, expand, collapse, none")
    system_action: Optional[str] = Field(default=None, description="set_volume, volume_up, volume_down, mute, unmute, set_brightness, brightness_up, brightness_down, dark_mode, light_mode, lock_pc, sleep_pc, restart_pc, shutdown_pc, show_desktop, screenshot")
    target: Optional[str] = Field(default=None, description="Target element name, label, or application")
    target_type: Optional[str] = Field(default=None, description="button, edit, menu, tab, window, combobox, list, tree")
    text: Optional[str] = Field(default=None, description="Text string if typing")
    keys: Optional[str] = Field(default=None, description="Key combinations if shortcut or key_press")
    window_action: Optional[str] = Field(default=None, description="minimize, maximize, close, switch")
    menu_path: Optional[str] = Field(default=None, description="Path for menu navigation, e.g. File->Save")
    select_value: Optional[str] = Field(default=None, description="Item or value to select in combobox or list")
    target_app: Optional[str] = Field(default=None, description="Target application name or regex for targeted window connection")
    scroll_direction: Optional[str] = Field(default=None, description="up or down")
    scroll_amount: int = Field(default=3)
    box_2d: Optional[List[int]] = Field(default=None, description="Bounding box [ymin, xmin, ymax, xmax] on a 0-1000 scale if element is visible in attached screenshot")
    requires_confirmation: bool = Field(default=False)


class GeminiActionPlan(BaseModel):
    actions: List[GeminiSingleAction] = Field(default_factory=list, description="Ordered sequence of actions to perform")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    reasoning: str = Field(description="Explanation of the planned actions or answer")
    answer_text: Optional[str] = Field(default=None, description="Direct conversational answer if the user asked an informational question or screen query")
    clarification_question: Optional[str] = Field(default=None, description="Question if command is too ambiguous")


class GeminiInterpreter(BaseIntentInterpreter):
    """Interprets complex voice commands and multi-turn conversations using Google Gemini 2.5 Flash."""

    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        self.model_name = model_name
        self._client = None
        self.conversation_history: List[Dict[str, str]] = []

    def clear_history(self) -> None:
        """Clear session conversational memory."""
        self.conversation_history.clear()

    def get_history(self) -> List[Dict[str, str]]:
        """Return a copy of recent conversational turns."""
        return list(self.conversation_history)

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
            f"You are the brain of Vyoma Handless, an intelligent voice-controlled desktop assistant on Windows 11.\n"
            f"You have direct, full control over the user's Windows 11 PC via native hardware and system controllers.\n"
            f"You CAN and MUST control master volume, display brightness, power, audio mute, and applications.\n"
            f"NEVER say 'I cannot directly control the desktop volume' or refuse any hardware or desktop command.\n"
            f"Always output action_type: 'system_action' for volume, brightness, power, or hardware adjustments.\n"
            f"When messaging someone in WhatsApp/Discord/Slack/Teams (e.g. 'select X and type Y to her', 'type X and send her Y'):\n"
            f"  - Click the contact (action_type: 'click', target: '<contact name>', target_type: 'contact')\n"
            f"  - Click message box (action_type: 'click', target: 'Type a message', target_type: 'edit')\n"
            f"  - Type text into message box (action_type: 'type', text: '<message>', target: 'Type a message')\n"
            f"  - If asked to send, press enter (action_type: 'key_press', keys: 'enter'). If asked to just type or wait, do NOT send.\n"
            f"  - NEVER type the message into the contact search box.\n"
            f"Translate the user's natural language command into precise desktop actions.\n"
            f"User command: \"{transcript}\"\n"
        )
        if context:
            visible_elements = context.get("visible_elements")
            if visible_elements:
                prompt += f"Currently visible UI elements on active screen: {visible_elements}\n"
            control_tree = context.get("control_tree")
            if control_tree and "No active window" not in control_tree:
                prompt += f"Active Window Control Hierarchy:\n{control_tree}\n"
            recent_history = context.get("history")
            if recent_history:
                prompt += f"Recent command history: {recent_history}\n"

        if self.conversation_history:
            prompt += "\nRecent Conversation Turns with User:\n"
            for turn in self.conversation_history[-6:]:
                role = "User" if turn.get("role") == "user" else "Vyoma Assistant"
                prompt += f"- {role}: {turn.get('text')}\n"

        screenshot_image = context.get("screenshot") if context else None
        screen_w, screen_h = context.get("screen_size", (1920, 1080)) if context else (1920, 1080)

        models_to_try = []
        if screenshot_image and "gemma" in self.model_name.lower():
            models_to_try.append("gemini-2.5-flash")
            models_to_try.append("gemini-2.5-flash-lite")
            models_to_try.append(self.model_name)
        else:
            models_to_try.append(self.model_name)
            for fallback in ("gemini-2.5-flash", "gemini-2.5-flash-lite"):
                if fallback not in models_to_try:
                    models_to_try.append(fallback)

        last_error = None
        for current_model in models_to_try:
            is_gemma = "gemma" in current_model.lower()
            current_prompt = prompt
            if is_gemma:
                current_prompt += (
                    "\nReturn ONLY valid JSON matching this schema without markdown or extra text:\n"
                    "{\n"
                    '  "actions": [\n'
                    '    {"action_type": "click|double_click|right_click|type|key_press|shortcut|scroll|launch_app|window_action|select|expand|collapse|none", '
                    '"target": "element or app name", "target_type": "button|edit|menu|tab|combobox|tree or null", "text": "text string", "keys": "shortcut", "select_value": "value", "menu_path": "path"}\n'
                    '  ],\n'
                    '  "confidence": 0.95,\n'
                    '  "reasoning": "explanation"\n'
                    "}\n"
                )

            contents: list = []
            if screenshot_image:
                current_prompt += (
                    "\n[LIVE DESKTOP SCREENSHOT ATTACHED]\n"
                    "Carefully examine open application windows, profile cards, buttons, avatars, tabs, icons, and menus.\n"
                    "If the user asks to click, interact with, or type into any visual element on screen, locate it in the screenshot and include its normalized bounding box in 'box_2d' [ymin, xmin, ymax, xmax] on a 0 to 1000 scale.\n"
                )
                contents.append(screenshot_image)
            contents.append(current_prompt)

            timeout_sec = 6.0 if is_gemma else 12.0
            try:
                def _call_api():
                    if is_gemma:
                        return client.models.generate_content(
                            model=current_model,
                            contents=contents,
                        )
                    else:
                        return client.models.generate_content(
                            model=current_model,
                            contents=contents,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                response_schema=GeminiActionPlan,
                                temperature=0.1,
                            ),
                        )

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(_call_api)
                    response = future.result(timeout=timeout_sec)

                if is_gemma:
                    text_resp = response.text.strip()
                    clean_json = re.sub(r"^```(?:json)?\s*", "", text_resp, flags=re.MULTILINE)
                    clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()
                    match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                    if match:
                        plan_data = json.loads(match.group(0))
                        plan = GeminiActionPlan.model_validate(plan_data)
                    else:
                        raise ValueError(f"No valid JSON object found in response: {text_resp}")
                else:
                    plan = response.parsed
                    if plan is None:
                        text_resp = getattr(response, "text", "") or ""
                        clean_json = re.sub(r"^```(?:json)?\s*", "", text_resp, flags=re.MULTILINE)
                        clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()
                        match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                        if match:
                            plan = GeminiActionPlan.model_validate(json.loads(match.group(0)))
                        else:
                            raise ValueError(f"Failed to parse response: {text_resp}")

                actions: List[ActionRequest] = []
                for a in plan.actions:
                    raw_act = (a.action_type or "").lower().strip()
                    raw_win = (a.window_action or "").lower().strip() if a.window_action else ""

                    # Default to NONE if not matched
                    act_type = ActionType(a.action_type) if a.action_type in ActionType._value2member_map_ else ActionType.NONE
                    win_act = WindowActionType(a.window_action) if a.window_action in WindowActionType._value2member_map_ else None
                    keys = a.keys

                    # Normalize app launching vs window actions
                    if raw_act in ("launch", "launch_app", "open", "start", "run"):
                        act_type = ActionType.LAUNCH_APP
                        win_act = None
                    elif raw_act == "window_action" and raw_win in ("open", "launch", "start"):
                        act_type = ActionType.LAUNCH_APP
                        win_act = None
                    elif raw_act == "window_action":
                        if raw_win in ("switch", "switch_window", "focus", "bring_up", "activate"):
                            win_act = WindowActionType.SWITCH
                        elif raw_win in ("close", "exit", "quit", "kill", "terminate"):
                            win_act = WindowActionType.CLOSE
                        elif raw_win in ("minimize", "min"):
                            win_act = WindowActionType.MINIMIZE
                        elif raw_win in ("maximize", "max", "fullscreen"):
                            win_act = WindowActionType.MAXIMIZE
                        elif raw_win in ("snap_left", "snap_window_left"):
                            win_act = WindowActionType.SNAP_LEFT
                        elif raw_win in ("snap_right", "snap_window_right"):
                            win_act = WindowActionType.SNAP_RIGHT
                        elif a.target and not win_act:
                            # Non-destructive switch/focus if target window/app is provided
                            win_act = WindowActionType.SWITCH
                    elif raw_act in ("new_tab", "tab"):
                        act_type = ActionType.SHORTCUT
                        keys = keys or "ctrl+t"
                    elif raw_act in ("close_tab",):
                        act_type = ActionType.SHORTCUT
                        keys = keys or "ctrl+w"

                    coords = None
                    if a.box_2d and len(a.box_2d) == 4:
                        ymin, xmin, ymax, xmax = a.box_2d
                        abs_x = int(((xmin + xmax) / 2.0 / 1000.0) * screen_w)
                        abs_y = int(((ymin + ymax) / 2.0 / 1000.0) * screen_h)
                        coords = (abs_x, abs_y)
                        logger.info("Gemini vision localized '%s' at pixel coordinates (%d, %d)", a.target or 'element', abs_x, abs_y)
                    actions.append(
                        ActionRequest(
                            action_type=act_type,
                            target=a.target,
                            target_type=a.target_type,
                            text=a.text,
                            keys=keys,
                            window_action=win_act,
                            system_action=a.system_action,
                            menu_path=a.menu_path,
                            select_value=a.select_value,
                            target_app=a.target_app,
                            scroll_direction=a.scroll_direction,
                            scroll_amount=a.scroll_amount,
                            coordinates=coords,
                            requires_confirmation=a.requires_confirmation,
                        )
                    )

                logger.info("Successfully interpreted command via Google model '%s'", current_model)

                # Record turn in conversational memory
                self.conversation_history.append({"role": "user", "text": transcript})
                reply_summary = plan.answer_text or plan.reasoning or (f"Executed {len(actions)} desktop action(s)" if actions else "Done")
                self.conversation_history.append({"role": "model", "text": reply_summary})
                if len(self.conversation_history) > 20:
                    self.conversation_history = self.conversation_history[-20:]

                return IntentResult(
                    raw_transcript=transcript,
                    source=f"google ({current_model})",
                    confidence=plan.confidence,
                    actions=actions,
                    reasoning=plan.reasoning,
                    clarification_question=plan.clarification_question,
                    answer_text=plan.answer_text,
                )
            except Exception as exc:
                last_error = exc
                logger.warning("Google model '%s' failed (%s). Trying fallback...", current_model, exc)

        logger.error("All Google models failed. Last error: %s", last_error)
        return None

    def polish_text(
        self, raw_text: str, tone: str = "professional", context: Optional[str] = None
    ) -> str:
        """Refine and polish spoken dictation into high-quality written text with specified tone."""
        if not raw_text.strip():
            return ""

        client = self._get_client()
        if not client:
            return raw_text.strip()

        tone_instructions = {
            "professional": "Tone: Polished, clear, courteous business communication suitable for email or workplace chat.",
            "casual": "Tone: Friendly, natural, concise message suitable for WhatsApp or Discord.",
            "bullets": "Tone: Structured bulleted list highlighting key takeaways and action items.",
            "commit": "Tone: Conventional Git commit message (e.g. feat: ..., fix: ..., docs: ...).",
            "grammar": "Tone: Exact original phrasing, fixing only typos, punctuation, and capitalization.",
        }
        chosen_tone = tone_instructions.get(tone.lower(), tone_instructions["professional"])

        prompt = (
            "You are an expert speech-to-text refiner and professional communication assistant.\n"
            "Take the following spoken voice transcript and polish it into crisp, high-quality written text.\n"
            f"{chosen_tone}\n"
            "Remove speech disfluencies (um, uh, like, you know), fix speech recognition misheard words, and ensure proper punctuation.\n"
        )
        if context:
            prompt += f"Active Application Context: {context}\n"

        prompt += f"\nRaw Spoken Input:\n\"{raw_text}\"\n\nReturn ONLY the polished text without quotes, explanations, or code blocks."

        try:
            target_model = self.model_name if "gemma" not in self.model_name.lower() else "gemini-2.5-flash"
            response = client.models.generate_content(
                model=target_model,
                contents=[prompt],
            )
            polished = response.text.strip() if response and response.text else raw_text
            if (polished.startswith('"') and polished.endswith('"')) or (polished.startswith("'") and polished.endswith("'")):
                polished = polished[1:-1].strip()
            return polished
        except Exception as exc:
            logger.error("Failed to polish text via Gemini: %s", exc)
            return raw_text.strip()

    def ask_grounded(self, query: str) -> Dict[str, Any]:
        """Answer informational and real-time questions with live Google Search Grounding."""
        client = self._get_client()
        if not client:
            return {"answer": "Gemini client not available (check API key)", "sources": [], "queries": []}

        try:
            from google.genai import types
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[query],
                config=types.GenerateContentConfig(
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    temperature=0.2,
                ),
            )
            answer = response.text.strip() if response and response.text else "No response returned."
            sources = []
            queries = []
            if response.candidates:
                gm = getattr(response.candidates[0], "grounding_metadata", None)
                if gm:
                    if getattr(gm, "web_search_queries", None):
                        queries = list(gm.web_search_queries)
                    if getattr(gm, "grounding_chunks", None):
                        for chunk in gm.grounding_chunks:
                            web = getattr(chunk, "web", None)
                            if web and getattr(web, "uri", None):
                                sources.append({
                                    "title": getattr(web, "title", "Source"),
                                    "uri": getattr(web, "uri", "")
                                })
            return {
                "answer": answer,
                "sources": sources[:6],
                "queries": queries,
            }
        except Exception as exc:
            logger.error("Grounded search failed: %s", exc)
            return {"answer": f"Search failed: {exc}", "sources": [], "queries": []}

    def generate_workflow_plan(self, prompt: str) -> Dict[str, Any]:
        """Convert a natural language macro description into an executable multi-action workflow."""
        client = self._get_client()
        if not client:
            return {"error": "Gemini client unavailable"}

        system_instruction = (
            "You are an expert Windows automation engineer.\n"
            "Convert the user's natural language request into a named, structured workflow containing an ordered sequence of desktop actions.\n"
            "Action types: launch_app, click, double_click, right_click, type, key_press, shortcut, scroll, window_action, select, none.\n"
            "For shortcut, use formats like 'win+d', 'ctrl+t', 'ctrl+w', 'alt+tab', 'win+left', 'win+right'.\n"
            "For launch_app, target is app name (e.g. 'chrome', 'code', 'notepad', 'wt', 'calc', 'spotify').\n"
            "Return valid JSON with: name, description, icon (single emoji), trigger_phrases (list of strings), actions (list of action objects)."
        )

        try:
            from google.genai import types
            resp = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[f"User request: '{prompt}'\n\nReturn JSON only."],
                config=types.GenerateContentConfig(
                    system_instruction=system_instruction,
                    response_mime_type="application/json",
                    temperature=0.1,
                ),
            )
            text_resp = resp.text.strip() if resp and resp.text else "{}"
            clean_json = re.sub(r"^```(?:json)?\s*", "", text_resp, flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                return json.loads(match.group(0))
            return json.loads(text_resp)
        except Exception as exc:
            logger.error("Failed to generate workflow plan: %s", exc)
            return {"error": str(exc)}

