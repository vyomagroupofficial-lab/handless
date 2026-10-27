"""Microphone Audio Capture and Processing Pipeline.

Captures live microphone audio using sounddevice, runs voice activity detection,
and feeds chunks into the offline Vosk speech recognizer in a low-latency thread.
"""

from __future__ import annotations

import logging
import queue
import sys
import threading
import time
from typing import Callable, Optional

import sounddevice as sd

from .recognizer import VoskSpeechRecognizer
from .vad import FRAME_SIZE, VoiceActivityDetector

logger = logging.getLogger(__name__)

SAMPLE_RATE = 16000
BLOCK_SIZE = 3200  # 200ms audio chunks


class MicrophonePipeline:
    """Manages audio capture, VAD filtering, and speech recognition."""

    def __init__(
        self,
        recognizer: Optional[VoskSpeechRecognizer] = None,
        vad_aggressiveness: int = 2,
        on_partial: Optional[Callable[[str], None]] = None,
        on_final: Optional[Callable[[str], None]] = None,
        device_index: int = -1,
    ) -> None:
        self.recognizer = recognizer or VoskSpeechRecognizer(auto_download=False)
        self.vad = VoiceActivityDetector(aggressiveness=vad_aggressiveness)
        self.on_partial = on_partial
        self.on_final = on_final
        self.device_index = device_index if device_index >= 0 else None

        self._audio_queue: queue.Queue[bytes] = queue.Queue(maxsize=100)
        self._stream: Optional[sd.RawInputStream] = None
        self._worker_thread: Optional[threading.Thread] = None
        self._running = False
        self._is_listening = False  # Controls whether incoming audio is transcribed
        self._last_speech_time = 0.0
        self._speech_in_progress = False

    def start(self) -> bool:
        """Start the background audio capture stream and worker thread."""
        if self._running:
            return True

        try:
            self._running = True
            self._audio_queue = queue.Queue(maxsize=100)

            def audio_callback(indata: bytes, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
                if status:
                    logger.debug("SoundDevice status warning: %s", status)
                if self._running and self._is_listening:
                    try:
                        self._audio_queue.put_nowait(bytes(indata))
                    except queue.Full:
                        pass

            self._stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
                device=self.device_index,
                callback=audio_callback,
            )
            self._stream.start()

            self._worker_thread = threading.Thread(target=self._process_loop, daemon=True)
            self._worker_thread.start()
            logger.info("Microphone audio stream started successfully.")
            return True
        except Exception as exc:
            logger.error("Failed to start microphone stream: %s", exc)
            self._running = False
            return False

    def stop(self) -> None:
        """Stop microphone stream and processing thread."""
        self._running = False
        self._is_listening = False

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
            except Exception:
                pass
            self._stream = None

        if self._worker_thread is not None:
            self._worker_thread.join(timeout=1.0)
            self._worker_thread = None

        logger.info("Microphone pipeline stopped.")

    def set_listening(self, active: bool) -> None:
        """Activate or deactivate listening (e.g. for push-to-talk)."""
        self._is_listening = active
        if active:
            if self.recognizer.is_ready:
                self.recognizer.reset()
            self._speech_in_progress = False
            self._last_speech_time = time.time()
            logger.debug("Microphone listening activated.")
        else:
            # When listening ceases, force-flush any pending speech result
            if self.recognizer.is_ready:
                final = self.recognizer.get_final_result()
                if final and self.on_final:
                    try:
                        self.on_final(final)
                    except Exception as exc:
                        logger.error("Error in on_final callback: %s", exc)
            logger.debug("Microphone listening deactivated.")

    def is_listening(self) -> bool:
        return self._is_listening

    def _process_loop(self) -> None:
        """Background worker thread processing audio blocks from queue."""
        vad_buffer = bytearray()

        while self._running:
            try:
                chunk = self._audio_queue.get(timeout=0.1)
            except queue.Empty:
                continue

            vad_buffer.extend(chunk)

            # Process 640-byte (20ms) frames for VAD
            has_speech_in_chunk = False
            while len(vad_buffer) >= FRAME_SIZE:
                frame = bytes(vad_buffer[:FRAME_SIZE])
                del vad_buffer[:FRAME_SIZE]
                if self.vad.is_speech(frame):
                    has_speech_in_chunk = True

            now = time.time()
            if has_speech_in_chunk:
                self._speech_in_progress = True
                self._last_speech_time = now

            # Feed chunk to recognizer
            partial, final = self.recognizer.process_chunk(chunk)
            if partial and self.on_partial:
                try:
                    self.on_partial(partial)
                except Exception as exc:
                    logger.error("Error in on_partial: %s", exc)

            if final and self.on_final:
                try:
                    self.on_final(final)
                except Exception as exc:
                    logger.error("Error in on_final: %s", exc)

            # If continuous mode and silence detected for >1.5s after speech
            if (
                self._speech_in_progress
                and (now - self._last_speech_time > 1.5)
            ):
                self._speech_in_progress = False
                final = self.recognizer.get_final_result()
                if final and self.on_final:
                    try:
                        self.on_final(final)
                    except Exception as exc:
                        logger.error("Error in on_final silence flush: %s", exc)
