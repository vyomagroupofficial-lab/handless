"""Spoken text cleaner and punctuation formatter.

Inspired by OpenWhispr: cleans spoken audio transcriptions, converts spoken punctuation
commands into proper characters, strips speech disfluencies and filler words, and ensures
natural writing capitalization and spacing.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Spoken punctuation rules ordered to prevent partial matches
PUNCTUATION_RULES: List[Tuple[str, str]] = [
    (r"\bnew\s+paragraph\b", "\n\n"),
    (r"\b(?:new\s+line|newline)\b", "\n"),
    (r"\b(?:question\s+mark)\b", "?"),
    (r"\b(?:exclamation\s+mark|exclamation\s+point)\b", "!"),
    (r"\b(?:full\s+stop|period)\b", "."),
    (r"\bcomma\b", ","),
    (r"\bcolon\b", ":"),
    (r"\bsemicolon\b", ";"),
    (r"\b(?:open\s+quote|open\s+quotes)\b", '"'),
    (r"\b(?:close\s+quote|close\s+quotes)\b", '"'),
    (r"\bhyphen\b", "-"),
    (r"\bdash\b", " - "),
    (r"\bunderscore\b", "_"),
    (r"\bat\s+sign\b", "@"),
    (r"\bhashtag\b", "#"),
]

# Common conversational speech fillers
FILLER_WORDS = [
    r"\b(?:um|uh|er|ah)\b[\s,]*",
    r"\b(?:you\s+know|i\s+mean)\b[\s,]*",
]


def format_spoken_punctuation(text: str) -> str:
    """Translate verbal punctuation commands into standard punctuation marks."""
    if not text:
        return ""

    result = text
    for pattern, replacement in PUNCTUATION_RULES:
        result = re.sub(pattern, replacement, result, flags=re.IGNORECASE)

    # Normalize spaces around punctuation:
    # 1. Remove space before punctuation marks: "hello , world ." -> "hello, world."
    result = re.sub(r"\s+([,.:;?!])", r"\1", result)

    # 2. Ensure exactly one space after punctuation if followed by a word (except newlines)
    result = re.sub(r"([,.:;?!])([^\s\d\n])", r"\1 \2", result)

    # 3. Clean spacing around newlines
    result = re.sub(r"[ \t]+\n", "\n", result)
    result = re.sub(r"\n[ \t]+", "\n", result)

    return result.strip()


def remove_filler_words(text: str) -> str:
    """Remove common speech disfluencies and verbal hesitations."""
    if not text:
        return ""

    result = text
    for pattern in FILLER_WORDS:
        result = re.sub(pattern, "", result, flags=re.IGNORECASE)

    # Collapse multiple whitespace
    result = re.sub(r"[ ]{2,}", " ", result)
    return result.strip()


def fix_capitalization(text: str, capitalize_first: bool = True) -> str:
    """Capitalize sentence boundaries, newlines, and optionally initial word."""
    if not text:
        return ""

    # Capitalize the first character if requested
    if capitalize_first:
        chars = list(text)
        if chars and chars[0].isalpha():
            chars[0] = chars[0].upper()
        text = "".join(chars)

    # Capitalize letter following sentence-ending punctuation (. ? !)
    def _capitalize_match(m: re.Match) -> str:
        return m.group(1) + m.group(2).upper()

    text = re.sub(r"([.?!]\s+)([a-z])", _capitalize_match, text)

    # Capitalize after newline
    text = re.sub(r"(\n+)([a-z])", _capitalize_match, text)

    return text


def clean_spoken_text(
    text: str, remove_fillers: bool = True, capitalize_first: bool = True
) -> str:
    """Complete dictation cleanup pipeline.
    
    1. Removes conversational fillers (if enabled)
    2. Converts spoken punctuation commands
    3. Normalizes spacing and sentence-level capitalization
    """
    if not text:
        return ""

    cleaned = text
    if remove_fillers:
        cleaned = remove_filler_words(cleaned)

    cleaned = format_spoken_punctuation(cleaned)
    cleaned = fix_capitalization(cleaned, capitalize_first=capitalize_first)
    return cleaned
