"""Tier 3 Cloud Fallback: Groq Cloud AI Client.

Provides ultra-fast cloud LLM inference (300+ tokens/sec) via Groq's
OpenAI-compatible chat completions API using models such as Llama 3.3 70B
and Llama 3.1 8B. Serves as a high-capacity (14,400 free requests/day) fallback
when Gemini hits 429 quota exhaustion or as a preferred cloud provider.
"""

from __future__ import annotations

import json
import logging
import re
import urllib.error
import urllib.request
from typing import Any, Dict, List, Optional

from handless.security.credentials import get_groq_api_key

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Vyoma Handless, an intelligent desktop automation AI for Windows 11.
You have direct, full control over the user's Windows 11 PC via native hardware controllers.
You CAN and MUST control master volume, display brightness, power, audio mute, and apps.
NEVER say "I cannot directly control the desktop volume" or refuse any hardware or desktop command.
When the user asks to change volume or brightness, output action_type: "system_action".
When messaging someone in WhatsApp/Telegram/Discord/Slack/Teams (e.g. "select X and type Y to her", "type X and send her Y"):
  - Step 1: Click the contact (action_type: "click", target: "<contact name>", target_type: "contact").
  - Step 2: Click the message box (action_type: "click", target: "Type a message", target_type: "edit").
  - Step 3: Type message into the message box (action_type: "type", text: "<message>", target: "Type a message").
  - Step 4: If asked to send, press enter (action_type: "key_press", keys: "enter"). If asked to just type or wait, do NOT send.
  - NEVER type the message text into the contact search box!
