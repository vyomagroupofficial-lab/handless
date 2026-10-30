"""Microphone hardware audio capture engine for live meeting transcription ("You").

Runs in parallel with SystemLoopbackCapture to provide physically isolated,
zero-crosstalk stereo diarization during calls (Zoom, Meet, WhatsApp, Teams).
"""

from __future__ import annotations

import logging
import math
import struct
import threading
import time
from typing import Callable, Optional

import webrtcvad

logger = logging.getLogger(__name__)

FRAME_SIZE_16K = 640          # 20ms at 16kHz mono (320 samples * 2 bytes)
SILENCE_THRESHOLD_SEC = 0.85     # Pause duration to treat user speech as complete
SAMPLE_RATE = 16000
BLOCK_SIZE = 3200             # 200ms audio chunks


class MicChannelCapture:
    """Captures the local user's microphone audio for the 'You' channel in meetings.

    Downsamples audio to 16kHz mono 16-bit PCM, applies WebRTC Voice Activity Detection (VAD)
    to segment user speech into discrete utterances, and calculates real-time RMS audio levels.
    """

    def __init__(
        self,
        on_speech_segment: Optional[Callable[[bytes], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        vad_aggressiveness: int = 2,
        device_index: Optional[int] = None,
    ) -> None:
        self.on_speech_segment = on_speech_segment
        self.on_audio_level = on_audio_level
        self._vad = webrtcvad.Vad(max(0, min(3, vad_aggressiveness)))
        self.device_index = device_index

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stream = None

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> bool:
        """Begin capturing microphone audio in a background thread."""
        if self._running:
            return True

        self._running = True
        self._thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._thread.start()
        logger.info("Microphone channel audio capture started.")
        return True

    def stop(self) -> None:
        """Stop capturing microphone audio."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.2)
        self._thread = None
        logger.info("Microphone channel audio capture stopped.")

    def _capture_worker(self) -> None:
        """Microphone capture loop with WebRTC VAD segmentation."""
        try:
            import sounddevice as sd
        except ImportError:
            logger.error("sounddevice is not installed.")
            self._running = False
            return

        stream = None
        try:
            vad_fifo = bytearray()
            speech_buffer = bytearray()
            is_in_speech = False
            last_speech_time = 0.0

            def audio_callback(indata: bytes, frames: int, time_info: dict, status: sd.CallbackFlags) -> None:
                nonlocal is_in_speech, last_speech_time
                if not self._running:
                    return

                mono_16k_chunk = bytes(indata)
                if not mono_16k_chunk:
                    return

                # 1. Audio Level (RMS) for UI Equalizer
                if self.on_audio_level:
                    rms = self._calculate_rms(mono_16k_chunk)
                    level = min(1.0, rms * 14.0)
                    try:
                        self.on_audio_level(level)
                    except Exception:
                        pass

                # 2. VAD processing in 640-byte (20ms) slices
                vad_fifo.extend(mono_16k_chunk)
                while len(vad_fifo) >= FRAME_SIZE_16K:
                    frame = bytes(vad_fifo[:FRAME_SIZE_16K])
                    del vad_fifo[:FRAME_SIZE_16K]

                    is_speech = False
                    try:
                        is_speech = self._vad.is_speech(frame, 16000)
                    except Exception:
                        pass

                    if is_speech:
                        if not is_in_speech:
                            is_in_speech = True
                        speech_buffer.extend(frame)
                        last_speech_time = time.time()
                    elif is_in_speech:
                        speech_buffer.extend(frame)

                now = time.time()
                # 3. Check if user has finished speaking
                if is_in_speech and (now - last_speech_time > SILENCE_THRESHOLD_SEC):
                    is_in_speech = False
                    # Minimum speech segment: ~0.35s (5600 bytes)
                    if len(speech_buffer) >= 5600:
                        segment_bytes = bytes(speech_buffer)
                        if self.on_speech_segment:
                            try:
                                self.on_speech_segment(segment_bytes)
                            except Exception as exc:
                                logger.error("Error dispatching mic speech segment: %s", exc)
                    speech_buffer.clear()

            stream = sd.RawInputStream(
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_SIZE,
                dtype="int16",
                channels=1,
                device=self.device_index,
                callback=audio_callback,
            )
            stream.start()

            while self._running:
                time.sleep(0.05)

        except Exception as exc:
            if self._running:
                logger.warning("Microphone stream error (using silent fallback): %s", exc)
                # Keep thread alive to avoid crashing if mic is disconnected
                while self._running:
                    time.sleep(0.1)
        finally:
            if stream is not None:
                try:
                    stream.stop()
                    stream.close()
                except Exception:
                    pass

    @staticmethod
    def _calculate_rms(pcm_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) amplitude of 16-bit PCM bytes."""
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", pcm_bytes)
        sum_sq = sum(s * s for s in shorts)
        rms = math.sqrt(sum_sq / count)
        return min(1.0, rms / 10000.0)

