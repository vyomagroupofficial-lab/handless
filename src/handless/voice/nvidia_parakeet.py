"""Offline Speech Recognizer using NVIDIA NeMo Parakeet model.

Accelerated via ONNX Runtime & sherpa-onnx with int8 AVX2 vectorization,
delivering state-of-the-art English conversational speech recognition
(trained on 36,000+ hours by NVIDIA) running 100% locally on CPU/DirectML.
"""

from __future__ import annotations

import array
import logging
import os
import tarfile
import urllib.request
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

DEFAULT_PARAKEET_URL = (
    "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/"
    "sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8.tar.bz2"
)
DEFAULT_PARAKEET_DIR = "sherpa-onnx-nemo-parakeet_tdt_ctc_110m-en-36000-int8"


class NvidiaParakeetRecognizer:
    """Offline speech recognizer powered by NVIDIA NeMo Parakeet FastConformer CTC."""

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
        p1 = Path("models") / DEFAULT_PARAKEET_DIR
        if p1.is_dir():
            return p1.resolve()

        p2 = Path.home() / ".vyoma-handless" / "models" / DEFAULT_PARAKEET_DIR
        if p2.is_dir():
            return p2.resolve()

        dest = Path("models") / DEFAULT_PARAKEET_DIR
        if auto_download:
            self._download_model(dest.parent)
        return dest.resolve()

    def _download_model(self, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_folder = target_dir / DEFAULT_PARAKEET_DIR
        if dest_folder.is_dir():
            return

        tar_path = target_dir / f"{DEFAULT_PARAKEET_DIR}.tar.bz2"
        logger.info("Downloading NVIDIA NeMo Parakeet 110M int8 model (~99MB)...")
        try:
            urllib.request.urlretrieve(DEFAULT_PARAKEET_URL, tar_path)
            with tarfile.open(tar_path, "r:bz2") as tar:
                tar.extractall(target_dir)
            if tar_path.exists():
                tar_path.unlink()
            logger.info("NVIDIA Parakeet model successfully installed to %s", dest_folder)
        except Exception as exc:
            logger.error("Failed to auto-download NVIDIA Parakeet model: %s", exc)

    def _load_model(self) -> None:
        try:
            import sherpa_onnx

            model_file = self.model_dir / "model.int8.onnx"
            if not model_file.exists():
                model_file = self.model_dir / "model.onnx"
            tokens_file = self.model_dir / "tokens.txt"

            if not model_file.exists() or not tokens_file.exists():
                logger.warning("NVIDIA Parakeet model files missing in: %s", self.model_dir)
                return

            logger.info("Initializing NVIDIA NeMo Parakeet STT (threads=%d)...", self.num_threads)
            self.recognizer = sherpa_onnx.OfflineRecognizer.from_nemo_ctc(
                model=str(model_file),
                tokens=str(tokens_file),
                num_threads=self.num_threads,
                sample_rate=self.sample_rate,
            )
            logger.info("NVIDIA NeMo Parakeet STT engine initialized successfully.")
        except Exception as exc:
            logger.error("Failed to load NVIDIA Parakeet engine: %s", exc)
            self.recognizer = None

    def reset(self) -> None:
        """Reset internal buffer state."""
        self._audio_buffer.clear()
        self._last_partial_len = 0

    def process_chunk(self, audio_data: bytes) -> tuple[Optional[str], Optional[str]]:
        """Feed audio chunk into recognizer.

        Returns:
            (partial_text, final_text) tuple.
        """
        if not self.recognizer or not audio_data:
            return None, None

        self._audio_buffer.extend(audio_data)

        # Process every ~0.5s of audio (16,000 samples/sec * 2 bytes/sample * 0.5s = 16,000 bytes)
        # to produce live partial feedback without excessive overhead
        partial = None
        final = None

        if len(self._audio_buffer) >= 16000 and (len(self._audio_buffer) - self._last_partial_len) >= 16000:
            self._last_partial_len = len(self._audio_buffer)
            try:
                # Convert raw 16-bit PCM bytes to float normalized samples
                raw_samples = array.array("h", self._audio_buffer)
                float_samples = [x / 32768.0 for x in raw_samples]

                stream = self.recognizer.create_stream()
                stream.accept_waveform(self.sample_rate, float_samples)
                self.recognizer.decode_stream(stream)
                text = stream.result.text.strip()
                if text:
                    partial = text
            except Exception as exc:
                logger.debug("Partial decoding error: %s", exc)

        return partial, final

    @property
    def is_ready(self) -> bool:
        """Check if model engine is loaded and ready."""
        return self.recognizer is not None

    def get_final_result(self) -> Optional[str]:
        """Alias for finalize_speech to maintain compatibility with Vosk interface."""
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
            final_text = stream.result.text.strip()

            self.reset()
            return final_text if final_text else None
        except Exception as exc:
            logger.error("Error finalizing NVIDIA Parakeet speech: %s", exc)
            self.reset()
            return None
