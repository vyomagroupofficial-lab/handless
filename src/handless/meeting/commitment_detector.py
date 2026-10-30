"""Real-time Action Item & Commitment Detector for meeting audio transcripts.

Extracts promises, delegated tasks, deadlines, and deliverables as participants speak
with zero API latency, enabling live commitment badges and instant post-call agendas.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

from .models import ActionItem, TranscriptTurn

logger = logging.getLogger(__name__)

# Deadline detection pattern
DEADLINE_REGEX = re.compile(
    r"\b(?:by|before|on|until)\s+("
    r"(?:today|tomorrow|yesterday|eod|end of day|end of week|next week|cob|close of business)|"
    r"(?:monday|tuesday|wednesday|thursday|friday|saturday|sunday)(?:\s+(?:morning|afternoon|evening|night))?|"
    r"(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}(?:st|nd|rd|th)?|"
    r"\d{1,2}(?::\d{2})?\s*(?:am|pm|AM|PM)?"
    r")\b",
    re.IGNORECASE,
)

# Commitment intent patterns: (compiled_regex, default_assignee_type)
# default_assignee_type: "speaker" (whoever spoke), "other" (listener/team), "all" (collective)
COMMITMENT_PATTERNS = [
    # 1. First-person promises (I will, I'll, Let me, I am going to, I plan to)
    (
        re.compile(
            r"\b(?:i\s+will|i'll|i\s+am\s+going\s+to|i'm\s+going\s+to|let\s+me|i\s+can\s+handle|i'll\s+take\s+care\s+of|i\s+promise\s+to)\s+([a-z0-9\s\,\-\'\"]+)",
            re.IGNORECASE,
        ),
        "speaker",
    ),
    # 2. Direct requests / Delegations (Can you, Could you, Please, Make sure to)
    (
        re.compile(
            r"\b(?:please|could\s+you|can\s+you|would\s+you|make\s+sure\s+to|ensure\s+that\s+you|don't\s+forget\s+to)\s+([a-z0-9\s\,\-\'\"]+)",
            re.IGNORECASE,
        ),
        "other",
    ),
    # 3. Collective agreements (We will, We need to, We should, Let's)
    (
        re.compile(
            r"\b(?:we\s+need\s+to|we\s+should|we\s+have\s+to|we\s+will|we'll|let's|let\s+us)\s+([a-z0-9\s\,\-\'\"]+)",
            re.IGNORECASE,
        ),
        "all",
    ),
    # 4. Explicit markers (Action item:, Todo:)
    (
        re.compile(
            r"\b(?:action\s+item|to[\-\s]?do|follow[\-\s]?up|deliverable)\s*[:\-]\s*([a-z0-9\s\,\-\'\"]+)",
            re.IGNORECASE,
        ),
        "speaker",
    ),
]

# Action verbs that indicate a real task rather than casual conversation
ACTION_VERBS = {
    "send", "email", "share", "write", "create", "deploy", "release", "ship",
    "review", "check", "verify", "test", "fix", "update", "schedule", "organize",
    "prepare", "finalize", "investigate", "debug", "push", "merge", "call", "ping",
    "document", "summarize", "clean", "format", "export", "import", "build", "set",
}


class CommitmentDetector:
    """Detects commitments, assignments, and deadlines in spoken meeting turns."""

    @staticmethod
    def extract_commitments_from_text(text: str, speaker: str = "Speaker") -> List[ActionItem]:
        """Parse spoken text and return any detected action items/commitments."""
        if not text or len(text.strip()) < 10:
            return []

        clean_input = text.strip()
        items: List[ActionItem] = []

        # Find deadline if present in the sentence
        deadline_match = DEADLINE_REGEX.search(clean_input)
        due_date = deadline_match.group(1).strip().capitalize() if deadline_match else None

        for pattern, role_type in COMMITMENT_PATTERNS:
            for match in pattern.finditer(clean_input):
                raw_task = match.group(1).strip()
                if not raw_task or len(raw_task) < 5:
                    continue

                # Truncate at sentence boundaries or clause ends
                task_snippet = re.split(r"[\.\!\?\;]|\b(?:because|so\s+that|in\s+order\s+to)\b", raw_task, flags=re.IGNORECASE)[0].strip()

                # Verify that snippet starts with an action verb or contains meaningful action
                words = task_snippet.split()
                if not words:
                    continue

                first_word = words[0].lower()
                has_action_verb = first_word in ACTION_VERBS or any(w.lower() in ACTION_VERBS for w in words[:3])

                if not has_action_verb and len(words) > 8:
                    continue

                # Determine assignee
                if role_type == "speaker":
                    assignee = "You" if speaker.lower() in ("you", "me") else speaker
                elif role_type == "other":
                    # Check if a name was mentioned right before or inside
                    assignee = "Team"
                else:
                    assignee = "All"

                # Clean up task text
                formatted_task = task_snippet[:100].strip()
                # Remove trailing deadline from task string to keep task clean
                if due_date and due_date.lower() in formatted_task.lower():
                    formatted_task = re.sub(re.escape(due_date), "", formatted_task, flags=re.IGNORECASE).strip()
                formatted_task = re.sub(r"\b(?:by|before|on|until)\s*$", "", formatted_task, flags=re.IGNORECASE).strip()

                if len(formatted_task) >= 6:
                    formatted_task = formatted_task[0].upper() + formatted_task[1:]
                    item = ActionItem(
                        task=formatted_task,
                        assignee=assignee,
                        due_date=due_date,
                    )
                    # Deduplicate within this turn
                    if not any(it.task.lower() == item.task.lower() for it in items):
                        items.append(item)

        return items

    @classmethod
    def extract_from_turn(cls, turn: TranscriptTurn) -> List[ActionItem]:
        """Convenience method to extract action items from a TranscriptTurn object."""
        return cls.extract_commitments_from_text(turn.text, speaker=turn.speaker)

