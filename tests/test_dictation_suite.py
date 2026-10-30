"""Comprehensive Test Suite for Wispr Flow Dictation Suite.

Validates:
1. 4-Level Auto Cleanup Engine (None, Light, Medium, High) + Diffs
2. Text Transforms Engine (Polish, Prompt Engineer, Grammar, Executive, Bulletize)
3. 100+ Languages Manager & Whisper ISO Resolution
4. Transcription History Journal, Interrupted Session Recovery & Retention
5. Deterministic Voice Intent Parsing for all Dictation controls
6. Interactive Flow & Transform UI Overlays
"""

import os
import shutil
import tempfile
import time
from pathlib import Path
import pytest

from handless.dictation.cleanup_engine import (
    CleanupLevel,
    CleanupResult,
    clean_text_with_level,
    compute_text_diff,
)
from handless.dictation.text_transformer import (
    PROMPT_TEMPLATES,
    TransformType,
    transform_text,
)
from handless.dictation.language_manager import LanguageManager, WHISPER_LANGUAGES
from handless.dictation.history_journal import HistoryEntry, HistoryJournal
from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType


# =========================================================================
# 1. AUTO CLEANUP ENGINE TESTS
# =========================================================================

def test_cleanup_level_none():
    raw = "um so like I was saying comma we should definitely check this out"
    res = clean_text_with_level(raw, level=CleanupLevel.NONE)
    assert res.level == CleanupLevel.NONE
    assert res.cleaned_text == raw
    assert not res.is_modified
    assert res.diff_count == 0


def test_cleanup_level_light():
    raw = "um so uh we need to finish this report period"
    res = clean_text_with_level(raw, level=CleanupLevel.LIGHT)
    assert res.level == CleanupLevel.LIGHT
    assert "um" not in res.cleaned_text.lower()
    assert "uh" not in res.cleaned_text.lower()
    assert "period" not in res.cleaned_text.lower()
    assert res.cleaned_text.endswith(".")
    assert res.is_modified


def test_cleanup_level_medium():
    raw = "um basically like I just think that we should definitely proceed with the plan comma you know"
    res = clean_text_with_level(raw, level=CleanupLevel.MEDIUM)
    assert res.level == CleanupLevel.MEDIUM
    assert "basically" not in res.cleaned_text.lower()
    assert "you know" not in res.cleaned_text.lower()
    assert "comma" not in res.cleaned_text.lower()
    assert res.is_modified


def test_cleanup_level_high():
    raw = "in order to make sure that we are able to reach our quarterly revenue goals we should start marketing"
    res = clean_text_with_level(raw, level=CleanupLevel.HIGH)
    assert res.level == CleanupLevel.HIGH
    # "in order to" should be tightened to "to"
    assert "in order to" not in res.cleaned_text.lower()
    assert res.is_modified


def test_text_diff_computation():
    raw = "I um think so"
    cleaned = "I think so"
    diffs = compute_text_diff(raw, cleaned)
    assert len(diffs) > 0
    # diffs is list of (tag, text)
    tags = [tag for tag, text in diffs]
    assert "delete" in tags or "replace" in tags or "equal" in tags


# =========================================================================
# 2. TEXT TRANSFORMS ENGINE TESTS
# =========================================================================

def test_transform_types_enum():
    assert TransformType.POLISH.value == "polish"
    assert TransformType.PROMPT_ENGINEER.value == "prompt_engineer"
    assert TransformType.GRAMMAR.value == "grammar"
    assert TransformType.TONE_EXECUTIVE.value == "tone_executive"
    assert TransformType.BULLETIZE.value == "bulletize"


def test_transform_bulletize_fallback():
    text = "First we need to review requirements. Second build prototype. Finally test and deploy."
    res = transform_text(text, transform_type=TransformType.BULLETIZE)
    assert "•" in res
    assert res.count("•") >= 2


def test_transform_polish_fallback():
    text = "basically in order to like proceed we should do it"
    res = transform_text(text, transform_type=TransformType.POLISH)
    assert "basically" not in res.lower()
    assert "in order to" not in res.lower()


def test_transform_prompt_engineer_fallback():
    text = "write a python script to parse logs and send alerts"
    res = transform_text(text, transform_type=TransformType.PROMPT_ENGINEER)
    assert "# ROLE & OBJECTIVE" in res or "# CONTEXT" in res or "Objective" in res
    assert "python" in res.lower()


def test_prompt_engineering_template_builder():
    tmpl = PROMPT_TEMPLATES[TransformType.PROMPT_ENGINEER]
    assert "{text}" in tmpl
    formatted = tmpl.format(text="create a landing page for ai copilot")
    assert "landing page" in formatted.lower()
    assert "Role & Objective" in formatted or "Prompt" in formatted


