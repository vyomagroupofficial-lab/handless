"""Windows WASAPI Loopback audio capture engine for system sound (Zoom, Meet, WhatsApp, etc.).
"""

from __future__ import annotations

import logging
import math
import queue
import struct
import threading
import time
from typing import Callable, Optional

import webrtcvad

logger = logging.getLogger(__name__)

FRAME_SIZE_16K = 640       # 20ms at 16kHz mono (320 samples * 2 bytes)
SILENCE_THRESHOLD_SEC = 0.85  # Pause duration to treat speech as complete


class SystemLoopbackCapture:
    """Captures desktop audio output (speakers/headphones) via Windows WASAPI Loopback.

    Downsamples audio to 16kHz mono PCM, applies WebRTC Voice Activity Detection (VAD)
    to segment remote participant speech into discrete utterances, and calculates real-time
    RMS audio levels for UI meters.
    """

    def __init__(
        self,
        on_speech_segment: Optional[Callable[[bytes], None]] = None,
        on_audio_level: Optional[Callable[[float], None]] = None,
        vad_aggressiveness: int = 2,
    ) -> None:
        self.on_speech_segment = on_speech_segment
        self.on_audio_level = on_audio_level
        self._vad = webrtcvad.Vad(max(0, min(3, vad_aggressiveness)))

        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._pyaudio_inst = None
        self._stream = None
        self._device_info: Optional[dict] = None

    @property
    def is_running(self) -> bool:
        return self._running

    def find_loopback_device(self) -> Optional[dict]:
        """Find the default WASAPI loopback device corresponding to default output speakers."""
        try:
            import pyaudiowpatch as pyaudio

            p = pyaudio.PyAudio()
            try:
                wasapi_info = p.get_host_api_info_by_type(pyaudio.paWASAPI)
                default_speakers = p.get_device_info_by_index(wasapi_info["defaultOutputDevice"])
                if default_speakers.get("isLoopbackDevice", False):
                    return default_speakers

                # Search through loopback devices matching default speakers
                for loopback in p.get_loopback_device_info_generator():
                    if default_speakers["name"] in loopback["name"]:
                        return loopback

                # Fallback to any available loopback device
                for loopback in p.get_loopback_device_info_generator():
                    return loopback
            finally:
                p.terminate()
        except Exception as exc:
            logger.warning("Could not enumerate WASAPI loopback devices: %s", exc)

        return None

    def start(self) -> bool:
        """Begin capturing system audio in a background thread."""
        if self._running:
            return True

        self._device_info = self.find_loopback_device()
        if not self._device_info:
            logger.warning("No WASAPI Loopback device found on this system.")
            return False

        self._running = True
        self._thread = threading.Thread(target=self._capture_worker, daemon=True)
        self._thread.start()
        logger.info("System loopback audio capture started on '%s'", self._device_info.get("name", "Unknown"))
        return True

    def stop(self) -> None:
        """Stop capturing system audio."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.2)
        self._thread = None
        logger.info("System loopback audio capture stopped.")

    def _capture_worker(self) -> None:
        """Dedicated loopback capture loop with downsampling and VAD segmentation."""
        try:
            import pyaudiowpatch as pyaudio
        except ImportError:
            logger.error("pyaudiowpatch is not installed.")
            self._running = False
            return

        p = pyaudio.PyAudio()
        stream = None
        try:
            dev = self._device_info
            if not dev:
                return

            sample_rate = int(dev["defaultSampleRate"])
            channels = int(dev["maxInputChannels"])
            frames_per_buffer = 960 if sample_rate == 48000 else 882

            stream = p.open(
                format=pyaudio.paInt16,
                channels=channels,
                rate=sample_rate,
                input=True,
                input_device_index=dev["index"],
                frames_per_buffer=frames_per_buffer,
            )

            vad_fifo = bytearray()
            speech_buffer = bytearray()
            is_in_speech = False
            last_speech_time = 0.0

            while self._running:
                try:
                    data = stream.read(frames_per_buffer, exception_on_overflow=False)
                except Exception as e:
                    if not self._running:
                        break
                    logger.debug("Loopback stream read warning: %s", e)
                    time.sleep(0.01)
                    continue

                if not data:
                    continue

                # 1. Convert to 16kHz Mono 16-bit PCM
                mono_16k_chunk = self._resample_to_16k_mono(data, channels, sample_rate)
                if not mono_16k_chunk:
                    continue

                # 2. Audio Level (RMS) for UI Equalizer
                if self.on_audio_level:
                    rms = self._calculate_rms(mono_16k_chunk)
                    level = min(1.0, rms * 16.0)
                    self.on_audio_level(level)

                # 3. WebRTC VAD Processing in 640-byte (20ms) slices
                vad_fifo.extend(mono_16k_chunk)
                has_speech_in_buffer = False

                while len(vad_fifo) >= FRAME_SIZE_16K:
                    frame = bytes(vad_fifo[:FRAME_SIZE_16K])
                    del vad_fifo[:FRAME_SIZE_16K]

                    is_speech = False
                    try:
                        is_speech = self._vad.is_speech(frame, 16000)
                    except Exception:
                        pass

                    if is_speech:
                        has_speech_in_buffer = True
                        if not is_in_speech:
                            is_in_speech = True
                        speech_buffer.extend(frame)
                        last_speech_time = time.time()
                    elif is_in_speech:
                        # Include post-speech trailing frame
                        speech_buffer.extend(frame)

                now = time.time()
                # 4. Check if participant has finished speaking (silence detected)
                if is_in_speech and (now - last_speech_time > SILENCE_THRESHOLD_SEC):
                    is_in_speech = False
                    # Minimum viable speech segment: ~0.4s (6400 bytes)
                    if len(speech_buffer) >= 6400:
                        segment_bytes = bytes(speech_buffer)
                        if self.on_speech_segment:
                            try:
                                self.on_speech_segment(segment_bytes)
                            except Exception as exc:
                                logger.error("Error dispatching system speech segment: %s", exc)
                    speech_buffer.clear()

        except Exception as exc:
            if self._running:
                logger.error("Error in system loopback audio capture: %s", exc)
        finally:
            if stream:
                try:
                    stream.stop_stream()
                    stream.close()
                except Exception:
                    pass
            p.terminate()

    @staticmethod
    def _resample_to_16k_mono(raw_bytes: bytes, channels: int, sample_rate: int) -> bytes:
        """Convert raw multi-channel audio to 16kHz 16-bit mono PCM."""
        if not raw_bytes:
            return b""

        total_samples = len(raw_bytes) // 2
        shorts = struct.unpack(f"{total_samples}h", raw_bytes)

        # 1. Convert multi-channel to mono
        if channels == 2:
            mono = [(shorts[i] + shorts[i + 1]) // 2 for i in range(0, total_samples, 2)]
        elif channels > 2:
            mono = [shorts[i] for i in range(0, total_samples, channels)]
        else:
            mono = list(shorts)

        # 2. Resample to 16kHz
        if sample_rate == 48000:
            # 48000 -> 16000 is exact 3x decimation
            resampled = mono[::3]
        elif sample_rate == 44100:
            # Simple linear approximation for 44.1k
            step = 44100.0 / 16000.0
            out_len = int(len(mono) / step)
            resampled = [mono[int(i * step)] for i in range(out_len)]
        elif sample_rate == 16000:
            resampled = mono
        else:
            step = sample_rate / 16000.0
            out_len = int(len(mono) / step)
            resampled = [mono[int(i * step)] for i in range(out_len)]

        return struct.pack(f"{len(resampled)}h", *resampled)

    @staticmethod
    def _calculate_rms(pcm_bytes: bytes) -> float:
        """Calculate Root Mean Square (RMS) amplitude of 16-bit PCM bytes."""
        count = len(pcm_bytes) // 2
        if count == 0:
            return 0.0
        shorts = struct.unpack(f"{count}h", pcm_bytes)
        sum_sq = sum(s * s for s in shorts)
        rms = math.sqrt(sum_sq / count)
        return min(1.0, rms / 12000.0)

