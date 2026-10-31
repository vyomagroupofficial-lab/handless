"""Local persistence and export storage for meeting transcripts and summaries.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from .models import MeetingSession, MeetingSummary, TranscriptTurn

logger = logging.getLogger(__name__)

DEFAULT_STORAGE_DIR = Path.home() / ".vyoma-handless" / "meetings"


class MeetingStorage:
    """Manages saving, loading, and searching past call transcripts and AI summaries."""

    def __init__(
        self,
        storage_dir: Optional[Union[Path, str]] = None,
        base_dir: Optional[Union[Path, str]] = None,
    ) -> None:
        target = storage_dir or base_dir or DEFAULT_STORAGE_DIR
        self.storage_dir = Path(target)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def save_session(self, session: MeetingSession) -> Tuple[Path, Path]:
        """Save a meeting session as structured JSON and companion Markdown."""
        file_path = self.storage_dir / f"{session.session_id}.json"
        md_path = self.storage_dir / f"{session.session_id}.md"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)

            # Companion Markdown file
            with open(md_path, "w", encoding="utf-8") as f:
                f.write(self.render_session_markdown(session))

            logger.info("Saved meeting session '%s' to %s", session.session_id, file_path)
            return file_path, md_path
        except Exception as exc:
            logger.error("Failed to save meeting session '%s': %s", session.session_id, exc)
            return file_path, md_path

    def load_session(self, session_id: str) -> Optional[MeetingSession]:
        """Load a meeting session from disk."""
        file_path = self.storage_dir / f"{session_id}.json"
        if not file_path.exists():
            return None
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return MeetingSession.from_dict(data)
        except Exception as exc:
            logger.error("Failed to load meeting session '%s': %s", session_id, exc)
            return None

    def list_sessions(self, limit: int = 50) -> List[Dict[str, Any]]:
        """List past meeting sessions sorted by most recent first."""
        sessions = []
        try:
            for p in self.storage_dir.glob("*.json"):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    sessions.append({
                        "session_id": data.get("session_id", p.stem),
                        "title": data.get("title", "Meeting"),
                        "app_name": data.get("app_name", "Call"),
                        "started_at": data.get("started_at", 0),
                        "date_str": time.strftime("%b %d, %Y", time.localtime(data.get("started_at", 0))),
                        "time_str": time.strftime("%I:%M %p", time.localtime(data.get("started_at", 0))),
                        "duration_str": data.get("duration_str", "00:00"),
                        "turns_count": len(data.get("turns", [])),
                        "has_summary": bool(data.get("summary")),
                    })
                except Exception:
                    continue
        except Exception as exc:
            logger.warning("Error listing meeting sessions: %s", exc)

        sessions.sort(key=lambda s: s["started_at"], reverse=True)
        return sessions[:limit]

    def delete_session(self, session_id: str) -> bool:
        """Delete a saved meeting session and its markdown companion."""
        json_path = self.storage_dir / f"{session_id}.json"
        md_path = self.storage_dir / f"{session_id}.md"
        deleted = False
        if json_path.exists():
            json_path.unlink()
            deleted = True
        if md_path.exists():
            md_path.unlink()
            deleted = True
        return deleted

    def search_transcripts(self, query: str) -> List[MeetingSession]:
        """Search across all saved meeting sessions for keywords."""
        if not query:
            return []
        q = query.lower()
        results = []
        for meta in self.list_sessions(limit=100):
            sess = self.load_session(meta["session_id"])
            if not sess:
                continue
            # Search title, app, turns, or summary
            if q in sess.title.lower() or q in sess.app_name.lower():
                results.append(sess)
                continue
            if any(q in turn.text.lower() for turn in sess.turns):
                results.append(sess)
                continue
            if sess.summary and q in sess.summary.markdown_full.lower():
                results.append(sess)
        return results

    def search_sessions(self, query: str) -> List[MeetingSession]:
        """Alias for search_transcripts."""
        return self.search_transcripts(query)

    @staticmethod
    def render_session_markdown(session: MeetingSession) -> str:
        """Format the entire meeting session as a publication-ready Markdown report."""
        date_str = time.strftime("%B %d, %Y", time.localtime(session.started_at))
        time_str = time.strftime("%I:%M %p", time.localtime(session.started_at))

        md = [
            f"# {session.title}",
            f"**App:** {session.app_name} | **Date:** {date_str} at {time_str} | **Duration:** {session.duration_str}\n",
            "---",
        ]

        if session.summary:
            s = session.summary
            if s.executive_summary:
                md.extend([
                    "## 🎯 Executive Summary",
                    s.executive_summary + "\n",
                ])

            if s.key_points:
                md.append("## 📌 Key Discussion Points")
                for kp in s.key_points:
                    md.append(f"- {kp}")
                md.append("")

            if s.action_items:
                md.append("## ✅ Action Items & Next Steps")
                for item in s.action_items:
                    assignee_str = f" (**{item.assignee}**)" if item.assignee and item.assignee != "Unassigned" else ""
                    check = "[x]" if item.completed else "[ ]"
                    md.append(f"- {check} {item.task}{assignee_str}")
                md.append("")

            if s.decisions:
                md.append("## 💡 Key Decisions")
                for dec in s.decisions:
                    md.append(f"- {dec}")
                md.append("")

            md.append("---\n")

        md.append("## 💬 Verbatim Transcript\n")
        for turn in session.turns:
            speaker_badge = "**You**" if turn.is_user else f"**{turn.speaker}**"
            md.append(f"**[{turn.time_str}]** {speaker_badge}: {turn.text}\n")

        return "\n".join(md)
