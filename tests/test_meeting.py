"""Comprehensive Unit & Integration Tests for Vyoma Handless Meeting & Call Transcripts.

Covers:
- Models (TranscriptTurn, MeetingSummary, MeetingSession, Wispr Flow highlights, Claude prompts)
- Active App Detection
- WASAPI Loopback Capture & Downsampling
- Meeting Storage & Search
- Meeting Summarizer
- Meeting Transcriber Engine (QObject signals & diarization)
- MeetingTranscriptsView Qt UI
- Local parser meeting commands
"""

import os
import shutil
import struct
import tempfile
import time
import pytest
from PySide6.QtWidgets import QApplication

from handless.intelligence.local_parser import LocalRuleParser
from handless.intelligence.models import ActionType
from handless.meeting.active_app import detect_active_meeting_app
from handless.meeting.loopback_capture import SystemLoopbackCapture
from handless.meeting.models import (
    ActionItem,
    MeetingSession,
    MeetingSummary,
    TranscriptTurn,
    apply_wispr_flow_highlights,
)
from handless.meeting.storage import MeetingStorage
from handless.meeting.summarizer import MeetingSummarizer
from handless.meeting.transcription_engine import MeetingTranscriber
from handless.ui.screens.meeting_view import (
    MeetingTranscriptsView,
    MiniEqualizerBar,
    TranscriptCard,
)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# 1. Models & Wispr Flow Highlights
# ---------------------------------------------------------------------------

def test_wispr_flow_highlights():
    text = "We need to finish project Alpha by tomorrow at 5 PM for $10,000 with 95% accuracy."
    html = apply_wispr_flow_highlights(text)

    # Must contain HTML bold
    assert "<b>" in html
    # Check that dollar amount and numbers are highlighted
    assert "<b>10,000</b>" in html
    assert "<b>95</b>" in html
    assert "<b>tomorrow</b>" in html


def test_transcript_turn_and_html():
    turn = TranscriptTurn(
        id="turn_1",
        speaker="You",
        text="Let's schedule a review on Friday with Sarah.",
        timestamp=time.time(),
        is_user=True,
        source="mic",
    )
    assert turn.is_user is True
    assert "<b>" in turn.highlighted_html
    assert "Friday" in turn.highlighted_html


def test_meeting_session_and_claude_prompt():
    session = MeetingSession(
        session_id="meet_123",
        title="Product Roadmap Call",
        app_name="Zoom",
        started_at=time.time() - 120,
        ended_at=time.time(),
    )
    turn1 = TranscriptTurn(
        id="t1",
        speaker="Speaker 1",
        text="We should launch the new feature next Monday.",
        timestamp=session.started_at + 10,
        is_user=False,
    )
    turn2 = TranscriptTurn(
        id="t2",
        speaker="You",
        text="Agreed, I will prepare the test suite by Thursday.",
        timestamp=session.started_at + 25,
        is_user=True,
    )
    session.turns.extend([turn1, turn2])

    clean_text = session.generate_clean_transcript_text()
    assert "Speaker 1:" in clean_text
    assert "You:" in clean_text
    assert "launch the new feature" in clean_text

    claude_prompt = session.generate_claude_prompt()
    assert "<meeting_transcript>" in claude_prompt
    assert "</meeting_transcript>" in claude_prompt
    assert "Zoom" in claude_prompt
    assert "Product Roadmap Call" in claude_prompt
    assert "Executive Summary" in claude_prompt
    assert "Action Items" in claude_prompt


# ---------------------------------------------------------------------------
# 2. Active App Detection
# ---------------------------------------------------------------------------

def test_active_meeting_app_detection():
    name, app_type, _ = detect_active_meeting_app()
    assert isinstance(name, str)
    assert isinstance(app_type, str)
    assert len(name) > 0


# ---------------------------------------------------------------------------
# 3. Audio Loopback Math & Resampling
# ---------------------------------------------------------------------------

def test_loopback_downsampling_math():
    capture = SystemLoopbackCapture()
    # Generate 48000 Hz 2-channel 16-bit PCM test buffer (960 stereo frames = 3840 bytes = 20ms)
    num_samples = 960 * 2
    raw_samples = [int(1000 * ((i % 100) / 100.0)) for i in range(num_samples)]
    raw_bytes = struct.pack(f"{num_samples}h", *raw_samples)

    # Downsample from 48kHz stereo to 16kHz mono
    pcm_16k = capture._resample_to_16k_mono(raw_bytes, channels=2, sample_rate=48000)
    # Output must be exactly 320 samples = 640 bytes (20ms at 16kHz mono)
    assert len(pcm_16k) == 640

    # Test RMS level calculation
    level = capture._calculate_rms(pcm_16k)
    assert 0.0 <= level <= 1.0


