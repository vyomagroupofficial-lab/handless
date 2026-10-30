"""Transcription History, Local Retention, and Session Recovery Journal.

Provides resilient local journaling inspired by Wispr Flow:
- Tracks all raw speech, cleaned speech, cleanup levels, target apps, and timestamps.
- Auto-recovers interrupted or pending dictation sessions upon app launch.
- Provides 1-click retry for failed transcriptions.
- Manages local data retention policies (Never delete, 30 days, 7 days, Incognito).
- Exports history to Markdown and JSON.
"""

from __future__ import annotations

import json
import logging
import os
import threading
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_DIR = Path(os.path.expanduser("~")) / ".handless" / "history"
DEFAULT_HISTORY_FILE = DEFAULT_HISTORY_DIR / "transcription_journal.json"


class HistoryEntry(BaseModel):
    """Detailed record of a single dictation, action, or transformation event."""
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    timestamp: float = Field(default_factory=time.time)
    raw_text: str = Field(default="", description="Original raw transcript from STT or command")
    cleaned_text: str = Field(default="", description="Cleaned transcript or action execution result")
    cleanup_level: str = Field(default="medium", description="Cleanup tier applied")
    target_app: str = Field(default="Active Window", description="Application where text was typed or action was run")
    sector: str = Field(default="Dictation", description="Activity sector: System, Apps, Web, Dictation, Files, Automation")
    entry_type: str = Field(default="dictation", description="dictation, action, conversation")
    language: str = Field(default="en", description="Spoken language code")
    duration_sec: float = Field(default=0.0, description="Duration of audio recording in seconds")
    status: str = Field(default="completed", description="Status: completed, pending, failed, recovered")
    transform_applied: Optional[str] = Field(default=None, description="Any transform applied (e.g. polish)")
    error_message: Optional[str] = Field(default=None, description="Details if status is failed")

    @property
    def formatted_time(self) -> str:
        """Human-readable time string (e.g. 'Today, 2:45 PM')."""
        t = time.localtime(self.timestamp)
        now = time.localtime()
        if t.tm_yday == now.tm_yday and t.tm_year == now.tm_year:
            return time.strftime("Today, %I:%M %p", t)
        elif t.tm_yday == now.tm_yday - 1 and t.tm_year == now.tm_year:
            return time.strftime("Yesterday, %I:%M %p", t)
        return time.strftime("%b %d, %I:%M %p", t)


