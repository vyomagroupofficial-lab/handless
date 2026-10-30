"""Unit tests for NVIDIA NeMo Parakeet Speech Recognizer."""

from __future__ import annotations

import wave
import array
from pathlib import Path
import pytest

from handless.voice.nvidia_parakeet import NvidiaParakeetRecognizer


def test_nvidia_parakeet_initialization():
    """Verify NVIDIA Parakeet recognizer instantiates and loads model."""
    rec = NvidiaParakeetRecognizer(auto_download=False)
    assert rec.is_ready is True
    assert rec.recognizer is not None


def test_nvidia_parakeet_transcription():
    """Verify transcription on sample test audio."""
    rec = NvidiaParakeetRecognizer(auto_download=False)
    test_wav = Path("models/sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8/test_wavs/0.wav")

    if not test_wav.exists():
        pytest.skip("Test wav not present")

    with wave.open(str(test_wav), "rb") as w:
        raw_bytes = w.readframes(w.getnframes())

    # Feed in chunks
    chunk_size = 3200
    for i in range(0, len(raw_bytes), chunk_size):
        rec.process_chunk(raw_bytes[i:i+chunk_size])

    final_text = rec.finalize_speech()
    assert final_text is not None
    assert len(final_text) > 0
    # Should accurately recognize sentence
    assert "Phoebe" in final_text or "wish to see" in final_text.lower()


def test_nvidia_parakeet_reset():
    """Verify reset clears internal state."""
    rec = NvidiaParakeetRecognizer(auto_download=False)
    rec._audio_buffer.extend(b"\x00" * 1000)
    assert len(rec._audio_buffer) == 1000
    rec.reset()
    assert len(rec._audio_buffer) == 0
