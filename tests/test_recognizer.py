import pytest
from pathlib import Path
from handless.voice.recognizer import VoskSpeechRecognizer


def test_vosk_model_loaded():
    model_path = Path("models/vosk-model-small-en-us-0.15")
    if not model_path.exists():
        pytest.skip("Vosk model not downloaded (python scripts/download_vosk_model.py)")

    recognizer = VoskSpeechRecognizer(model_path=str(model_path), auto_download=False)
    assert recognizer.is_ready is True
    assert recognizer.model is not None
    assert recognizer.recognizer is not None

    # Test feeding empty or silence buffer
    silence = bytes(640)
    partial, final = recognizer.process_chunk(silence)
    # Processing silence shouldn't crash
    recognizer.reset()
