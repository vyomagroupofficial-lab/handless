"""Dual-stream meeting transcription engine orchestrating mic and system audio.
"""

from __future__ import annotations

import logging
import queue
import threading
import time
import uuid
from typing import Any, Callable, Dict, List, Optional

from PySide6.QtCore import QObject, Signal

from .active_app import detect_active_meeting_app
from .commitment_detector import CommitmentDetector
from .loopback_capture import SystemLoopbackCapture
from .mic_capture import MicChannelCapture
from .models import ActionItem, MeetingSession, MeetingSummary, TranscriptTurn
from .storage import MeetingStorage
from .summarizer import MeetingSummarizer

logger = logging.getLogger(__name__)


class MeetingTranscriber(QObject):
    """Orchestrates dual-stream meeting audio recording, transcription, and diarization.

    - Stream 1: User microphone (labeled as 'You' with Handless emerald styling).
    - Stream 2: System loopback audio (labeled as 'Speaker 1' / 'Speaker 2' with indigo styling).
    """

    turn_added = Signal(object)              # TranscriptTurn
    action_item_detected = Signal(object)    # ActionItem (Real-time commitment detected)
    mic_level_changed = Signal(float)       # 0.0 to 1.0
    system_level_changed = Signal(float)    # 0.0 to 1.0
    recording_state_changed = Signal(bool)  # True if recording, False if stopped
    session_started = Signal(object)        # MeetingSession
    session_ended = Signal(object)          # MeetingSession
    summary_ready = Signal(object)          # MeetingSummary
    status_changed = Signal(str)            # Status text

    def __init__(
        self,
        stt_recognizer: Optional[Any] = None,
        gemini_client: Optional[Any] = None,
        groq_client: Optional[Any] = None,
        parent: Optional[QObject] = None,
    ) -> None:
        super().__init__(parent)
        self.recognizer = stt_recognizer
        self.summarizer = MeetingSummarizer(gemini_client=gemini_client, groq_client=groq_client)
        self.storage = MeetingStorage()

        self._is_recording = False
        self._current_session: Optional[MeetingSession] = None
        self._speaker_turn_counter = 1
        self._last_system_speaker_time = 0.0

        # Stream 1: User Microphone hardware capture ("You")
        self._mic_capture = MicChannelCapture(
            on_speech_segment=self._on_mic_speech_segment,
            on_audio_level=self._on_mic_audio_level,
        )

        # Stream 2: System Loopback hardware capture ("Remote Participants")
        self._loopback = SystemLoopbackCapture(
            on_speech_segment=self._on_system_speech_segment,
            on_audio_level=self._on_system_audio_level,
        )

        # Multi-worker queue for concurrent asynchronous speech recognition
        self._task_queue: queue.Queue = queue.Queue()
        self._worker_running = True
        self._worker_threads = []
        for _ in range(2):  # 2 concurrent workers for parallel mic & system streams
            t = threading.Thread(target=self._transcription_worker, daemon=True)
            t.start()
            self._worker_threads.append(t)

    @property
    def is_recording(self) -> bool:
        return self._is_recording

    @property
    def current_session(self) -> Optional[MeetingSession]:
        return self._current_session

    def start_recording(self, custom_title: Optional[str] = None) -> MeetingSession:
        """Start capturing and transcribing call audio from both mic and desktop speakers."""
        if self._is_recording:
            return self._current_session  # type: ignore

        app_name, _, _ = detect_active_meeting_app()
        date_str = time.strftime("%b %d, %I:%M %p")
        title = custom_title or f"{app_name} Call ({date_str})"
        session_id = f"meet_{int(time.time())}_{uuid.uuid4().hex[:6]}"

        session = MeetingSession(
            session_id=session_id,
            title=title,
            app_name=app_name,
            started_at=time.time(),
        )
        self._current_session = session
        self._is_recording = True
        self._speaker_turn_counter = 1

        # Start both physically isolated hardware capture streams concurrently
        self._loopback.start()
        self._mic_capture.start()

        self.recording_state_changed.emit(True)
        self.session_started.emit(session)
        self.status_changed.emit(f"Recording {app_name} (Stereo Diarization Active)...")
        logger.info("Meeting transcription started for '%s' (ID: %s)", title, session_id)
        return session

    def stop_recording(self) -> Optional[MeetingSession]:
        """Stop capturing and finalize the meeting transcript."""
        if not self._is_recording or not self._current_session:
            return None

        self._is_recording = False
        self._loopback.stop()
        self._mic_capture.stop()
        self._current_session.ended_at = time.time()

        # Save to disk
        self.storage.save_session(self._current_session)

        self.recording_state_changed.emit(False)
        self.mic_level_changed.emit(0.0)
        self.system_level_changed.emit(0.0)
        self.session_ended.emit(self._current_session)
        self.status_changed.emit("Call ended and saved.")
        logger.info("Meeting transcription stopped: %s", self._current_session.session_id)
        return self._current_session

    def add_user_speech(self, text: str) -> None:
        """Add speech transcribed from the user's primary microphone ('You')."""
        if not self._is_recording or not self._current_session:
            return
        if not text or not text.strip():
            return

        turn = TranscriptTurn(
            id=f"t_{uuid.uuid4().hex[:8]}",
            speaker="You",
            text=text.strip(),
            timestamp=time.time(),
            is_user=True,
            source="mic",
        )
        self._current_session.turns.append(turn)
        detected_actions = CommitmentDetector.extract_from_turn(turn)
        for action in detected_actions:
            self._current_session.live_action_items.append(action)
            self.action_item_detected.emit(action)
        self.turn_added.emit(turn)
        self.storage.save_session(self._current_session)

    def feed_mic_level(self, level: float) -> None:
        """Feed live microphone level from external pipeline."""
        if self._is_recording:
            self.mic_level_changed.emit(level)

    def generate_summary(self) -> Optional[MeetingSummary]:
        """Request AI summary generation for current session in a background thread."""
        if not self._current_session:
            return None

        sess = self._current_session
        self.status_changed.emit("Generating AI summary...")

        def _worker():
            try:
                summary = self.summarizer.summarize_session(sess)
                self.storage.save_session(sess)
                self.summary_ready.emit(summary)
                self.status_changed.emit("AI Summary ready ✓")
            except Exception as e:
                logger.error("Error generating meeting summary: %s", e)
                self.status_changed.emit(f"Summary error: {e}")

        threading.Thread(target=_worker, daemon=True).start()
        return None

    def _on_mic_audio_level(self, level: float) -> None:
        if self._is_recording:
            self.mic_level_changed.emit(level)

    def _on_mic_speech_segment(self, pcm_bytes: bytes) -> None:
        """Queue captured microphone audio speech segment for 'You' transcription."""
        if not self._is_recording:
            return
        self._task_queue.put(("mic", pcm_bytes, time.time()))

    def _on_system_audio_level(self, level: float) -> None:
        if self._is_recording:
            self.system_level_changed.emit(level)

    def _on_system_speech_segment(self, pcm_bytes: bytes) -> None:
        """Queue captured system audio speech segment for remote participant transcription."""
        if not self._is_recording:
            return
        self._task_queue.put(("system", pcm_bytes, time.time()))

    def _transcription_worker(self) -> None:
        """Worker thread converting speech PCM audio bytes into text via Whisper."""
        while self._worker_running:
            try:
                source, pcm_data, timestamp = self._task_queue.get(timeout=0.2)
            except queue.Empty:
                continue

            try:
                text = self._transcribe_pcm(pcm_data)
                if not text or not text.strip():
                    continue

                clean_text = text.strip()
                # Skip common Whisper hallucinations on low volume/silence
                if clean_text.lower() in ("thank you.", "thank you", "bye", "you", "thanks for watching.", "."):
                    if len(pcm_data) < 16000:
                        continue

                # Stereo Diarization: Strict hardware channel isolation
                if source == "mic":
                    speaker_tag = "You"
                    is_user = True
                else:
                    is_user = False
                    now = time.time()
                    if now - self._last_system_speaker_time > 10.0:
                        # Alternate speaker tag if there was a pause between remote statements
                        self._speaker_turn_counter = 2 if self._speaker_turn_counter == 1 else 1
                    speaker_tag = f"Speaker {self._speaker_turn_counter}"
                    self._last_system_speaker_time = now

                turn = TranscriptTurn(
                    id=f"t_{uuid.uuid4().hex[:8]}",
                    speaker=speaker_tag,
                    text=clean_text,
                    timestamp=timestamp,
                    is_user=is_user,
                    source=source,
                )

                if self._current_session:
                    self._current_session.turns.append(turn)

                    # Real-time Commitment & Action Item Detection
                    detected_actions = CommitmentDetector.extract_from_turn(turn)
                    for action in detected_actions:
                        self._current_session.live_action_items.append(action)
                        self.action_item_detected.emit(action)
                        logger.info("Real-time commitment detected: '%s' (Assignee: %s, Due: %s)", action.task, action.assignee, action.due_date)

                    self.turn_added.emit(turn)
                    self.storage.save_session(self._current_session)

            except Exception as exc:
                logger.error("Error in transcription worker: %s", exc)

    def _transcribe_pcm(self, pcm_bytes: bytes) -> str:
        """Transcribe 16kHz 16-bit mono PCM bytes via Groq Cloud Whisper or local Whisper."""
        if not self.recognizer:
            return ""

        # 1. Try Groq Whisper Recognizer
        if hasattr(self.recognizer, "transcribe_pcm"):
            try:
                res = self.recognizer.transcribe_pcm(pcm_bytes)
                if res:
                    return res
            except Exception as e:
                logger.debug("Groq transcribe_pcm failed: %s", e)

        if hasattr(self.recognizer, "transcribe_raw_pcm"):
            try:
                return self.recognizer.transcribe_raw_pcm(pcm_bytes)
            except Exception as e:
                logger.debug("Groq transcribe_raw_pcm failed: %s", e)

        # 2. Try processing via recognizer.process_chunk
        try:
            if hasattr(self.recognizer, "reset"):
                self.recognizer.reset()
            _, final = self.recognizer.process_chunk(pcm_bytes)
            if not final and hasattr(self.recognizer, "get_final_result"):
                final = self.recognizer.get_final_result()
            return final or ""
        except Exception as e:
            logger.debug("Recognizer process_chunk failed: %s", e)

        return ""