# ---------------------------------------------------------------------------
# 4. Storage & Persistence
# ---------------------------------------------------------------------------

def test_meeting_storage_crud():
    temp_dir = tempfile.mkdtemp(prefix="handless_test_meetings_")
    try:
        storage = MeetingStorage(storage_dir=temp_dir)
        session = MeetingSession(
            session_id="meet_test_001",
            title="Q3 Strategy Meeting",
            app_name="Google Meet",
            started_at=time.time() - 300,
            ended_at=time.time(),
        )
        session.turns.append(
            TranscriptTurn(
                id="t1",
                speaker="Speaker 1",
                text="The conversion rate increased by 22 percent.",
                timestamp=session.started_at + 15,
                is_user=False,
            )
        )
        session.turns.append(
            TranscriptTurn(
                id="t2",
                speaker="You",
                text="Great job team, let us deploy the new dashboard.",
                timestamp=session.started_at + 40,
                is_user=True,
            )
        )

        # Save session
        json_path, md_path = storage.save_session(session)
        assert os.path.exists(json_path)
        assert os.path.exists(md_path)

        # Load session
        loaded = storage.load_session("meet_test_001")
        assert loaded is not None
        assert loaded.title == "Q3 Strategy Meeting"
        assert loaded.app_name == "Google Meet"
        assert len(loaded.turns) == 2
        assert loaded.turns[0].speaker == "Speaker 1"
        assert loaded.turns[1].speaker == "You"

        # Search sessions
        results = storage.search_sessions("conversion rate")
        assert len(results) == 1
        assert results[0].session_id == "meet_test_001"

        # List sessions
        sessions_meta = storage.list_sessions()
        assert len(sessions_meta) == 1
        assert sessions_meta[0]["session_id"] == "meet_test_001"

        # Delete session
        deleted = storage.delete_session("meet_test_001")
        assert deleted is True
        assert storage.load_session("meet_test_001") is None
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# 5. Summarizer Fallback Logic
# ---------------------------------------------------------------------------

def test_meeting_summarizer_local_fallback():
    summarizer = MeetingSummarizer(gemini_client=None, groq_client=None)
    session = MeetingSession(
        session_id="meet_sum_test",
        title="Sync on Handless v2",
        app_name="Teams",
        started_at=time.time() - 600,
        ended_at=time.time(),
    )
    session.turns.append(
        TranscriptTurn(
            id="t1",
            speaker="Speaker 1",
            text="We need to finalize the UI layout before release.",
            timestamp=session.started_at + 10,
            is_user=False,
        )
    )
    session.turns.append(
        TranscriptTurn(
            id="t2",
            speaker="You",
            text="I will complete the unit tests and verify the sound levels.",
            timestamp=session.started_at + 30,
            is_user=True,
        )
    )

    summary = summarizer.summarize_session(session)
    assert summary is not None
    assert len(summary.executive_summary) > 0
    assert len(summary.markdown_full) > 0
    assert "Executive Summary" in summary.markdown_full
    assert "Action Items" in summary.markdown_full


# ---------------------------------------------------------------------------
# 6. MeetingTranscriber Engine
# ---------------------------------------------------------------------------

def test_meeting_transcriber_lifecycle():
    engine = MeetingTranscriber(stt_recognizer=None, gemini_client=None, groq_client=None)
    assert not engine.is_recording

    # Start recording
    session = engine.start_recording(custom_title="Test Unit Call")
    assert engine.is_recording is True
    assert session.title == "Test Unit Call"

    turns_received = []
    engine.turn_added.connect(lambda t: turns_received.append(t))

    # Add user speech ("You")
    engine.add_user_speech("Hello from the user microphone!")
    assert len(session.turns) == 1
    assert session.turns[0].speaker == "You"
    assert session.turns[0].is_user is True
    assert len(turns_received) == 1

    # Feed levels
    mic_levels = []
    engine.mic_level_changed.connect(lambda l: mic_levels.append(l))
    engine.feed_mic_level(0.75)
    assert len(mic_levels) > 0
    assert mic_levels[-1] == 0.75

    # Stop recording
    stopped_sess = engine.stop_recording()
    assert engine.is_recording is False
    assert stopped_sess is not None