# =========================================================================
# 3. 100+ LANGUAGES MANAGER TESTS
# =========================================================================

def test_language_manager_catalog():
    lm = LanguageManager()
    assert len(WHISPER_LANGUAGES) >= 95
    assert "en" in WHISPER_LANGUAGES
    assert "hi" in WHISPER_LANGUAGES
    assert "es" in WHISPER_LANGUAGES
    assert "fr" in WHISPER_LANGUAGES
    assert "ja" in WHISPER_LANGUAGES
    assert "de" in WHISPER_LANGUAGES


def test_language_manager_resolution():
    lm = LanguageManager()
    assert lm.resolve_code("Spanish") == "es"
    assert lm.resolve_code("hindi") == "hi"
    assert lm.resolve_code("fr") == "fr"
    assert lm.resolve_code("auto") == "auto"
    assert lm.resolve_code("unknown_xyz") == "en"


def test_whisper_language_code():
    lm = LanguageManager(current_language="es")
    assert lm.whisper_language == "es"
    lm.set_language("auto")
    assert lm.whisper_language is None  # Auto omitting param activates detection
    lm.set_language("hi")
    assert lm.whisper_language == "hi"
    assert lm.get_language_name("hi") == "Hindi"


def test_pinned_languages():
    lm = LanguageManager()
    pinned = lm.pinned_languages
    assert len(pinned) >= 8
    codes = [code for code, name in pinned]
    assert "en" in codes
    assert "es" in codes
    assert "hi" in codes


# =========================================================================
# 4. TRANSCRIPTION HISTORY JOURNAL & RECOVERY TESTS
# =========================================================================

@pytest.fixture
def temp_journal_dir():
    temp_dir = tempfile.mkdtemp()
    yield Path(temp_dir)
    shutil.rmtree(temp_dir, ignore_errors=True)


def test_history_journal_record_and_query(temp_journal_dir):
    journal_path = temp_journal_dir / "journal.json"
    journal = HistoryJournal(file_path=journal_path, retention_policy="never")

    entry1 = journal.record_dictation(
        raw_text="um test dictation one",
        cleaned_text="Test dictation one.",
        cleanup_level="medium",
        target_app="VS Code",
        language="en",
        duration_sec=2.5,
    )
    assert entry1.id is not None
    assert entry1.cleaned_text == "Test dictation one."

    entry2 = journal.record_dictation(
        raw_text="hola como estas",
        cleaned_text="Hola, ¿cómo estás?",
        cleanup_level="light",
        target_app="Google Chrome",
        language="es",
        duration_sec=1.8,
    )

    all_entries = journal.get_entries()
    assert len(all_entries) == 2
    assert all_entries[0].id == entry2.id  # Newest first

    # Filter by search
    searched = journal.get_entries(search="como estas")
    assert len(searched) == 1
    assert searched[0].language == "es"

    # Filter by app
    app_filtered = journal.get_entries(app_filter="VS Code")
    assert len(app_filtered) == 1
    assert app_filtered[0].target_app == "VS Code"


def test_history_journal_interrupted_session_recovery(temp_journal_dir):
    journal_path = temp_journal_dir / "journal.json"
    journal = HistoryJournal(file_path=journal_path, retention_policy="never")

    # Simulate an interrupted session left in 'pending' status
    pending_entry = HistoryEntry(
        raw_text="interrupted audio text",
        cleaned_text="",
        status="pending",
        target_app="Slack",
    )
    journal.add_entry(pending_entry)

    # Reload / recover
    recovered = journal.recover_interrupted_sessions()
    assert len(recovered) == 1
    assert recovered[0].id == pending_entry.id
    assert recovered[0].status == "recovered"


def test_history_journal_retention_policy(temp_journal_dir):
    journal_path = temp_journal_dir / "journal.json"
    journal = HistoryJournal(file_path=journal_path, retention_policy="7_days")

    # Add old entry (> 8 days ago)
    old_time = time.time() - (8 * 86400)
    old_entry = HistoryEntry(
        timestamp=old_time,
        raw_text="old speech from last week",
        cleaned_text="Old speech from last week.",
    )
    journal.add_entry(old_entry)

    # Add fresh entry (now)
    fresh_entry = HistoryEntry(
        timestamp=time.time(),
        raw_text="fresh speech today",
        cleaned_text="Fresh speech today.",
    )
    journal.add_entry(fresh_entry)

    assert len(journal.get_entries()) == 2
    purged = journal.apply_retention_policy()
    assert purged == 1
    assert len(journal.get_entries()) == 1
    assert journal.get_entries()[0].cleaned_text == "Fresh speech today."


