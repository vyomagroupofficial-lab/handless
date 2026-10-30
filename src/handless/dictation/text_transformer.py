"""Transforms Engine - Rewrite and Supercharge Selected Text.

Highlight any existing text across Windows applications (VS Code, Chrome, Slack, Word)
and transform it using built-in options:
- Polish: Make writing clearer, more concise, and articulate.
- Prompt Engineer: Restructure dictated text or rough notes into a highly effective,
                   well-formatted AI prompt ready for ChatGPT, Claude, or coding assistants.
- Fix Grammar: Correct typos, awkward phrasing, and punctuation.
- Executive Tone: Elevate writing to polished business and leadership communication.
- Bulletize: Convert narrative blocks into punchy structured bullet points.
"""

from __future__ import annotations

import enum
import logging
import re
from typing import Any, Optional

logger = logging.getLogger(__name__)


class TransformType(str, enum.Enum):
    """Supported text transformation modes."""
    POLISH = "polish"
    PROMPT_ENGINEER = "prompt_engineer"
    GRAMMAR = "grammar"
    TONE_EXECUTIVE = "tone_executive"
    TONE_CASUAL = "tone_casual"
    BULLETIZE = "bulletize"


PROMPT_TEMPLATES = {
    TransformType.POLISH: (
        "You are an expert editor. Polish the following text to make it exceptionally clear, "
        "concise, articulate, and engaging while preserving its original core meaning and intent. "
        "Fix awkward phrasing, eliminate redundancy, and improve rhythm. "
        "Return ONLY the polished text with no explanations, preambles, or quotes.\n\n"
        "Input Text:\n{text}"
    ),
    TransformType.PROMPT_ENGINEER: (
        "You are a world-class prompt engineer. Restructure the following draft thoughts, ideas, or instructions "
        "into a highly effective, structured, and comprehensive AI prompt suitable for frontier LLMs "
        "(Claude 3.7 / GPT-4o / Gemini 2.5).\n\n"
        "Format the output clearly using this structure:\n"
        "# Role & Objective\n"
        "# Context & Constraints\n"
        "# Step-by-Step Instructions\n"
        "# Expected Output Format\n\n"
        "Return ONLY the engineered prompt with no introductory chatter.\n\n"
        "Draft Notes / Ideas:\n{text}"
    ),
    TransformType.GRAMMAR: (
        "You are a precision copyeditor. Correct all grammatical errors, spelling mistakes, punctuation issues, "
        "and minor syntax flaws in the following text. Do not rewrite or alter the voice of the author. "
        "Return ONLY the corrected text with no commentary.\n\n"
        "Input Text:\n{text}"
    ),
    TransformType.TONE_EXECUTIVE: (
        "Rewrite the following text into polished, professional, executive-ready communication. "
        "Ensure directness, diplomatic phrasing, high confidence, and crisp organization suitable for "
        "senior stakeholders, executives, or formal client emails. "
        "Return ONLY the rewritten text with no preamble.\n\n"
        "Input Text:\n{text}"
    ),
    TransformType.TONE_CASUAL: (
        "Rewrite the following text into a friendly, warm, conversational, and approachable tone "
        "suitable for team chats (Slack/Discord) or personal messages. "
        "Return ONLY the rewritten text with no preamble.\n\n"
        "Input Text:\n{text}"
    ),
    TransformType.BULLETIZE: (
        "Convert the following information or paragraphs into clear, structured bullet points. "
        "Use bold key terms at the start of each bullet point for fast scanning. "
        "Return ONLY the bulleted list with no preamble.\n\n"
        "Input Text:\n{text}"
    ),
}


def transform_text_offline_heuristic(text: str, transform_type: TransformType) -> str:
    """Deterministic offline fallback when AI API is unavailable."""
    if not text:
        return ""

    if transform_type == TransformType.POLISH:
        # Heuristic polish: clean fillers, tighten phrasing, trim, normalize punctuation
        res = re.sub(r"\b(?:in\s+order\s+to)\b", "to", text, flags=re.IGNORECASE)
        res = re.sub(r"\b(?:basically|actually|literally|sort of|kind of)\b", "", res, flags=re.IGNORECASE)
        res = re.sub(r"\s+", " ", res).strip()
        res = re.sub(r"\s*([,.:;?!])\s*", r"\1 ", res).strip()
        return res

    elif transform_type == TransformType.BULLETIZE:
        # Split sentences into bullet points
        sentences = re.split(r"(?<=[.?!])\s+", text.strip())
        bullets = [f"• {s.strip()}" for s in sentences if s.strip()]
        return "\n".join(bullets) if bullets else f"• {text.strip()}"

    elif transform_type == TransformType.PROMPT_ENGINEER:
        # Offline structured template
        return (
            f"# Role & Objective\nAct as an expert assistant to accomplish the following goal.\n\n"
            f"# Core Instructions\n{text.strip()}\n\n"
            f"# Constraints & Quality Standards\n- Ensure accuracy, depth, and clarity.\n"
            f"- Avoid generic summaries; provide concrete actionable output."
        )

    # Default fallback
    return text.strip()


def transform_text(
    text: str,
    transform_type: TransformType | str = TransformType.POLISH,
    llm_client: Optional[Any] = None,
) -> str:
    """Execute text transformation on input text via LLM or heuristic fallback."""
    clean_input = text.strip()
    if not clean_input:
        return ""

    if isinstance(transform_type, str):
        try:
            transform_type = TransformType(transform_type.lower().strip())
        except ValueError:
            transform_type = TransformType.POLISH

    template = PROMPT_TEMPLATES.get(transform_type, PROMPT_TEMPLATES[TransformType.POLISH])
    prompt = template.format(text=clean_input)

    # 1. Try LLM transformation (Groq / Gemini / Local)
    if llm_client and getattr(llm_client, "is_available", False):
        try:
            if hasattr(llm_client, "chat"):
                res = llm_client.chat(prompt).strip()
                if res:
                    return res.strip('"\'')
            elif hasattr(llm_client, "generate"):
                res = llm_client.generate(prompt).strip()
                if res:
                    return res.strip('"\'')
        except Exception as exc:
            logger.warning("LLM text transform error, falling back to heuristic: %s", exc)

    # 2. Offline fallback
    return transform_text_offline_heuristic(clean_input, transform_type)
