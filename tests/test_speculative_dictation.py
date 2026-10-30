"""Unit and integration tests for Speculative Pre-Transcribe Engine.

Verifies:
1. Sub-100ms perceived text turnaround through background sliding-window chunk transcription.
2. Speculative chunk caching and hit rate tracking.
3. Fallback direct transcription for short speech bursts (<1.2s).
4. Audio chunk feeding and buffer lifecycle.
5. Smart text stitching and auto cleanup level propagation.
"""

from __future__ import annotations

import time
from unittest.mock import MagicMock

import pytest

from handless.dictation.cleanup_engine import CleanupLevel
from handless.dictation.speculative_engine import (
    MIN_SPECULATIVE_WINDOW_BYTES,
    MIN_TAIL_BYTES,
    SpeculativeDictationEngine,
    SpeculativeResult,
    SpeculativeSession,
)


class DummyMockRecognizer:
    """Mock STT Recognizer that simulates Groq Whisper with configurable latency."""

    def __init__(self, latency_sec: float = 0.05, text_prefix: str = "chunk") -> None:
        self.latency_sec = latency_sec
        self.text_prefix = text_prefix
        self.call_count = 0

    def transcribe_pcm(self, pcm_bytes: bytes, language: str = "en") -> str:
        self.call_count += 1
        if self.latency_sec > 0:
            time.sleep(self.latency_sec)
        return f"{self.text_prefix}_{self.call_count}"


def generate_dummy_pcm(duration_sec: float, sample_rate: int = 16000, amplitude: int = 2000) -> bytes:
    """Generate dummy 16-bit 16kHz mono PCM bytes with non-zero energy."""
    import struct
    total_samples = int(duration_sec * sample_rate)
    # Sine-like / alternating waveform
    samples = [(amplitude if i % 2 == 0 else -amplitude) for i in range(total_samples)]
    return struct.pack(f"{total_samples}h", *samples)


def test_speculative_empty_session():
    """Finalizing an empty session without audio should return cleanly with 0 hits."""
    engine = SpeculativeDictationEngine(recognizer=DummyMockRecognizer())
    engine.start_session(language="en")
    result = engine.finalize_session()

    assert isinstance(result, SpeculativeResult)
    assert result.text == ""
    assert result.raw_text == ""
    assert result.speculative_chunks_total == 0
    assert result.speculative_hits == 0


def test_speculative_short_utterance():
    """Audio shorter than 1.2s uses direct transcribe without pre-speculative chunking."""
    mock_rec = DummyMockRecognizer(latency_sec=0.01, text_prefix="short_speech")
    engine = SpeculativeDictationEngine(recognizer=mock_rec)
    session = engine.start_session(language="en", cleanup_level=CleanupLevel.NONE)

    # 0.5s of audio (16,000 bytes) < MIN_SPECULATIVE_WINDOW_BYTES (38,400 bytes)
    chunk = generate_dummy_pcm(0.5)
    engine.feed_chunk(chunk)

    result = engine.finalize_session()
    assert result.text == "short_speech_1"
    assert result.speculative_chunks_total == 0
    assert mock_rec.call_count == 1


def test_speculative_streaming_hits_and_sub_100ms_latency():
    """Streaming audio > 1.2s triggers speculative pre-transcription in background,
    resulting in cache hits and sub-100ms finalization latency."""
    # Whisper responds in 30ms on Groq LPUs
    mock_rec = DummyMockRecognizer(latency_sec=0.03, text_prefix="word")
    engine = SpeculativeDictationEngine(recognizer=mock_rec, max_workers=2)
    session = engine.start_session(language="en", cleanup_level=CleanupLevel.NONE)

    # Feed 8 chunks of 200ms audio (1.6s total > 1.2s threshold)
    chunk_200ms = generate_dummy_pcm(0.2)
    for _ in range(8):
        engine.feed_chunk(chunk_200ms)
        time.sleep(0.01)  # small streaming interval

    # Simulate speaking pause while pre-transcription runs in background
    time.sleep(0.08)

    # User releases key -> Finalize should be instantaneous (<100ms)
    t0 = time.perf_counter()
    result = engine.finalize_session()
    finalize_time_ms = (time.perf_counter() - t0) * 1000.0

    assert finalize_time_ms < 100.0, f"Finalize took {finalize_time_ms}ms, expected < 100ms"
    assert result.speculative_chunks_total >= 1
    assert result.speculative_hits >= 1
    assert "word" in result.text


