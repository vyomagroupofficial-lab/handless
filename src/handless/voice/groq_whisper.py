"""Groq Cloud Speech Recognizer using OpenAI Whisper Large v3.

Delivers state-of-the-art speech-to-text accuracy and ultra-low latency (<300ms)
via Groq's LPU-accelerated Whisper Cloud API (whisper-large-v3).
"""

from __future__ import annotations

import io
import logging
import math
import re
import struct
import wave
from typing import Optional, Tuple

import httpx

from handless.security.credentials import get_groq_api_key

logger = logging.getLogger(__name__)

GROQ_TRANSCRIPTION_URL = "https://api.groq.com/openai/v1/audio/transcriptions"
DEFAULT_GROQ_WHISPER_MODEL = "whisper-large-v3"
MIN_AUDIO_DURATION_SEC = 0.25  # Minimum speech duration to transcribe
MIN_AUDIO_RMS = 45.0  # Silence threshold below which audio is discarded as background noise


class GroqWhisperRecognizer:
    """Ultra-low latency speech recognizer powered by Groq's whisper-large-v3 API."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_GROQ_WHISPER_MODEL,
        sample_rate: int = 16000,
        timeout: float = 6.0,
        language: Optional[str] = None,
    ) -> None:
        self._explicit_key = api_key
        self.model = model
        self.sample_rate = sample_rate
        self.timeout = timeout
        self.language = language or "en"
        self._audio_buffer = bytearray()
        self._has_speech = False
        self._last_partial_len = 0
        self._client: Optional[httpx.Client] = None
        self._request_history: list[float] = []

    def set_language(self, language: Optional[str]) -> None:
        """Set active spoken language code (e.g. 'en', 'hi', 'es', 'fr', 'auto')."""
        self.language = language or "en"
        logger.info("GroqWhisperRecognizer: Language set to '%s'", self.language)

    def _get_api_key(self) -> Optional[str]:
        if self._explicit_key and self._explicit_key.strip():
            return self._explicit_key.strip()
        return get_groq_api_key()

    @property
    def is_ready(self) -> bool:
        """Check if Groq API key is configured."""
        key = self._get_api_key()
        return bool(key and len(key) > 5)

    def reset(self) -> None:
        """Clear the audio buffer and speech tracking."""
        self._audio_buffer.clear()
        self._has_speech = False
        self._last_partial_len = 0

    def process_chunk(self, audio_data: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Accumulate incoming audio chunks from microphone pipeline.

        Returns:
            (partial_text, final_text) tuple.
        """
        if not audio_data:
            return None, None

        self._audio_buffer.extend(audio_data)

        # Calculate energy to detect real speech
        rms = self._calculate_rms(audio_data)
        if rms >= MIN_AUDIO_RMS:
            self._has_speech = True

        partial = None
        # Provide visual feedback every ~0.5s of speech
        if self._has_speech and len(self._audio_buffer) - self._last_partial_len >= (self.sample_rate * 2 * 0.5):
            self._last_partial_len = len(self._audio_buffer)
            duration_sec = len(self._audio_buffer) / (self.sample_rate * 2)
            dots = "." * (int(duration_sec * 2) % 4 + 1)
            partial = f"Listening{dots}"

        return partial, None

    def get_final_result(self) -> Optional[str]:
        """Alias for finalize_speech."""
        return self.finalize_speech()

    def finalize_speech(self) -> Optional[str]:
        """Package buffered audio as WAV and transcribe via Groq Whisper Large v3."""
        if not self._audio_buffer:
            self.reset()
            return None

        # Check minimum duration (bytes = duration * sample_rate * 2 bytes/sample)
        min_bytes = int(MIN_AUDIO_DURATION_SEC * self.sample_rate * 2)
        if len(self._audio_buffer) < min_bytes or not self._has_speech:
            logger.debug("Discarding short/silent audio chunk (%d bytes)", len(self._audio_buffer))
            self.reset()
            return None

        # Check overall buffer energy
        overall_rms = self._calculate_rms(bytes(self._audio_buffer))
        if overall_rms < MIN_AUDIO_RMS:
            logger.debug("Discarding audio chunk below noise threshold (RMS=%.1f)", overall_rms)
            self.reset()
            return None

        api_key = self._get_api_key()
        if not api_key:
            logger.warning("Cannot transcribe with Groq Whisper: No Groq API key found.")
            self.reset()
            return None

        # Build in-memory 16kHz mono 16-bit PCM WAV
        wav_bytes = self._encode_wav(bytes(self._audio_buffer))
        self.reset()

        # Send to Groq Whisper API (primary priority)
        return self._transcribe_wav(wav_bytes, api_key, is_speculative=False)

    def transcribe_pcm(
        self,
        pcm_bytes: bytes,
        language: Optional[str] = None,
        is_speculative: bool = False,
    ) -> Optional[str]:
        """Directly transcribe raw 16kHz mono 16-bit PCM audio bytes."""
        if not pcm_bytes:
            return None
        api_key = self._get_api_key()
        if not api_key:
            logger.warning("Cannot transcribe with Groq Whisper: No Groq API key found.")
            return None
        wav_bytes = self._encode_wav(pcm_bytes)
        return self._transcribe_wav(wav_bytes, api_key, language=language, is_speculative=is_speculative)

    def _encode_wav(self, pcm_bytes: bytes) -> bytes:

        """Encode raw PCM bytes into a standard WAV byte stream in memory."""
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(self.sample_rate)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()

    def _check_rpm_budget(self, is_speculative: bool) -> bool:
        """Check rolling 60-second request rate against Groq 20 RPM on-demand tier."""
        import time as _t
        now = _t.monotonic()
        # Evict timestamps older than 60s
        self._request_history = [t for t in self._request_history if (now - t) < 60.0]

        # If speculative and 12+ requests fired in the last minute, preserve quota for finalization
        if is_speculative and len(self._request_history) >= 12:
            logger.debug(
                "Groq Whisper RPM budget threshold reached (%d reqs in last 60s). Skipping speculative chunk to protect primary dictation quota.",
                len(self._request_history),
            )
            return False
        return True

    def _transcribe_wav(
        self,
        wav_bytes: bytes,
        api_key: str,
        language: Optional[str] = None,
        is_speculative: bool = False,
    ) -> Optional[str]:
        """Perform HTTP POST multipart upload to Groq Whisper API with retry on 429."""
        if not self._check_rpm_budget(is_speculative):
            return None

        headers = {
            "Authorization": f"Bearer {api_key}",
            "User-Agent": "VyomaHandless/1.0",
        }
        files = {
            "file": ("speech.wav", wav_bytes, "audio/wav"),
        }
        data = {
            "model": self.model,
            "response_format": "json",
            "temperature": "0.0",
        }
        target_lang = language or self.language
        if target_lang and target_lang.lower() != "auto":
            data["language"] = target_lang.lower()

        try:
            import time as _t
            self._request_history.append(_t.monotonic())

            client = self._get_client()
            response = client.post(
                GROQ_TRANSCRIPTION_URL,
                headers=headers,
                files=files,
                data=data,
                timeout=self.timeout,
            )

            if response.status_code == 200:
                result_json = response.json()
                raw_text = result_json.get("text", "")
                cleaned = self._clean_whisper_text(raw_text)
                if cleaned:
                    logger.info("Groq Whisper STT recognized (%s): '%s'", self.model, cleaned)
                    return cleaned
                return None
            elif response.status_code == 429:
                retry_after_val = 2.5
                try:
                    retry_header = response.headers.get("retry-after")
                    if retry_header:
                        retry_after_val = float(retry_header)
                except Exception:
                    pass
                retry_after_val = max(1.0, min(retry_after_val, 3.5))

                if not is_speculative:
                    logger.warning(
                        "Groq Whisper rate limit encountered (429). Retrying primary transcription in %.1fs...",
                        retry_after_val,
                    )
                    _t.sleep(retry_after_val)
                    try:
                        self._request_history.append(_t.monotonic())
                        retry_resp = client.post(
                            GROQ_TRANSCRIPTION_URL,
                            headers=headers,
                            files=files,
                            data=data,
                            timeout=self.timeout,
                        )
                        if retry_resp.status_code == 200:
                            raw_text = retry_resp.json().get("text", "")
                            cleaned = self._clean_whisper_text(raw_text)
                            if cleaned:
                                logger.info("Groq Whisper STT recognized on retry (%s): '%s'", self.model, cleaned)
                                return cleaned
                    except Exception as r_exc:
                        logger.error("Groq Whisper retry failed: %s", r_exc)

                logger.warning(
                    "Groq Whisper transcription rate limited (status 429, speculative=%s): %s",
                    is_speculative,
                    response.text,
                )
                return None
            else:
                logger.error(
                    "Groq Whisper transcription failed (status %d): %s",
                    response.status_code,
                    response.text,
                )
                return None
        except httpx.TimeoutException:
            logger.warning("Groq Whisper transcription timed out after %.1fs", self.timeout)
            return None
        except Exception as exc:
            logger.error("Error calling Groq Whisper API: %s", exc)
            return None

    def _get_client(self) -> httpx.Client:
        if self._client is None or self._client.is_closed:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    @staticmethod
    def _calculate_rms(pcm_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) volume of 16-bit PCM bytes."""
        if not pcm_bytes:
            return 0.0
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
        format_str = f"<{count}h"
        try:
            shorts = struct.unpack(format_str, pcm_bytes[: count * 2])
            sum_squares = sum(s * s for s in shorts)
            return math.sqrt(sum_squares / count)
        except Exception:
            return 0.0

    @staticmethod
    def _clean_whisper_text(raw_text: str) -> str:
        """Clean Whisper output by removing timestamps, repetitive hallucination tokens, and trailing periods."""
        if not raw_text:
            return ""
        # Remove prompt or timestamp tokens
        cleaned = re.sub(r"<\|.*?\|>", "", raw_text).strip()
        # Discard single punctuation or whitespace
        if cleaned in (".", ",", "?", "!", "-", "--", "you", "thank you", "thank you."):
            return ""
        # Clean terminal periods/commas while preserving text
        cleaned = re.sub(r"[\.,!?]+$", "", cleaned).strip()
        return cleaned

