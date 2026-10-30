"""Unit tests for Stereo Diarization (hardware isolated mic + loopback) and real-time commitment detection.
"""

import time
import struct
from unittest.mock import MagicMock
import pytest
from PySide6.QtWidgets import QApplication

from handless.meeting.commitment_detector import CommitmentDetector
from handless.meeting.mic_capture import MicChannelCapture
from handless.meeting.models import ActionItem, MeetingSession, TranscriptTurn
from handless.meeting.transcription_engine import MeetingTranscriber


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


# ---------------------------------------------------------------------------
# 1. CommitmentDetector Tests
# ---------------------------------------------------------------------------

def test_commitment_detector_first_person():
    text = "I will fix the payment gateway bug by tomorrow at 5 PM."
    items = CommitmentDetector.extract_commitments_from_text(text, speaker="You")
    assert len(items) == 1
    assert items[0].assignee == "You"
    assert "fix the payment gateway bug" in items[0].task.lower()
    assert items[0].due_date is not None
    assert "tomorrow" in items[0].due_date.lower()


def test_commitment_detector_delegated_request():
    text = "Please send the client report before Friday."
    items = CommitmentDetector.extract_commitments_from_text(text, speaker="Speaker 1")
    assert len(items) == 1
    assert "send the client report" in items[0].task.lower()
    assert items[0].due_date is not None
    assert "friday" in items[0].due_date.lower()


def test_commitment_detector_collective_agreement():
    text = "We should deploy the new microservices by next week."
    items = CommitmentDetector.extract_commitments_from_text(text, speaker="Speaker 2")
    assert len(items) == 1
    assert items[0].assignee == "All"
    assert "deploy the new microservices" in items[0].task.lower()
    assert items[0].due_date is not None
    assert "next week" in items[0].due_date.lower()


def test_commitment_detector_ignores_chitchat():
    text = "Yeah that sounds like a great movie, I loved watching it last night."
    items = CommitmentDetector.extract_commitments_from_text(text, speaker="Speaker 1")
    assert len(items) == 0


def test_commitment_detector_from_turn():
    turn = TranscriptTurn(
        id="t_001",
        speaker="You",
        text="I'll prepare the slide deck by Thursday morning.",
        timestamp=time.time(),
        is_user=True,
    )
    items = CommitmentDetector.extract_from_turn(turn)
    assert len(items) == 1
    assert items[0].assignee == "You"
    assert "prepare the slide deck" in items[0].task.lower()


# ---------------------------------------------------------------------------
# 2. MicChannelCapture Tests
# ---------------------------------------------------------------------------

def test_mic_channel_capture_rms():
    # 320 samples of 16-bit PCM = 640 bytes (20ms at 16kHz)
    pcm = struct.pack("320h", *([1000] * 320))
    rms = MicChannelCapture._calculate_rms(pcm)
    assert 0.0 < rms <= 1.0

    silent = struct.pack("320h", *([0] * 320))
    assert MicChannelCapture._calculate_rms(silent) == 0.0


def test_mic_channel_capture_lifecycle():
    capture = MicChannelCapture()
    assert not capture.is_running
    # Start and stop safely
    capture.start()
    assert capture.is_running is True
    capture.stop()
    assert capture.is_running is False


# ---------------------------------------------------------------------------
# 3. Stereo Diarization & Channel Isolation in MeetingTranscriber
# ---------------------------------------------------------------------------

def test_stereo_diarization_channel_isolation(qapp):
    mock_recognizer = MagicMock()
    mock_recognizer.transcribe_pcm.side_effect = lambda b: b.decode("utf-8", errors="ignore")

    engine = MeetingTranscriber(stt_recognizer=mock_recognizer)
    session = engine.start_recording(custom_title="Stereo Call")
    assert engine.is_recording is True

    detected_commitments = []
    engine.action_item_detected.connect(lambda item: detected_commitments.append(item))

    turns = []
    engine.turn_added.connect(lambda t: turns.append(t))

    # Simulate speech on Microphone channel ("You")
    engine._on_mic_speech_segment(b"I will update the billing documentation by Friday.")
    # Simulate speech on System loopback channel ("Remote Participants")
    engine._on_system_speech_segment(b"Please check the server memory usage today.")

    # Allow worker thread to process queue
    time.sleep(0.6)
    qapp.processEvents()

    engine.stop_recording()

    assert len(session.turns) >= 2
    assert len(turns) >= 2
    # Verify Channel 1: mic -> strictly "You", is_user=True
    mic_turns = [t for t in turns if t.source == "mic"]
    assert len(mic_turns) >= 1
    assert mic_turns[0].speaker == "You"
    assert mic_turns[0].is_user is True

    # Verify Channel 2: system -> strictly remote speaker, is_user=False
    sys_turns = [t for t in turns if t.source == "system"]
    assert len(sys_turns) >= 1
    assert sys_turns[0].speaker.startswith("Speaker")
    assert sys_turns[0].is_user is False

    # Verify real-time commitment detection
    assert len(detected_commitments) >= 1
    assert len(session.live_action_items) >= 1