def test_speculative_stitching():
    """Smart stitcher correctly joins chunk parts without duplicate whitespace."""
    parts = ["Hello world,", "how are you today?", "I hope all is well."]
    stitched = SpeculativeSession._stitch_parts(parts)
    assert stitched == "Hello world, how are you today? I hope all is well."

    assert SpeculativeSession._stitch_parts([]) == ""
    assert SpeculativeSession._stitch_parts(["Solo"]) == "Solo"


def test_speculative_cleanup_levels():
    """Auto cleanup levels are respected during speculative output assembly."""
    mock_rec = DummyMockRecognizer(latency_sec=0.0, text_prefix="um like you know test")
    engine = SpeculativeDictationEngine(recognizer=mock_rec)

    # Level None preserves raw text
    engine.start_session(language="en", cleanup_level=CleanupLevel.NONE)
    engine.feed_chunk(generate_dummy_pcm(0.4))
    res_none = engine.finalize_session()
    assert "um like" in res_none.text.lower()

    # Level Light cleans fillers
    engine.start_session(language="en", cleanup_level=CleanupLevel.LIGHT)
    engine.feed_chunk(generate_dummy_pcm(0.4))
    res_light = engine.finalize_session()
    assert "um" not in res_light.text.lower().split()


def test_speculative_engine_session_reset():
    """Subsequent finalizes on already completed session return empty safely."""
    engine = SpeculativeDictationEngine(recognizer=DummyMockRecognizer())
    engine.start_session()
    engine.feed_chunk(generate_dummy_pcm(0.3))
    r1 = engine.finalize_session()
    assert r1 is not None

    # Immediate second finalize
    r2 = engine.finalize_session()
    assert r2.text == ""
    assert r2.speculative_chunks_total == 0


def test_speculative_max_chunks_budget_cap():
    """Streaming long continuous audio never exceeds MAX_SPECULATIVE_CHUNKS (2), protecting RPM quota."""
    mock_rec = DummyMockRecognizer(latency_sec=0.01, text_prefix="long")
    engine = SpeculativeDictationEngine(recognizer=mock_rec)
    session = engine.start_session(language="en", cleanup_level=CleanupLevel.NONE)

    # Feed 20 seconds of audio (100 chunks of 200ms)
    chunk_200ms = generate_dummy_pcm(0.2)
    for _ in range(30):
        engine.feed_chunk(chunk_200ms)
        time.sleep(0.01)

    # Even after 6 seconds of speech, chunk counter must not exceed 2
    assert session._chunk_counter <= 2
    res = engine.finalize_session()
    assert res.speculative_chunks_total <= 3  # at most 2 chunks + 1 tail
    assert "long" in res.text


def test_speculative_rate_limit_recovery():
    """If speculative pre-transcription fails (e.g. 429), it disables further speculative calls
    and recovers via direct full-buffer transcription during finalization."""
    call_modes = []

    class RateLimitedRecognizer:
        def transcribe_pcm(self, pcm_bytes: bytes, language: str = "en", is_speculative: bool = False) -> str:
            call_modes.append(is_speculative)
            if is_speculative:
                # Speculative request fails with 429
                return ""
            # Primary direct fallback succeeds
            return "recovered voice command"

    engine = SpeculativeDictationEngine(recognizer=RateLimitedRecognizer())
    engine.start_session(language="en", cleanup_level=CleanupLevel.NONE)

    # Feed enough audio for a speculative window
    for _ in range(8):
        engine.feed_chunk(generate_dummy_pcm(0.2))

    res = engine.finalize_session()
    assert res.text == "recovered voice command"
    assert True in call_modes  # Speculative was attempted
    assert False in call_modes  # Primary direct fallback was executed and succeeded


