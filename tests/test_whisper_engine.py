"""Unit tests for WhisperSpeechRecognizer using sherpa-onnx Whisper Base."""

import wave
from pathlib import Path
import pytest
from handless.voice.whisper_engine import WhisperSpeechRecognizer


def test_whisper_engine_initialization():
    rec = WhisperSpeechRecognizer(auto_download=False)
    assert rec.is_ready is True


def test_whisper_engine_decode_test_wav():
    rec = WhisperSpeechRecognizer(auto_download=False)
    assert rec.is_ready is True

    test_wav = Path("models/sherpa-onnx-whisper-base.en/test_wavs/0.wav")
    if not test_wav.exists():
        pytest.skip("Test wav file missing")

    with wave.open(str(test_wav)) as wf:
        data = wf.readframes(wf.getnframes())

    rec.reset()
    partial, final = rec.process_chunk(data)
    result = rec.finalize_speech()

    assert result is not None
    assert len(result) > 10
    # Whisper should recognize the content about lamps/yellow lamps
    assert "lamps" in result.lower() or "nightfall" in result.lower()


def test_whisper_engine_clean_text():
    assert WhisperSpeechRecognizer._clean_whisper_text("<|startoftranscript|> Hello World. ") == "Hello World"
    assert WhisperSpeechRecognizer._clean_whisper_text("Open Chrome.") == "Open Chrome"
