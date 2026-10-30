"""AI-powered meeting summarizer for executive notes, action items, and Claude prompts.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from .models import ActionItem, MeetingSession, MeetingSummary

logger = logging.getLogger(__name__)

SUMMARY_SYSTEM_PROMPT = (
    "You are an elite executive assistant and meeting note specialist. "
    "Analyze the following verbatim meeting transcript and extract structured meeting minutes. "
    "Respond ONLY with a valid JSON object matching this schema:\n"
    "{\n"
    '  "executive_summary": "A concise, high-level overview of the call (2-3 sentences).",\n'
    '  "key_points": ["Key topic or discussion point 1", "Key topic 2"],\n'
    '  "action_items": [\n'
    '    {"task": "Specific actionable task", "assignee": "Name of person or You", "due_date": "Date if mentioned"}\n'
    "  ],\n"
    '  "decisions": ["Important decision or consensus reached 1", "Decision 2"]\n'
    "}"
)


class MeetingSummarizer:
    """Summarizes multi-turn meeting transcripts into executive summaries, action items, and Claude meta-prompts."""

    def __init__(self, gemini_client: Optional[Any] = None, groq_client: Optional[Any] = None) -> None:
        self.gemini = gemini_client
        self.groq = groq_client

    def summarize_session(self, session: MeetingSession) -> MeetingSummary:
        """Generate structured AI summary of the meeting session."""
        if not session.turns:
            return MeetingSummary(
                executive_summary="No speech was recorded in this session.",
                key_points=[],
                action_items=[],
                decisions=[],
                markdown_full="*No speech recorded.*",
            )

        transcript_text = session.generate_clean_transcript_text()
        prompt = (
            f"Meeting Title: {session.title}\n"
            f"Platform: {session.app_name}\n"
            f"Duration: {session.duration_str}\n\n"
            f"Transcript:\n{transcript_text}"
        )

        response_text = ""
        # 1. Try Gemini
        if self.gemini and hasattr(self.gemini, "client") and self.gemini.client:
            try:
                response = self.gemini.client.models.generate_content(
                    model=getattr(self.gemini, "model_name", "gemini-2.5-flash"),
                    contents=f"{SUMMARY_SYSTEM_PROMPT}\n\n{prompt}",
                )
                response_text = response.text or ""
            except Exception as e:
                logger.warning("Gemini meeting summarization failed: %s", e)

        # 2. Try Groq fallback
        if not response_text and self.groq and hasattr(self.groq, "client") and self.groq.client:
            try:
                chat = self.groq.client.chat.completions.create(
                    model=getattr(self.groq, "model_name", "llama-3.3-70b-versatile"),
                    messages=[
                        {"role": "system", "content": SUMMARY_SYSTEM_PROMPT},
                        {"role": "user", "content": prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0.2,
                )
                response_text = chat.choices[0].message.content or ""
            except Exception as e:
                logger.warning("Groq meeting summarization failed: %s", e)

        # 3. Parse JSON or generate local heuristic summary
        summary = self._parse_summary_json(response_text)
        if not summary:
            summary = self._generate_heuristic_summary(session)

        # Build clean markdown_full without raw emojis
        md_lines = [
            f"### Executive Summary\n{summary.executive_summary}\n",
            "### Key Discussion Points",
        ]
        for kp in summary.key_points:
            md_lines.append(f"- {kp}")
        md_lines.append("\n### Action Items & Next Steps")
        for item in summary.action_items:
            assignee = f" (**{item.assignee}**)" if item.assignee and item.assignee != "Unassigned" else ""
            md_lines.append(f"- [ ] {item.task}{assignee}")
        if summary.decisions:
            md_lines.append("\n### Key Decisions")
            for dec in summary.decisions:
                md_lines.append(f"- {dec}")

        summary.markdown_full = "\n".join(md_lines)
        session.summary = summary
        return summary

    @staticmethod
    def _parse_summary_json(raw_text: str) -> Optional[MeetingSummary]:
        """Extract and parse JSON object from LLM response."""
        if not raw_text:
            return None
        try:
            # Strip markdown code blocks if present
            clean = raw_text.strip()
            if clean.startswith("```json"):
                clean = clean[7:]
            if clean.startswith("```"):
                clean = clean[3:]
            if clean.endswith("```"):
                clean = clean[:-3]
            clean = clean.strip()

            data = json.loads(clean)
            actions = [
                ActionItem(
                    task=a.get("task", ""),
                    assignee=a.get("assignee", "Unassigned"),
                    due_date=a.get("due_date"),
                )
                for a in data.get("action_items", [])
                if isinstance(a, dict) and a.get("task")
            ]
            return MeetingSummary(
                executive_summary=data.get("executive_summary", ""),
                key_points=data.get("key_points", []),
                action_items=actions,
                decisions=data.get("decisions", []),
            )
        except Exception as exc:
            logger.debug("Could not parse summary JSON: %s", exc)
            return None

    @staticmethod
    def _generate_heuristic_summary(session: MeetingSession) -> MeetingSummary:
        """Rule-based fallback summary when offline or without API keys."""
        turns = session.turns
        total = len(turns)
        user_turns = [t for t in turns if t.is_user]
        other_turns = [t for t in turns if not t.is_user]

        exec_summary = (
            f"Meeting held on {session.app_name} lasting {session.duration_str} with {total} conversational turns "
            f"({len(user_turns)} from You, {len(other_turns)} from call participants)."
        )

        key_points = []
        action_items = []
        for t in turns[:8]:
            if len(t.text.split()) > 4:
                key_points.append(f"{t.speaker}: {t.text[:120]}...")

        # Find action statements
        for t in turns:
            lower = t.text.lower()
            if any(w in lower for w in ("will", "need to", "action item", "todo", "make sure", "deploy", "review")):
                action_items.append(ActionItem(task=t.text, assignee=t.speaker))

        return MeetingSummary(
            executive_summary=exec_summary,
            key_points=key_points[:5],
            action_items=action_items[:6],
            decisions=["Discussed project updates and next milestones."],
        )