class HistoryJournal:
    """Thread-safe persistent journal with recovery and retention management."""

    def __init__(
        self,
        file_path: Optional[Path] = None,
        retention_policy: str = "never",  # never, 30_days, 7_days, incognito
    ) -> None:
        self.file_path = file_path or DEFAULT_HISTORY_FILE
        self.retention_policy = retention_policy.lower().strip()
        self._lock = threading.Lock()
        self._entries: List[HistoryEntry] = []
        self._is_incognito = self.retention_policy == "incognito"

        self._ensure_storage()
        self._load()

    def _ensure_storage(self) -> None:
        if self._is_incognito:
            return
        try:
            self.file_path.parent.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            logger.warning("Could not create history directory: %s", exc)

    def _load(self) -> None:
        if self._is_incognito or not self.file_path.exists():
            return
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    self._entries = [HistoryEntry(**item) for item in data if isinstance(item, dict)]
            logger.info("HistoryJournal: Loaded %d historical entries.", len(self._entries))
        except Exception as exc:
            logger.error("HistoryJournal: Failed loading history file: %s", exc)
            self._entries = []

    def _save_locked(self) -> None:
        if self._is_incognito:
            return
        try:
            temp_path = self.file_path.with_suffix(".tmp")
            data = [e.model_dump() for e in self._entries]
            with open(temp_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            temp_path.replace(self.file_path)
        except Exception as exc:
            logger.error("HistoryJournal: Failed saving entries: %s", exc)

    def add_entry(self, entry: HistoryEntry) -> HistoryEntry:
        """Append a new dictation record to memory and persistent journal."""
        with self._lock:
            self._entries.insert(0, entry)
            self._save_locked()
        logger.debug("HistoryJournal: Added entry %s for app %s", entry.id, entry.target_app)
        return entry

    def record_dictation(
        self,
        raw_text: str,
        cleaned_text: str,
        cleanup_level: str = "medium",
        target_app: str = "Active Window",
        language: str = "en",
        duration_sec: float = 0.0,
        status: str = "completed",
        sector: str = "Dictation",
    ) -> HistoryEntry:
        """Create and persist a new dictation entry in one call."""
        entry = HistoryEntry(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            cleanup_level=cleanup_level,
            target_app=target_app,
            language=language,
            duration_sec=duration_sec,
            status=status,
            sector=sector,
            entry_type="dictation",
        )
        return self.add_entry(entry)

    def record_action(
        self,
        raw_text: str,
        cleaned_text: str,
        action_name: str = "desktop_action",
        sector: str = "System",
        target_app: str = "Windows",
        status: str = "completed",
    ) -> HistoryEntry:
        """Create and persist an automated desktop action entry."""
        entry = HistoryEntry(
            raw_text=raw_text,
            cleaned_text=cleaned_text,
            cleanup_level=action_name,
            target_app=target_app,
            status=status,
            sector=sector,
            entry_type="action",
        )
        return self.add_entry(entry)

    def get_sector_stats(self) -> Dict[str, int]:
        """Compute task and activity counts broken down by sector."""
        stats = {
            "System": 0,
            "Apps": 0,
            "Web": 0,
            "Dictation": 0,
            "Files": 0,
            "Automation": 0,
        }
        with self._lock:
            for e in self._entries:
                sec = e.sector if e.sector in stats else "System"
                stats[sec] += 1
        return stats

    def update_entry(self, entry_id: str, **kwargs: Any) -> Optional[HistoryEntry]:
        """Update fields of an existing entry (e.g. status, error)."""
        with self._lock:
            for entry in self._entries:
                if entry.id == entry_id:
                    for k, v in kwargs.items():
                        if hasattr(entry, k):
                            setattr(entry, k, v)
                    self._save_locked()
                    return entry
        return None

    def get_entries(
        self,
        limit: int = 100,
        search: Optional[str] = None,
        app_filter: Optional[str] = None,
        sector_filter: Optional[str] = None,
    ) -> List[HistoryEntry]:
        """Query entries with optional filtering by text, application, and sector."""
        with self._lock:
            results = list(self._entries)

        if sector_filter and sector_filter.lower() != "all":
            flt_sec = sector_filter.lower()
            results = [e for e in results if flt_sec in e.sector.lower()]

        if app_filter and app_filter.lower() != "all":
            flt = app_filter.lower()
            results = [e for e in results if flt in e.target_app.lower()]

        if search:
            q = search.lower().strip()
            results = [
                e for e in results
                if q in e.raw_text.lower() or q in e.cleaned_text.lower() or q in e.target_app.lower() or q in e.sector.lower()
            ]

        return results[:limit]

    def get_last_entry(self) -> Optional[HistoryEntry]:
        """Get the most recent dictation entry."""
        with self._lock:
            return self._entries[0] if self._entries else None

    def recover_interrupted_sessions(self) -> List[HistoryEntry]:
        """Scan for any sessions that were pending when the app closed and mark as recovered."""
        recovered = []
        with self._lock:
            for entry in self._entries:
                if entry.status == "pending":
                    entry.status = "recovered"
                    recovered.append(entry)
            if recovered:
                self._save_locked()
                logger.info("HistoryJournal: Recovered %d interrupted dictation sessions.", len(recovered))
        return recovered

    def apply_retention_policy(self) -> int:
        """Purge entries exceeding the configured retention duration."""
        if self._is_incognito or self.retention_policy == "never":
            return 0

        now = time.time()
        max_age_seconds = {
            "7_days": 7 * 86400,
            "30_days": 30 * 86400,
        }.get(self.retention_policy, 0)

        if not max_age_seconds:
            return 0

        with self._lock:
            initial_count = len(self._entries)
            cutoff = now - max_age_seconds
            self._entries = [e for e in self._entries if e.timestamp >= cutoff]
            purged = initial_count - len(self._entries)
            if purged > 0:
                self._save_locked()
                logger.info("HistoryJournal: Purged %d expired entries under '%s' policy.", purged, self.retention_policy)
        return purged

    def clear_all(self) -> None:
        """Wipe all historical records."""
        with self._lock:
            self._entries.clear()
            self._save_locked()
        logger.info("HistoryJournal: Cleared all history.")

    def export_to_markdown(self, output_path: Optional[Path] = None) -> Path:
        """Generate a structured Markdown export of the entire dictation history and write to disk."""
        with self._lock:
            entries = list(self._entries)

        lines = [
            "# Vyoma Handless — Transcription & Dictation History",
            f"*Generated on {time.strftime('%Y-%m-%d %H:%M:%S')} | Total Records: {len(entries)}*",
            "",
            "---",
            "",
        ]

        for e in entries:
            lines.append(f"### {e.formatted_time} — `{e.target_app}`")
            lines.append(f"- **Language**: `{e.language.upper()}` | **Level**: `{e.cleanup_level.title()}` | **Status**: `{e.status}`")
            if e.raw_text != e.cleaned_text:
                lines.append(f"- **Raw**: *\"{e.raw_text}\"*")
                lines.append(f"- **Cleaned**: **\"{e.cleaned_text}\"**")
            else:
                lines.append(f"- **Transcript**: **\"{e.cleaned_text}\"**")
            lines.append("")

        md_content = "\n".join(lines)
        target = output_path or (self.file_path.parent / f"dictation_history_{int(time.time())}.md")
        target.parent.mkdir(parents=True, exist_ok=True)
        with open(target, "w", encoding="utf-8") as f:
            f.write(md_content)
        return target
