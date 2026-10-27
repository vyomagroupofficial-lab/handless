import pytest
from pathlib import Path
from handless.voice.recognizer import VoskSpeechRecognizer


def test_vosk_model_loaded():
    model_path = Path("models/vosk-model-small-en-us-0.15")
    assert model_path.exists(), "Model path must exist"

    recognizer = VoskSpeechRecognizer(model_path=str(model_path), auto_download=False)
    assert recognizer.is_ready is True
    assert recognizer.model is not None
    assert recognizer.recognizer is not None

    # Test feeding empty or silence buffer
    silence = bytes(640)
    partial, final = recognizer.process_chunk(silence)
    # Processing silence shouldn't crash
    recognizer.reset()