# ---------------------------------------------------------------------------
# 7. UI Components (Qt)
# ---------------------------------------------------------------------------

def test_mini_equalizer_bar(qapp):
    eq = MiniEqualizerBar(color_hex="#10B981")
    eq.set_level(0.6)
    assert eq._level == 0.6
    eq.set_level(1.5)  # clamp to 1.0
    assert eq._level == 1.0


def test_transcript_card(qapp):
    turn = TranscriptTurn(
        id="t1",
        speaker="Speaker 1",
        text="Discussing budget: $50,000 allocated for marketing.",
        timestamp=time.time(),
        is_user=False,
    )
    card = TranscriptCard(turn)
    assert card.speaker_badge.text() == "Speaker 1"
    assert "50,000" in card.text_label.text()


def test_meeting_transcripts_view(qapp):
    engine = MeetingTranscriber(stt_recognizer=None, gemini_client=None, groq_client=None)
    view = MeetingTranscriptsView(transcriber=engine)

    # Check initial elements
    assert view.title_label.text() == "Call Transcripts & Notes"
    assert "General Call" in view.app_badge.text()
    assert "Record" in view.record_btn.text()

    # Start session
    engine.start_recording(custom_title="Sprint Planning")
    assert "Stop" in view.record_btn.text()

    # Add turns
    turn_user = TranscriptTurn(
        id="tu",
        speaker="You",
        text="I am ready to ship.",
        timestamp=time.time(),
        is_user=True,
    )
    turn_other = TranscriptTurn(
        id="to",
        speaker="Speaker 1",
        text="Looks solid to me.",
        timestamp=time.time(),
        is_user=False,
    )
    view.add_turn(turn_user)
    view.add_turn(turn_other)
    assert len(view._cards) == 2

    # Test Speaker filtering (using isHidden to avoid requiring parent window show)
    view._set_filter("you", view.btn_filter_you)
    assert not view._cards[0].isHidden()
    assert view._cards[1].isHidden()

    view._set_filter("speakers", view.btn_filter_speakers)
    assert view._cards[0].isHidden()
    assert not view._cards[1].isHidden()

    view._set_filter("all", view.btn_filter_all)
    assert not view._cards[0].isHidden()
    assert not view._cards[1].isHidden()

    # Test Search filter
    view._on_search_changed("ship")
    assert not view._cards[0].isHidden()
    assert view._cards[1].isHidden()

    # Stop recording
    engine.stop_recording()
    assert "Record" in view.record_btn.text()


# ---------------------------------------------------------------------------
# 8. Local Rule Parser Intents
# ---------------------------------------------------------------------------

def test_local_parser_meeting_commands():
    parser = LocalRuleParser()

    # Open meeting transcripts
    r = parser.interpret("transcribe meeting")
    assert r is not None
    assert r.actions[0].system_action == "sidebar_meeting"

    r = parser.interpret("transcribe call")
    assert r is not None
    assert r.actions[0].system_action == "sidebar_meeting"

    r = parser.interpret("show meeting notes")
    assert r is not None
    assert r.actions[0].system_action == "sidebar_meeting"

    # Start recording
    r = parser.interpret("start meeting recording")
    assert r is not None
    assert r.actions[0].system_action == "start_meeting_recording"

    r = parser.interpret("record zoom")
    assert r is not None
    assert r.actions[0].system_action == "start_meeting_recording"

    r = parser.interpret("record whatsapp call")
    assert r is not None
    assert r.actions[0].system_action == "start_meeting_recording"

    # Stop recording
    r = parser.interpret("stop meeting recording")
    assert r is not None
    assert r.actions[0].system_action == "stop_meeting_recording"

    r = parser.interpret("stop recording call")
    assert r is not None
    assert r.actions[0].system_action == "stop_meeting_recording"

    # Summarize meeting
    r = parser.interpret("summarize meeting")
    assert r is not None
    assert r.actions[0].system_action == "summarize_meeting"

    r = parser.interpret("generate meeting summary")
    assert r is not None
    assert r.actions[0].system_action == "summarize_meeting"
