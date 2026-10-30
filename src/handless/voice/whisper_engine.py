"""Offline Speech Recognizer using OpenAI Whisper model.

Accelerated via ONNX Runtime & sherpa-onnx with int8 AVX2 vectorization,
delivering state-of-the-art English transcription accuracy (OpenAI Whisper Base English)
running 100% locally on CPU without GPU or cloud dependency.
"""

from __future__ import annotations

import array
import logging
import os
import re
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

DEFAULT_WHISPER_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-whisper-base.en.tar.bz2"
)
DEFAULT_WHISPER_DIR = "sherpa-onnx-whisper-base.en"


class WhisperSpeechRecognizer:
    """Offline speech recognizer powered by OpenAI Whisper via sherpa-onnx."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        num_threads: int = 4,
        auto_download: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.num_threads = num_threads
        self.model_dir = self._resolve_model_dir(model_path, auto_download)
        self.recognizer = None
        self._audio_buffer: bytearray = bytearray()
        self._last_partial_len = 0

        self._load_model()

    def _resolve_model_dir(self, model_path: Optional[str], auto_download: bool) -> Path:
        if model_path:
            p = Path(model_path)
            if p.is_dir():
                return p.resolve()

        # Check default paths
        p1 = Path("models") / DEFAULT_WHISPER_DIR
        if p1.is_dir():
            return p1.resolve()

        p2 = Path.home() / ".vyoma-handless" / "models" / DEFAULT_WHISPER_DIR
        if p2.is_dir():
            return p2.resolve()

        dest = Path("models") / DEFAULT_WHISPER_DIR
        if auto_download:
            self._download_model(dest.parent)
        return dest.resolve()

    def _download_model(self, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_folder = target_dir / DEFAULT_WHISPER_DIR
        if dest_folder.is_dir():
            return

        tar_path = target_dir / f"{DEFAULT_WHISPER_DIR}.tar.bz2"
        logger.info("Downloading OpenAI Whisper Base English model (~208MB)...")
        try:
            urllib.request.urlretrieve(DEFAULT_WHISPER_URL, tar_path)
            with tarfile.open(tar_path, "r:bz2") as tar:
                tar.extractall(target_dir)
            if tar_path.exists():
                tar_path.unlink()
            logger.info("Whisper Base model successfully installed to %s", dest_folder)
        except Exception as exc:
            logger.error("Failed to auto-download Whisper Base model: %s", exc)

    def _load_model(self) -> None:
        try:
            import sherpa_onnx

            encoder_file = self.model_dir / "base.en-encoder.int8.onnx"
            if not encoder_file.exists():
                encoder_file = self.model_dir / "base.en-encoder.onnx"
            if not encoder_file.exists():
                encoder_file = self.model_dir / "tiny.en-encoder.int8.onnx"

            decoder_file = self.model_dir / "base.en-decoder.int8.onnx"
            if not decoder_file.exists():
                decoder_file = self.model_dir / "base.en-decoder.onnx"
            if not decoder_file.exists():
                decoder_file = self.model_dir / "tiny.en-decoder.int8.onnx"

            tokens_file = self.model_dir / "base.en-tokens.txt"
            if not tokens_file.exists():
                tokens_file = self.model_dir / "tokens.txt"
            if not tokens_file.exists():
                tokens_file = self.model_dir / "tiny.en-tokens.txt"

            if not encoder_file.exists() or not decoder_file.exists() or not tokens_file.exists():
                logger.warning(
                    "Whisper model files missing in: %s (need encoder, decoder, tokens.txt)",
                    self.model_dir,
                )
                return

            logger.info(
                "Initializing OpenAI Whisper Base STT (int8, threads=%d)...", self.num_threads
            )
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_whisper(
                encoder=str(encoder_file),
                decoder=str(decoder_file),
                tokens=str(tokens_file),
                language="en",
                task="transcribe",
                num_threads=self.num_threads,
            )
            logger.info("OpenAI Whisper Base STT engine initialized successfully.")
        except Exception as exc:
            logger.error("Failed to load OpenAI Whisper Base engine: %s", exc)
            self.recognizer = None

    def reset(self) -> None:
        """Reset internal buffer state."""
        self._audio_buffer.clear()
        self._last_partial_len = 0

    def process_chunk(self, audio_data: bytes) -> Tuple[Optional[str], Optional[str]]:
        """Feed audio chunk into recognizer.

        Returns:
            (partial_text, final_text) tuple.
        """
        if not self.recognizer or not audio_data:
            return None, None

        self._audio_buffer.extend(audio_data)

        # Process every ~0.6s of audio (16,000 samples/sec * 2 bytes/sample * 0.6s = 19,200 bytes)
        # to generate live partial feedback in VoiceBar
        partial = None
        final = None

        chunk_threshold = 19200
        if len(self._audio_buffer) >= chunk_threshold and (len(self._audio_buffer) - self._last_partial_len) >= chunk_threshold:
            self._last_partial_len = len(self._audio_buffer)
            try:
                raw_samples = array.array("h", self._audio_buffer)
                float_samples = [x / 32768.0 for x in raw_samples]

                stream = self.recognizer.create_stream()
                stream.accept_waveform(self.sample_rate, float_samples)
                self.recognizer.decode_stream(stream)
                text = self._clean_whisper_text(stream.result.text)
                if text:
                    partial = text
            except Exception as exc:
                logger.debug("Whisper partial decoding error: %s", exc)

        return partial, final

    @property
    def is_ready(self) -> bool:
        """Check if model engine is loaded and ready."""
        return self.recognizer is not None

    def get_final_result(self) -> Optional[str]:
        """Alias for finalize_speech to maintain compatibility."""
        return self.finalize_speech()

    def finalize_speech(self) -> Optional[str]:
        """Decode complete accumulated speech buffer and return final recognized text."""
        if not self.recognizer or not self._audio_buffer:
            return None

        try:
            raw_samples = array.array("h", self._audio_buffer)
            float_samples = [x / 32768.0 for x in raw_samples]

            stream = self.recognizer.create_stream()
            stream.accept_waveform(self.sample_rate, float_samples)
            self.recognizer.decode_stream(stream)
            final_text = self._clean_whisper_text(stream.result.text)

            self.reset()
            return final_text if final_text else None
        except Exception as exc:
            logger.error("Error finalizing Whisper speech: %s", exc)
            self.reset()
            return None

    @staticmethod
    def _clean_whisper_text(raw_text: str) -> str:
        """Clean Whisper output text by stripping repetitive tags and terminal punctuation."""
        if not raw_text:
            return ""
        # Remove Whisper prompt or timestamp tokens if any
        cleaned = re.sub(r"<\|.*?\|>", "", raw_text).strip()
        # Clean terminal periods/commas while preserving letters and numbers
        cleaned = re.sub(r"[\.,!?]+$", "", cleaned).strip()
        return cleaned
