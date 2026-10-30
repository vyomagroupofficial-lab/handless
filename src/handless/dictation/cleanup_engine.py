"""Auto Cleanup Engine - Four Configurable AI Tiers.

Provides multi-tier transcription post-processing inspired by Wispr Flow:
- None: 100% raw verbatim literal transcription (zero alterations).
- Light: Cleans verbal filler words ("um", "uh", "like", "you know"), stutters,
         and normalizes punctuation commands and sentence casing.
- Medium (Default): Enhances sentence flow, eliminates repetition, clarifies run-ons,
                    while strictly preserving user voice, meaning, and vocabulary.
- High (Executive): Full cognitive rewrite. Maximizes conciseness and punchiness,
                    converting spoken brainstorming into polished executive prose.

Includes dual-state raw tracking and 1-click revert/undo support.
"""

from __future__ import annotations

import difflib
import enum
import logging
import re
from typing import Any, Dict, List, Optional, Tuple

from pydantic import BaseModel, Field

from handless.dictation.text_cleaner import clean_spoken_text, format_spoken_punctuation, remove_filler_words

logger = logging.getLogger(__name__)


class CleanupLevel(str, enum.Enum):
    """The four levels of AI transcript modification."""
    NONE = "none"        # Literal verbatim, no changes
    LIGHT = "light"      # Fillers, punctuation, basic grammar
    MEDIUM = "medium"    # Clarity, flow, conciseness (Default)
    HIGH = "high"        # Executive rewrite, brevity, polish


class CleanupResult(BaseModel):
    """Encapsulates raw text, cleaned text, and diff information."""
    raw_text: str = Field(..., description="Original raw transcript from STT")
    cleaned_text: str = Field(..., description="Cleaned transcript after post-processing")
    level: CleanupLevel = Field(default=CleanupLevel.MEDIUM, description="Applied cleanup tier")
    diff_count: int = Field(default=0, description="Number of word alterations made")
    is_modified: bool = Field(default=False, description="Whether cleaned differs from raw")


# High-efficiency regex cleanups for Light and Medium tiers
FALSE_STARTS_REGEX = re.compile(
    r"\b([A-Za-z]+)\s+([A-Za-z]+)\s+\1\b", re.IGNORECASE
)
STUTTER_REGEX = re.compile(r"\b([A-Za-z]+)-\1\b", re.IGNORECASE)
REPETITIVE_PHRASES = [
    (r"\b(?:i\s+think\s+that\s+i\s+think|what\s+i\s+mean\s+is\s+what\s+i\s+mean)\b", ""),
    (r"\b(basically|actually|literally)\s+(?:basically|actually|literally)\b", r"\1"),
    (r"\b(?:sort\s+of|kind\s+of)\s+(?:like\s+)?", ""),
    (r"\b(?:in\s+order\s+to)\b", "to"),
    (r"\b(?:at\s+this\s+point\s+in\s+time)\b", "now"),
    (r"\b(?:due\s+to\s+the\s+fact\s+that)\b", "because"),
    (r"\b(?:for\s+the\s+purpose\s+of)\b", "for"),
]


