"""Base abstract interface for modular intent interpreters.

Allows seamlessly swapping or stacking different intelligence engines
(Deterministic Rule Parser, Local LLM like Ollama/Llama.cpp, and Cloud Gemini)
without altering the application controller or action executor.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

from .models import IntentResult


class BaseIntentInterpreter(ABC):
    """Abstract base class for all intent interpreters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the interpreter engine."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Check if engine is configured and ready."""
        pass

    @abstractmethod
    def interpret(
        self, transcript: str, context: Optional[Dict[str, Any]] = None
    ) -> Optional[IntentResult]:
        """Parse voice transcript into an IntentResult.

        Args:
            transcript: Transcribed speech text.
            context: Optional UI context or recent history.

        Returns:
            IntentResult if confident, or None if unable to interpret.
        """
        pass
