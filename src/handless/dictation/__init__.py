"""Dictation module for Vyoma Handless.

Inspired by OpenWhispr: provides spoken punctuation parsing, conversational filler cleanup,
and clipboard-preserving auto-paste with terminal-aware keystroke simulation.
"""

from .text_cleaner import clean_spoken_text, format_spoken_punctuation
from .paste_controller import PasteController, paste_text, is_terminal_window
from .flow_overlay import WisprFlowOverlay
from .speculative_engine import (
    SpeculativeDictationEngine,
    SpeculativeResult,
    SpeculativeSession,
)

__all__ = [
    "clean_spoken_text",
    "format_spoken_punctuation",
    "PasteController",
    "paste_text",
    "is_terminal_window",
    "WisprFlowOverlay",
    "SpeculativeDictationEngine",
    "SpeculativeResult",
    "SpeculativeSession",
]
