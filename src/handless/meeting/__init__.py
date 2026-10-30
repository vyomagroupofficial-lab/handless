"""Meeting and call transcription, diarization, and AI summarization package.
"""

from .active_app import detect_active_meeting_app
from .loopback_capture import SystemLoopbackCapture
from .models import ActionItem, MeetingSession, MeetingSummary, TranscriptTurn
from .storage import MeetingStorage
from .summarizer import MeetingSummarizer
from .transcription_engine import MeetingTranscriber

__all__ = [
    "detect_active_meeting_app",
    "SystemLoopbackCapture",
    "TranscriptTurn",
    "ActionItem",
    "MeetingSummary",
    "MeetingSession",
    "MeetingStorage",
    "MeetingSummarizer",
    "MeetingTranscriber",
]

