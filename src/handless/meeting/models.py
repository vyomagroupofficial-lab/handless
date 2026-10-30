"""Data models for dual-stream meeting transcription, diarization, and summarization.
"""

from __future__ import annotations

import html
import re
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


# Keywords and patterns for Wispr Flow-style intelligent bolding
HIGHLIGHT_PATTERNS = [
    # Numbers, metrics, percentages, currency
    r"\b\d+(?:[\.,]\d+)?(?:\%|\b|k|M|B)?\b",
    r"\b(?:\$|€|£|₹)\s*\d+(?:[\.,]\d+)?\b",
    # Dates, days, times
    r"\b(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b",
    r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\b",
    r"\b\d{1,2}:\d{2}(?:\s*(?:AM|PM|am|pm))?\b",
    r"\b(?:today|tomorrow|yesterday|next week|this week|end of week|EOD|end of day)\b",
    # Action verbs & agreements
    r"\b(?:action item|deliverable|deadline|milestone|approved|agreed|decided|blocked)\b",
    r"\b(?:deploy|release|ship|review|schedule|finalize|implement|test|fix|launch)\b",
]

COMPILED_HIGHLIGHTS = re.compile(
    "|".join(f"({p})" for p in HIGHLIGHT_PATTERNS),
    re.IGNORECASE,
)


def apply_wispr_flow_highlights(text: str) -> str:
    """Smart-bold key terms, metrics, dates, and action verbs in transcript text."""
    if not text:
        return ""

    escaped = html.escape(text)

    def _replace(match: re.Match) -> str:
        word = match.group(0)
        # Avoid double-bolding
        return f"<b>{word}</b>"

    return COMPILED_HIGHLIGHTS.sub(_replace, escaped)


@dataclass
class TranscriptTurn:
    """Represents a single spoken statement from either the user or a call participant."""

    id: str
    speaker: str              # "You", "Speaker 1", "Speaker 2", etc.
    text: str
    timestamp: float = field(default_factory=time.time)
    time_str: str = ""        # e.g. "02:15" or "17:15:23"
    is_user: bool = False     # True if from microphone ("You"), False if from system loopback
    source: str = "mic"       # "mic" or "system"
    confidence: float = 0.95
    highlighted_html: str = ""

    def __post_init__(self) -> None:
        if not self.time_str:
            self.time_str = time.strftime("%H:%M:%S", time.localtime(self.timestamp))
        if not self.highlighted_html:
            self.highlighted_html = apply_wispr_flow_highlights(self.text)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "speaker": self.speaker,
            "text": self.text,
            "timestamp": self.timestamp,
            "time_str": self.time_str,
            "is_user": self.is_user,
            "source": self.source,
            "confidence": self.confidence,
            "highlighted_html": self.highlighted_html,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> TranscriptTurn:
        return cls(
            id=data.get("id", ""),
            speaker=data.get("speaker", "Speaker"),
            text=data.get("text", ""),
            timestamp=data.get("timestamp", time.time()),
            time_str=data.get("time_str", ""),
            is_user=data.get("is_user", False),
            source=data.get("source", "mic"),
            confidence=data.get("confidence", 0.95),
            highlighted_html=data.get("highlighted_html", ""),
        )


@dataclass
class ActionItem:
    """Action item extracted from meeting discussion."""

    task: str
    assignee: str = "Unassigned"
    completed: bool = False
    due_date: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task": self.task,
            "assignee": self.assignee,
            "completed": self.completed,
            "due_date": self.due_date,
        }


@dataclass
class MeetingSummary:
    """AI-synthesized summary of the call with key points and action items."""

    executive_summary: str = ""
    key_points: List[str] = field(default_factory=list)
    action_items: List[ActionItem] = field(default_factory=list)
    decisions: List[str] = field(default_factory=list)
    markdown_full: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "executive_summary": self.executive_summary,
            "key_points": self.key_points,
            "action_items": [item.to_dict() for item in self.action_items],
            "decisions": self.decisions,
            "markdown_full": self.markdown_full,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MeetingSummary:
        actions = [
            ActionItem(**item) if isinstance(item, dict) else ActionItem(str(item))
            for item in data.get("action_items", [])
        ]
        return cls(
            executive_summary=data.get("executive_summary", ""),
            key_points=data.get("key_points", []),
            action_items=actions,
            decisions=data.get("decisions", []),
            markdown_full=data.get("markdown_full", ""),
        )


@dataclass
class MeetingSession:
    """Complete meeting recording session with transcripts, audio metrics, and summary."""

    session_id: str
    title: str = "Meeting Call"
    app_name: str = "General Call"  # Zoom, Google Meet, WhatsApp, Teams, Discord
    started_at: float = field(default_factory=time.time)
    ended_at: Optional[float] = None
    turns: List[TranscriptTurn] = field(default_factory=list)
    live_action_items: List[ActionItem] = field(default_factory=list)
    summary: Optional[MeetingSummary] = None

    @property
    def duration_seconds(self) -> int:
        end = self.ended_at or time.time()
        return max(0, int(end - self.started_at))

    @property
    def duration_str(self) -> str:
        d = self.duration_seconds
        mins = d // 60
        secs = d % 60
        return f"{mins:02d}:{secs:02d}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "title": self.title,
            "app_name": self.app_name,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "duration_str": self.duration_str,
            "turns": [turn.to_dict() for turn in self.turns],
            "live_action_items": [item.to_dict() for item in self.live_action_items],
            "summary": self.summary.to_dict() if self.summary else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> MeetingSession:
        turns = [TranscriptTurn.from_dict(t) for t in data.get("turns", [])]
        live_items = [
            ActionItem(**item) if isinstance(item, dict) else ActionItem(str(item))
            for item in data.get("live_action_items", [])
        ]
        summary = MeetingSummary.from_dict(data["summary"]) if data.get("summary") else None
        return cls(
            session_id=data.get("session_id", ""),
            title=data.get("title", "Meeting Call"),
            app_name=data.get("app_name", "General Call"),
            started_at=data.get("started_at", time.time()),
            ended_at=data.get("ended_at"),
            turns=turns,
            live_action_items=live_items,
            summary=summary,
        )

    def generate_clean_transcript_text(self) -> str:
        """Generate human-readable plain text transcript with speaker tags."""
        lines = []
        for turn in self.turns:
            lines.append(f"[{turn.time_str}] {turn.speaker}: {turn.text}")
        return "\n".join(lines)

    def generate_claude_prompt(self) -> str:
        """Generate ready-to-paste tailored meta-prompt for Anthropic Claude or other LLMs."""
        clean_transcript = self.generate_clean_transcript_text()
        return (
            f"Here is the verbatim transcript from my {self.app_name} meeting titled \"{self.title}\" "
            f"({time.strftime('%b %d, %Y', time.localtime(self.started_at))} | Duration: {self.duration_str}):\n\n"
            f"<meeting_transcript>\n"
            f"{clean_transcript}\n"
            f"</meeting_transcript>\n\n"
            f"Please analyze this meeting and provide:\n"
            f"1. A concise Executive Summary of what was discussed.\n"
            f"2. A prioritized checklist of all Action Items, assigning owners/speakers and deadlines where mentioned.\n"
            f"3. Key Decisions reached and critical takeaways.\n"
            f"4. A professional follow-up email draft ready to send to the meeting participants."
        )