Return ONLY valid JSON matching this schema:
{
  "actions": [
    {
      "action_type": "click|double_click|right_click|type|key_press|shortcut|scroll|launch_app|window_action|system_action|select|none",
      "system_action": "set_volume|volume_up|volume_down|mute|unmute|set_brightness|brightness_up|brightness_down|dark_mode|light_mode|lock_pc|sleep_pc|restart_pc|shutdown_pc|show_desktop|screenshot or null",
      "target": "element name or app name if applicable",
      "target_type": "button|edit|menu|tab|combobox or null",
      "text": "text to type if typing",
      "keys": "keys if shortcut or key_press",
      "window_action": "minimize|maximize|close|switch or null",
      "scroll_direction": "up|down or null",
      "scroll_amount": 3
    }
  ],
  "reasoning": "brief explanation",
  "answer_text": "conversational reply or answer if user asked a question instead of desktop action",
  "confidence": 0.95
}
"""


class GroqInterpreter(BaseIntentInterpreter):
    """High-speed cloud intent interpreter via Groq OpenAI-compatible API."""

    def __init__(
        self,
        model_name: str = "qwen/qwen3.8-27b",
        endpoint: str = "https://api.groq.com/openai/v1/chat/completions",
        timeout: float = 6.0,
    ) -> None:
        self.model_name = model_name
        self.endpoint = endpoint
        self.timeout = timeout
        self.conversation_history: List[Dict[str, str]] = []

    @property
    def name(self) -> str:
        return f"groq ({self.model_name})"

    def is_available(self) -> bool:
        """Check whether a Groq API key is present."""
        key = get_groq_api_key()
        return bool(key and len(key) > 5)

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        api_key = get_groq_api_key()
        if not api_key:
            return None

        # Build prompt with active screen and UI context
        user_prompt = f"User voice command: \"{transcript}\"\nRespond with a valid JSON object matching the schema.\n"
        if context:
            if context.get("visible_elements"):
                user_prompt += f"\nCurrently Visible UI Elements:\n{context['visible_elements']}\n"
            if context.get("control_tree"):
                user_prompt += f"\nActive Window Controls:\n{context['control_tree']}\n"

        messages = [{"role": "system", "content": SYSTEM_PROMPT}]
        for hist in self.conversation_history[-6:]:
            messages.append(hist)
        messages.append({"role": "user", "content": user_prompt})

        payload = {
            "model": self.model_name,
            "messages": messages,
            "temperature": 0.1,
            "response_format": {"type": "json_object"},
        }

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "VyomaHandless/1.0",
                },
                method="POST",
            )

            try:
                with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                    resp_data = json.loads(resp.read().decode("utf-8"))
            except urllib.error.HTTPError as h_err:
                body = ""
                try:
                    body = h_err.read().decode("utf-8", errors="ignore")
                except Exception:
                    pass
                # If json_validate_failed, retry once without response_format constraint
                if h_err.code == 400 and "json_validate_failed" in body:
                    logger.info("Groq json_validate_failed: Retrying without rigid response_format...")
                    payload.pop("response_format", None)
                    req_retry = urllib.request.Request(
                        self.endpoint,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "Authorization": f"Bearer {api_key}",
                            "User-Agent": "VyomaHandless/1.0",
                        },
                        method="POST",
                    )
                    with urllib.request.urlopen(req_retry, timeout=self.timeout) as resp:
                        resp_data = json.loads(resp.read().decode("utf-8"))
                else:
                    logger.warning("Groq API HTTP error %d: %s. Response: %s", h_err.code, h_err.reason, body)
                    return None

            choice = resp_data.get("choices", [{}])[0]
            content = choice.get("message", {}).get("content", "").strip()
            if not content:
                logger.warning("Groq returned empty response content.")
                return None

            clean_json = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL)
            clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json.strip(), flags=re.MULTILINE)
            clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()
            match = re.search(r"\{.*\}", clean_json, re.DOTALL)
            if match:
                plan_data = json.loads(match.group(0))
            else:
                plan_data = json.loads(clean_json)

            actions = self._parse_actions(plan_data.get("actions", []))

            # Track conversation history
            self.conversation_history.append({"role": "user", "content": transcript})
            reply_summary = plan_data.get("answer_text") or plan_data.get("reasoning") or "Executed desktop action(s)"
            self.conversation_history.append({"role": "assistant", "content": reply_summary})
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]

            return IntentResult(
                raw_transcript=transcript,
                source=self.name,
                confidence=float(plan_data.get("confidence", 0.9)),
                actions=actions,
                reasoning=plan_data.get("reasoning", "Interpreted via Groq"),
                answer_text=plan_data.get("answer_text"),
            )
        except urllib.error.HTTPError as h_err:
            body = ""
            try:
                body = h_err.read().decode("utf-8", errors="ignore")
            except Exception:
                pass
            logger.warning("Groq API HTTP error %d: %s. Response: %s", h_err.code, h_err.reason, body)
            return None
        except Exception as exc:
            logger.warning("Groq interpretation failed: %s", exc)
            return None

    def polish_text(
        self, raw_text: str, tone: str = "professional", context: Optional[str] = None
    ) -> str:
        """Polish spoken dictation into high-quality written text using Groq."""
        if not raw_text.strip():
            return ""

        api_key = get_groq_api_key()
        if not api_key:
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
        prompt += f"\nRaw Spoken Input:\n\"{raw_text}\"\n\nReturn ONLY the polished text without quotes, explanations, or markdown code blocks."

        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "You are a professional writing and dictation cleanup assistant."},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.2,
        }

        try:
            req = urllib.request.Request(
                self.endpoint,
                data=json.dumps(payload).encode("utf-8"),
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {api_key}",
                    "User-Agent": "VyomaHandless/1.0",
                },
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
            choice = resp_data.get("choices", [{}])[0]
            polished = choice.get("message", {}).get("content", "").strip()
            if (polished.startswith('"') and polished.endswith('"')) or (polished.startswith("'") and polished.endswith("'")):
                polished = polished[1:-1].strip()
            return polished or raw_text.strip()
        except Exception as exc:
            logger.warning("Groq text polishing failed: %s", exc)
            return raw_text.strip()

    def _parse_actions(self, raw_actions: List[Dict[str, Any]]) -> List[ActionRequest]:
        actions: List[ActionRequest] = []
        for a in raw_actions:
            act_type_str = str(a.get("action_type", "none")).lower()
            try:
                act_type = ActionType(act_type_str)
            except ValueError:
                act_type = ActionType.NONE

            win_act = None
            if a.get("window_action"):
                try:
                    win_act = WindowActionType(str(a["window_action"]).lower())
                except ValueError:
                    pass

            scroll_val = a.get("scroll_amount")
            try:
                scroll_amt = int(scroll_val) if scroll_val is not None else 3
            except (ValueError, TypeError):
                scroll_amt = 3

            actions.append(
                ActionRequest(
                    action_type=act_type,
                    target=a.get("target"),
                    target_type=a.get("target_type"),
                    text=a.get("text"),
                    keys=a.get("keys"),
                    window_action=win_act,
                    system_action=a.get("system_action"),
                    scroll_direction=a.get("scroll_direction"),
                    scroll_amount=scroll_amt,
                )
            )
        return actions
