"""Tier 2: Pluggable Local LLM Interpreter.

Supports offline local model servers (such as Ollama, Llama.cpp, LM Studio)
via standard HTTP JSON requests. Provides offline natural language reasoning
when local regex rules cannot determine the intent.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Optional
import urllib.error
import urllib.request

from .base import BaseIntentInterpreter
from .models import ActionRequest, ActionType, IntentResult

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are Vyoma Handless, an intelligent desktop automation AI.
Translate the user's voice command into desktop actions.
Return ONLY valid JSON matching this schema:
{
  "actions": [
    {
      "action_type": "click|double_click|right_click|type|key_press|shortcut|scroll|launch_app|window_action|none",
      "target": "element name or app name if applicable",
      "target_type": "button|edit|menu|tab or null",
      "text": "text to type if typing",
      "keys": "keys if shortcut or key_press",
      "scroll_direction": "up|down or null",
      "scroll_amount": 3
    }
  ],
  "reasoning": "brief explanation",
  "confidence": 0.9
}
"""


class LocalLLMInterpreter(BaseIntentInterpreter):
    """Interprets commands via a local LLM server (e.g. Ollama)."""

    def __init__(
        self,
        endpoint: str = "http://localhost:11434/api/generate",
        model: str = "qwen2.5-coder:3b",
        timeout: float = 3.0,
    ) -> None:
        self.endpoint = endpoint
        self.model = model
        self.timeout = timeout

    @property
    def name(self) -> str:
        return "local_llm"

    def is_available(self) -> bool:
        """Check if local LLM server is reachable."""
        try:
            # Quick ping to root host
            host_url = self.endpoint.split("/api/")[0]
            req = urllib.request.Request(host_url, method="HEAD")
            with urllib.request.urlopen(req, timeout=0.5):
                return True
        except Exception:
            return False

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        payload = {
            "model": self.model,
            "prompt": f"{SYSTEM_PROMPT}\nUser Command: {transcript}\nContext: {context or {}}\nOutput:",
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
                raw_response = parsed_resp.get("response", "")
                llm_output = json.loads(raw_response)

                actions = []
                for act in llm_output.get("actions", []):
                    actions.append(ActionRequest.model_validate(act))

                return IntentResult(
                    raw_transcript=transcript,
                    source=self.name,
                    confidence=float(llm_output.get("confidence", 0.8)),
                    actions=actions,
                    reasoning=llm_output.get("reasoning"),
                )
        except Exception as exc:
            logger.debug("Local LLM unavailable or error: %s", exc)
            return None
