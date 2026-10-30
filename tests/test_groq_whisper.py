"""Unit tests for Groq Whisper Cloud Speech Recognizer."""

import io
import wave
from unittest.mock import MagicMock, patch
import pytest

from handless.voice.groq_whisper import (
    DEFAULT_GROQ_WHISPER_MODEL,
    GroqWhisperRecognizer,
)


@pytest.fixture
def recognizer():
    return GroqWhisperRecognizer(api_key="mock_groq_key_12345")


def test_recognizer_init_and_ready(recognizer):
    assert recognizer.is_ready is True
    assert recognizer.model == DEFAULT_GROQ_WHISPER_MODEL
    assert recognizer.sample_rate == 16000


def test_recognizer_not_ready_without_key():
    with patch("handless.voice.groq_whisper.get_groq_api_key", return_value=None):
        r = GroqWhisperRecognizer(api_key=None)
        assert r.is_ready is False


def test_discard_short_audio(recognizer):
    # Only 100 bytes (far below 0.25s / 8000 bytes)
    recognizer.process_chunk(b"\x10\x00" * 50)
    result = recognizer.finalize_speech()
    assert result is None


def test_discard_silence(recognizer):
    # 0.5s of absolute silence (RMS = 0)
    recognizer.process_chunk(b"\x00\x00" * 8000)
    result = recognizer.finalize_speech()
    assert result is None


def test_clean_whisper_text():
    assert GroqWhisperRecognizer._clean_whisper_text("<|transcribe|> Hello world... ") == "Hello world"
    assert GroqWhisperRecognizer._clean_whisper_text("thank you.") == ""
    assert GroqWhisperRecognizer._clean_whisper_text(".") == ""
    assert GroqWhisperRecognizer._clean_whisper_text("open chrome") == "open chrome"


def test_successful_transcription(recognizer):
    # Create ~0.5s of simulated audio with sufficient amplitude
    pcm = (b"\x50\x20\xa0\xd0" * 2000)
    recognizer.process_chunk(pcm)

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {"text": "open chrome browser."}

    with patch.object(recognizer, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        text = recognizer.finalize_speech()
        assert text == "open chrome browser"


def test_transcription_http_error(recognizer):
    pcm = (b"\x50\x20\xa0\xd0" * 2000)
    recognizer.process_chunk(pcm)

    mock_resp = MagicMock()
    mock_resp.status_code = 500
    mock_resp.text = "Internal Server Error"

    with patch.object(recognizer, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.post.return_value = mock_resp
        mock_get_client.return_value = mock_client

        text = recognizer.finalize_speech()
        assert text is None


def test_transcription_rate_limit_retry_succeeds(recognizer):
    """When Groq Whisper returns HTTP 429, primary transcription retries and succeeds."""
    pcm = (b"\x50\x20\xa0\xd0" * 2000)
    recognizer.process_chunk(pcm)

    resp_429 = MagicMock()
    resp_429.status_code = 429
    resp_429.headers = {"retry-after": "0.01"}
    resp_429.text = "Rate limit reached"

    resp_200 = MagicMock()
    resp_200.status_code = 200
    resp_200.json.return_value = {"text": "recovered message"}

    with patch.object(recognizer, "_get_client") as mock_get_client, \
         patch("time.sleep") as mock_sleep:
        mock_client = MagicMock()
        mock_client.post.side_effect = [resp_429, resp_200]
        mock_get_client.return_value = mock_client

        text = recognizer.finalize_speech()
        assert text == "recovered message"
        assert mock_client.post.call_count == 2
        mock_sleep.assert_called_once()


def test_speculative_budget_skips_when_quota_low(recognizer):
    """Speculative chunks are skipped when request rate is high, preserving quota for final speech."""
    import time as _t
    now = _t.monotonic()
    # Simulate 13 requests in the last 60 seconds
    recognizer._request_history = [now - i for i in range(13)]

    with patch.object(recognizer, "_get_client") as mock_get_client:
        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        # Speculative request must be throttled without calling network
        result = recognizer.transcribe_pcm(b"\x50\x20" * 4000, is_speculative=True)
        assert result is None
        mock_client.post.assert_not_called()


