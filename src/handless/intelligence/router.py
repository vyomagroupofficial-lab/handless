"""Intent Router coordinating Tier 1 (Rule), Tier 2 (Local LLM), and Tier 3 (Cloud Gemini).
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from .base import BaseIntentInterpreter
from .gemini_client import GeminiInterpreter
from .local_llm import LocalLLMInterpreter
from .local_parser import LocalRuleParser
from .models import IntentResult

logger = logging.getLogger(__name__)


class IntentRouter:
    """Routes voice transcripts through the multi-tier intelligence hierarchy."""

    def __init__(
        self,
        local_parser: Optional[LocalRuleParser] = None,
        local_llm: Optional[LocalLLMInterpreter] = None,
        gemini: Optional[GeminiInterpreter] = None,
        mode: str = "hybrid",  # "local_only", "hybrid", "cloud_only"
    ) -> None:
        self.local_parser = local_parser or LocalRuleParser()
        self.local_llm = local_llm or LocalLLMInterpreter()
        self.gemini = gemini or GeminiInterpreter()
        self.mode = mode

    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        cleaned = transcript.strip()
        if not cleaned:
            return None

        # Tier 1: Try deterministic local rules first (unless mode is strictly cloud_only)
        if self.mode != "cloud_only":
            local_res = self.local_parser.interpret(cleaned, context=context)
            if local_res and local_res.confidence >= 0.8:
                logger.info("Command routed to Tier 1 Local Rule: %s", local_res.reasoning)
                return local_res

        # If user selected local_only, attempt local LLM before giving up
        if self.mode == "local_only":
            if self.local_llm.is_available():
                logger.info("Command routed to Tier 2 Local LLM...")
                llm_res = self.local_llm.interpret(cleaned, context=context)
                if llm_res:
                    return llm_res
            return local_res  # may be None or lower confidence

        # Tier 2: Try Local LLM if available
        if self.local_llm.is_available():
            logger.info("Escalating command to Tier 2 Local LLM...")
            llm_res = self.local_llm.interpret(cleaned, context=context)
            if llm_res and llm_res.confidence >= 0.7:
                return llm_res

        # Tier 3: Escalate to Cloud Gemini
        if self.gemini.is_available():
            logger.info("Escalating command to Tier 3 Cloud Gemini...")
            gemini_res = self.gemini.interpret(cleaned, context=context)
            if gemini_res:
                return gemini_res

        # Fallback to local_res if any was found
        return local_res
