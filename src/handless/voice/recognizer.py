"""Offline Speech Recognizer using Vosk.

Translates streaming audio into live partial transcripts and final commands
completely offline on the local CPU without network dependency.
"""

from __future__ import annotations

import json
import logging
import os
import urllib.request
import zipfile
from pathlib import Path
from typing import Optional

from vosk import KaldiRecognizer, Model, SetLogLevel

logger = logging.getLogger(__name__)

# Suppress verbose Vosk Kaldi logging
SetLogLevel(-1)

DEFAULT_MODEL_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"
DEFAULT_MODEL_NAME = "vosk-model-small-en-us-0.15"


class VoskSpeechRecognizer:
    """Offline speech recognizer wrapping Vosk Kaldi engine."""

    def __init__(
        self,
        model_path: Optional[str] = None,
        sample_rate: int = 16000,
        auto_download: bool = True,
    ) -> None:
        self.sample_rate = sample_rate
        self.model_path = self._resolve_model_path(model_path, auto_download)
        self.model: Optional[Model] = None
        self.recognizer: Optional[KaldiRecognizer] = None

        if self.model_path and Path(self.model_path).exists():
            self._load_model()
        else:
            logger.warning("Vosk model directory not found at: %s", self.model_path)

    def _resolve_model_path(self, model_path: Optional[str], auto_download: bool) -> Path:
        if model_path:
            p = Path(model_path)
            if p.is_absolute() and p.exists():
                return p
            # Check relative to cwd
            if p.exists():
                return p.resolve()

        # Check default paths:
        # 1. Project models/ dir
        project_model = Path("models") / DEFAULT_MODEL_NAME
        if project_model.exists():
            return project_model.resolve()

        # 2. User home dir
        home_model = Path.home() / ".vyoma-handless" / "models" / DEFAULT_MODEL_NAME
        if home_model.exists():
            return home_model.resolve()

        # Return default destination
        dest = Path("models") / DEFAULT_MODEL_NAME
        if auto_download:
            self._download_default_model(dest.parent)
        return dest.resolve()

    def _download_default_model(self, target_dir: Path) -> None:
        target_dir.mkdir(parents=True, exist_ok=True)
        dest_folder = target_dir / DEFAULT_MODEL_NAME
        if dest_folder.exists():
            return

        zip_path = target_dir / f"{DEFAULT_MODEL_NAME}.zip"
        logger.info("Downloading small English Vosk model (~40MB)...")
        try:
            urllib.request.urlretrieve(DEFAULT_MODEL_URL, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                zip_ref.extractall(target_dir)
            if zip_path.exists():
                zip_path.unlink()
            logger.info("Vosk model successfully downloaded and extracted to %s", dest_folder)
        except Exception as exc:
            logger.warning("Failed to auto-download Vosk model: %s. Local speech requires manual download.", exc)

    def _load_model(self) -> None:
        try:
            logger.info("Loading Vosk speech model from %s...", self.model_path)
            self.model = Model(str(self.model_path))
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)
            self.recognizer.SetWords(True)
            logger.info("Vosk model loaded successfully.")
        except Exception as exc:
            logger.error("Failed to initialize Vosk model: %s", exc)
            self.model = None
            self.recognizer = None

    def reset(self) -> None:
        """Reset internal recognizer state."""
        if self.model and self.sample_rate:
            self.recognizer = KaldiRecognizer(self.model, self.sample_rate)

    def process_chunk(self, audio_data: bytes) -> tuple[Optional[str], Optional[str]]:
        """Feed audio chunk into recognizer.

        Returns:
            (partial_text, final_text) tuple.
            One or both may be None if no speech / partial update occurred.
        """
        if not self.recognizer:
            return None, None

        if self.recognizer.AcceptWaveform(audio_data):
            res_str = self.recognizer.Result()
            try:
                data = json.loads(res_str)
                final_text = data.get("text", "").strip()
                return None, (final_text if final_text else None)
            except Exception:
                return None, None
        else:
            partial_str = self.recognizer.PartialResult()
            try:
                data = json.loads(partial_str)
                partial_text = data.get("partial", "").strip()
                return (partial_text if partial_text else None), None
            except Exception:
                return None, None

    def get_final_result(self) -> Optional[str]:
        """Force flush current buffer into final transcript."""
        if not self.recognizer:
            return None
        res_str = self.recognizer.FinalResult()
        try:
            data = json.loads(res_str)
            text = data.get("text", "").strip()
            self.reset()
            return text if text else None
        except Exception:
            self.reset()
            return None

    @property
    def is_ready(self) -> bool:
        return self.recognizer is not None