def test_history_journal_export_markdown(temp_journal_dir):
    journal_path = temp_journal_dir / "journal.json"
    journal = HistoryJournal(file_path=journal_path, retention_policy="never")
    journal.record_dictation(
        raw_text="export testing raw text",
        cleaned_text="Export testing cleaned text.",
        cleanup_level="high",
        target_app="Notion",
    )

    out_file = temp_journal_dir / "export.md"
    generated_path = journal.export_to_markdown(output_path=out_file)
    assert generated_path.exists()
    content = generated_path.read_text(encoding="utf-8")
    assert "Transcription & Dictation History" in content
    assert "Export testing cleaned text." in content
    assert "Notion" in content


# =========================================================================
# 5. DETERMINISTIC INTENT PARSER TESTS (NEW DICTATION RULES)
# =========================================================================

def test_parser_cleanup_level_intents():
    parser = LocalRuleParser()

    res1 = parser.interpret("set cleanup level to light")
    assert res1 is not None
    assert res1.actions[0].action_type == ActionType.SYSTEM_ACTION
    assert res1.actions[0].system_action == "set_cleanup_level"
    assert res1.actions[0].target == "light"

    res2 = parser.interpret("cleanup high")
    assert res2 is not None
    assert res2.actions[0].system_action == "set_cleanup_level"
    assert res2.actions[0].target == "high"

    res3 = parser.interpret("raw dictation")
    assert res3 is not None
    assert res3.actions[0].system_action == "set_cleanup_level"
    assert res3.actions[0].target == "none"


def test_parser_language_switching_intents():
    parser = LocalRuleParser()

    res1 = parser.interpret("switch language to spanish")
    assert res1 is not None
    assert res1.actions[0].system_action == "set_language"
    assert res1.actions[0].target == "spanish"

    res2 = parser.interpret("dictate in hindi")
    assert res2 is not None
    assert res2.actions[0].system_action == "set_language"
    assert res2.actions[0].target == "hindi"

    res3 = parser.interpret("auto language")
    assert res3 is not None
    assert res3.actions[0].system_action == "set_language"
    assert res3.actions[0].target == "auto"


def test_parser_transform_intents():
    parser = LocalRuleParser()

    res1 = parser.interpret("polish this")
    assert res1 is not None
    assert res1.actions[0].system_action == "transform_selection"
    assert res1.actions[0].target == "polish"

    res2 = parser.interpret("prompt engineer selection")
    assert res2 is not None
    assert res2.actions[0].system_action == "transform_selection"
    assert res2.actions[0].target == "prompt_engineer"

    res3 = parser.interpret("fix grammar and tone")
    assert res3 is not None
    assert res3.actions[0].system_action == "transform_selection"
    assert res3.actions[0].target == "grammar"

    res4 = parser.interpret("make this executive")
    assert res4 is not None
    assert res4.actions[0].system_action == "transform_selection"
    assert res4.actions[0].target == "tone_executive"

    res5 = parser.interpret("bulletize this")
    assert res5 is not None
    assert res5.actions[0].system_action == "transform_selection"
    assert res5.actions[0].target == "bulletize"

    res6 = parser.interpret("open transforms")
    assert res6 is not None
    assert res6.actions[0].system_action == "open_transforms"


def test_parser_undo_dictation_intent():
    parser = LocalRuleParser()

    res1 = parser.interpret("undo dictation")
    assert res1 is not None
    assert res1.actions[0].system_action == "undo_dictation"

    res2 = parser.interpret("revert to raw dictation")
    assert res2 is not None
    assert res2.actions[0].system_action == "undo_dictation"

    res3 = parser.interpret("undo ai edit")
    assert res3 is not None
    assert res3.actions[0].system_action == "undo_dictation"


# =========================================================================
# 6. UI OVERLAYS SMOKE TEST (QT WIDGETS)
# =========================================================================

def test_wispr_flow_overlay_ui():
    from PySide6.QtWidgets import QApplication
    from handless.dictation.flow_overlay import WisprFlowOverlay

    app = QApplication.instance() or QApplication([])
    overlay = WisprFlowOverlay()
    assert overlay.isVisible() is False

    # Check pills
    overlay.set_language_code("es")
    assert "ES" in overlay.lang_pill.text()

    overlay.set_cleanup_level("high")
    assert "Exec" in overlay.cleanup_pill.text()

    # Test flow state changes
    overlay.start_flow()
    assert overlay.isVisible() is True
    overlay.transcribing_flow()
    assert overlay._state == "transcribing"
    overlay.finish_flow("Cleaned text output", show_undo=True)
    assert overlay._state == "done"
    assert overlay.undo_btn.isVisible() is True
    overlay.cancel_flow()
    assert overlay._state == "idle"