def clean_light(text: str) -> str:
    """Level 1: Fast deterministic cleanup of fillers, stutters, and punctuation."""
    if not text:
        return ""
    # 1. Spoken text cleaning (fillers, punctuation mapping, capitalization)
    cleaned = clean_spoken_text(text, remove_fillers=True, capitalize_first=True)
    # 2. Fix stutters like "th-the" -> "the"
    cleaned = STUTTER_REGEX.sub(r"\1", cleaned)
    # 3. Fix simple duplicate words e.g. "the the" -> "the"
    cleaned = re.sub(r"\b(\w+)\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def clean_medium_heuristic(text: str) -> str:
    """Level 2 heuristic fallback: improve sentence flow and remove awkward verbal repetition."""
    cleaned = clean_light(text)
    if not cleaned:
        return ""

    # Remove conversational verbal padding
    cleaned = re.sub(r"\b(?:basically|actually|you\s+know|sort\s+of|kind\s+of)\b[\s,]*", "", cleaned, flags=re.IGNORECASE)

    for pat, rep in REPETITIVE_PHRASES:
        cleaned = re.sub(pat, rep, cleaned, flags=re.IGNORECASE)

    # Normalize awkward comma splices and collapsed whitespace
    cleaned = re.sub(r"\s*,\s*,+", ",", cleaned)
    cleaned = re.sub(r"\s+([,.?!])", r"\1", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned)

    # Clean double questions e.g. "what is that what is that?"
    cleaned = re.sub(r"\b(.{4,20})\s+\1\b", r"\1", cleaned, flags=re.IGNORECASE)
    return cleaned.strip()


def clean_text_with_level(
    raw_text: str,
    level: CleanupLevel | str = CleanupLevel.MEDIUM,
    llm_client: Optional[Any] = None,
) -> CleanupResult:
    """Apply selected auto cleanup level to raw transcription."""
    if not raw_text:
        return CleanupResult(
            raw_text="",
            cleaned_text="",
            level=CleanupLevel(level) if isinstance(level, str) else level,
            diff_count=0,
            is_modified=False,
        )

    if isinstance(level, str):
        try:
            level = CleanupLevel(level.lower().strip())
        except ValueError:
            level = CleanupLevel.MEDIUM

    # Level 0: None - pure verbatim raw
    if level == CleanupLevel.NONE:
        return CleanupResult(
            raw_text=raw_text,
            cleaned_text=raw_text,
            level=CleanupLevel.NONE,
            diff_count=0,
            is_modified=False,
        )

    # Level 1: Light - fillers & punctuation only
    if level == CleanupLevel.LIGHT:
        cleaned = clean_light(raw_text)
        diff_count = _count_word_diffs(raw_text, cleaned)
        return CleanupResult(
            raw_text=raw_text,
            cleaned_text=cleaned,
            level=CleanupLevel.LIGHT,
            diff_count=diff_count,
            is_modified=raw_text.strip() != cleaned.strip(),
        )

    # Level 2: Medium - Flow & Clarity
    if level == CleanupLevel.MEDIUM:
        cleaned = ""
        # If fast LLM available, use intelligent clarity prompt
        if llm_client and getattr(llm_client, "is_available", False):
            prompt = (
                "You are an expert spoken-dictation editor. Clean up the following speech transcript "
                "for readability, smooth sentence flow, and conciseness. Remove verbal hesitations, "
                "repetitive phrases, and fix awkward grammar. Keep the speaker's original tone, vocabulary, "
                "and exact intent. Return ONLY the cleaned text with no explanations or quotes.\n\n"
                f"Transcript:\n{raw_text}"
            )
            try:
                if hasattr(llm_client, "chat"):
                    cleaned = llm_client.chat(prompt).strip().strip('"\'')
                elif hasattr(llm_client, "generate"):
                    cleaned = llm_client.generate(prompt).strip().strip('"\'')
            except Exception as exc:
                logger.warning("LLM cleanup error, using heuristic fallback: %s", exc)

        if not cleaned:
            cleaned = clean_medium_heuristic(raw_text)

        diff_count = _count_word_diffs(raw_text, cleaned)
        return CleanupResult(
            raw_text=raw_text,
            cleaned_text=cleaned,
            level=CleanupLevel.MEDIUM,
            diff_count=diff_count,
            is_modified=raw_text.strip() != cleaned.strip(),
        )

    # Level 3: High - Executive Rewrite & Brevity
    if level == CleanupLevel.HIGH:
        cleaned = ""
        if llm_client and getattr(llm_client, "is_available", False):
            prompt = (
                "You are an executive communications editor. Rewrite the following dictated thoughts into "
                "exceptionally clear, punchy, concise, professional prose. Eliminate all wordiness and ramblings. "
                "Format with crisp sentence structure suitable for executive memos, emails, or docs. "
                "Return ONLY the rewritten text with no preamble or explanations.\n\n"
                f"Draft thoughts:\n{raw_text}"
            )
            try:
                if hasattr(llm_client, "chat"):
                    cleaned = llm_client.chat(prompt).strip().strip('"\'')
                elif hasattr(llm_client, "generate"):
                    cleaned = llm_client.generate(prompt).strip().strip('"\'')
            except Exception as exc:
                logger.warning("LLM high cleanup error, using heuristic fallback: %s", exc)

        if not cleaned:
            cleaned = clean_medium_heuristic(raw_text)

        diff_count = _count_word_diffs(raw_text, cleaned)
        return CleanupResult(
            raw_text=raw_text,
            cleaned_text=cleaned,
            level=CleanupLevel.HIGH,
            diff_count=diff_count,
            is_modified=raw_text.strip() != cleaned.strip(),
        )

    # Fallback to medium
    cleaned = clean_medium_heuristic(raw_text)
    return CleanupResult(
        raw_text=raw_text,
        cleaned_text=cleaned,
        level=CleanupLevel.MEDIUM,
        diff_count=_count_word_diffs(raw_text, cleaned),
        is_modified=raw_text.strip() != cleaned.strip(),
    )


def compute_text_diff(raw: str, cleaned: str) -> List[Tuple[str, str]]:
    """Generate visual word diff chunks: ('equal'|'insert'|'delete', text)."""
    raw_words = raw.split()
    clean_words = cleaned.split()
    matcher = difflib.SequenceMatcher(None, raw_words, clean_words)

    diffs: List[Tuple[str, str]] = []
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            diffs.append(("equal", " ".join(raw_words[i1:i2])))
        elif tag == "delete":
            diffs.append(("delete", " ".join(raw_words[i1:i2])))
        elif tag == "insert":
            diffs.append(("insert", " ".join(clean_words[j1:j2])))
        elif tag == "replace":
            diffs.append(("delete", " ".join(raw_words[i1:i2])))
            diffs.append(("insert", " ".join(clean_words[j1:j2])))
    return diffs


def _count_word_diffs(a: str, b: str) -> int:
    """Calculate the number of changed/added/removed words."""
    words_a = a.split()
    words_b = b.split()
    matcher = difflib.SequenceMatcher(None, words_a, words_b)
    diff = 0
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag != "equal":
            diff += max(i2 - i1, j2 - j1)
    return diff
