"""Tier 2: Pluggable Local LLM Interpreter.

Supports offline local model servers (Ollama, LM Studio, Llama.cpp, vLLM, LocalAI)
via standard HTTP JSON requests. Provides offline natural language reasoning
when local regex rules cannot determine the intent.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional, Tuple
import urllib.error
import urllib.request

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult, WindowActionType

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Vyoma Handless, an intelligent desktop automation AI for Windows 11.
Translate the user's voice command into desktop actions.
Return ONLY valid JSON matching this schema:
{
  "actions": [
    {
      "action_type": "click|double_click|right_click|type|key_press|shortcut|scroll|launch_app|window_action|select|none",
      "target": "element name or app name if applicable",
      "target_type": "button|edit|menu|tab or null",
      "text": "text to type if typing",
      "keys": "keys if shortcut or key_press",
      "window_action": "minimize|maximize|close|switch or null",
      "scroll_direction": "up|down or null",
      "scroll_amount": 3
    }
  ],
  "reasoning": "brief explanation",
  "answer_text": "conversational reply or answer if user asked a question instead of desktop action",
  "confidence": 0.9
}
"""


def detect_local_engines() -> List[Dict[str, Any]]:
    """Probe for running local LLM servers (Ollama on 11434, LM Studio on 1234)."""
    engines = []
    
    # 1. Probe Ollama
    try:
        req = urllib.request.Request("http://localhost:11434/api/tags", method="GET")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("name") for m in data.get("models", [])]
            engines.append({
                "type": "ollama",
                "endpoint": "http://localhost:11434/api/generate",
                "models": models,
                "status": "online",
            })
    except Exception:
        pass

    # 2. Probe LM Studio / OpenAI-compatible
    try:
        req = urllib.request.Request("http://localhost:1234/v1/models", method="GET")
        with urllib.request.urlopen(req, timeout=0.6) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            models = [m.get("id") for m in data.get("data", [])]
            engines.append({
                "type": "openai_compatible",
                "endpoint": "http://localhost:1234/v1/chat/completions",
                "models": models,
                "status": "online",
            })
    except Exception:
        pass

    return engines


class LocalLLMInterpreter(BaseIntentInterpreter):
    """Interprets commands via a local LLM server (Ollama or LM Studio)."""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/api/generate",
        model: str = "qwen2.5-coder:3b",
        timeout: float = 4.0,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return f"local_llm ({self.model})"

    def is_available(self) -> bool:
        """Check if local LLM server is reachable."""
        try:
            host_url = self.endpoint.split("/api/")[0].split("/v1/")[0]
            req = urllib.request.Request(host_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=0.5):
                return True
        except Exception:
            return False

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        if not self.is_available():
            return None

        is_openai_format = "/v1/" in self.endpoint or "chat/completions" in self.endpoint
        user_prompt = f"User Command: {transcript}\nContext: {context or {}}\nOutput:"

        if is_openai_format:
            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                "temperature": 0.1,
            }
        else:
            payload = {
                "model": self.model,
                "prompt": f"{SYSTEM_PROMPT}\n{user_prompt}",
                "stream": False,
                "format": "json",
            }

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self.endpoint,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as response:
                res_body = response.read().decode("utf-8")
                parsed_resp = json.loads(res_body)

                if is_openai_format:
                    choices = parsed_resp.get("choices", [])
                    raw_text = choices[0]["message"]["content"] if choices else ""
                else:
                    raw_text = parsed_resp.get("response", "")

                # Clean markdown blocks and deepseek/reasoning tags
                clean_json = re.sub(r"<think>.*?</think>", "", raw_text, flags=re.DOTALL)
                clean_json = re.sub(r"^```(?:json)?\s*", "", clean_json.strip(), flags=re.MULTILINE)
                clean_json = re.sub(r"```$", "", clean_json.strip(), flags=re.MULTILINE).strip()
                match = re.search(r"\{.*\}", clean_json, re.DOTALL)
                if not match:
                    logger.debug("No JSON block in Local LLM output: %s", raw_text)
                    return None

                llm_output = json.loads(match.group(0))

                actions: List[ActionRequest] = []
                for act in llm_output.get("actions", []):
                    try:
                        act_type = ActionType(act.get("action_type")) if act.get("action_type") in ActionType._value2member_map_ else ActionType.NONE
                        win_act = WindowActionType(act.get("window_action")) if act.get("window_action") in WindowActionType._value2member_map_ else None
                        scroll_val = act.get("scroll_amount")
                        try:
                            scroll_amt = int(scroll_val) if scroll_val is not None else 3
                        except (ValueError, TypeError):
                            scroll_amt = 3
                        actions.append(
                            ActionRequest(
                                action_type=act_type,
                                target=act.get("target"),
                                target_type=act.get("target_type"),
                                text=act.get("text"),
                                keys=act.get("keys"),
                                window_action=win_act,
                                scroll_direction=act.get("scroll_direction"),
                                scroll_amount=scroll_amt,
                            )
                        )
                    except Exception as exc:
                        logger.debug("Error parsing local action: %s", exc)

                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=float(llm_output.get("confidence", 0.85)),
                    actions=actions,
                    reasoning=llm_output.get("reasoning", "Interpreted via local LLM"),
                    answer_text=llm_output.get("answer_text"),
                )
        except Exception as exc:
            logger.debug("Local LLM request failed: %s", exc)
            return None
