"""Voice Activity Detection (VAD) module.

Combines WebRTC VAD with RMS energy calculation to filter silence and
background noise during continuous and push-to-talk microphone recording.
"""

from __future__ import annotations

import math
import struct
import webrtcvad

SAMPLE_RATE = 16000
FRAME_DURATION_MS = 20  # 20ms frames: 320 samples at 16kHz
FRAME_SIZE = int(SAMPLE_RATE * (FRAME_DURATION_MS / 1000.0) * 2)  # 2 bytes per sample (int16) = 640 bytes


def calculate_rms(pcm_data: bytes) -> float:
    """Calculate Root Mean Square energy without relying on deprecated audioop."""
    count = len(pcm_data) // 2
    if count == 0:
        return 0.0
    # Unpack 16-bit signed integers (little-endian)
    shorts = struct.unpack(f"<{count}h", pcm_data)
    sum_squares = sum(sample * sample for sample in shorts)
    return math.sqrt(sum_squares / count)


class VoiceActivityDetector:
    """Detects speech in 16kHz mono 16-bit PCM frames."""

    def __init__(self, aggressiveness: int = 2, min_rms: float = 180.0) -> None:
        """Initialize VAD.

        Args:
            aggressiveness: 0 (least aggressive) to 3 (most aggressive) in filtering noise.
            min_rms: Minimum Root Mean Square energy threshold to qualify as speech.
        """
        self.vad = webrtcvad.Vad(max(0, min(3, aggressiveness)))
        self.min_rms = min_rms

    def is_speech(self, frame: bytes) -> bool:
        """Check if a 640-byte audio frame contains human speech."""
        if len(frame) != FRAME_SIZE:
            return False

        # First check raw audio energy
        rms = calculate_rms(frame)
        if rms < self.min_rms:
            return False

        try:
            return self.vad.is_speech(frame, SAMPLE_RATE)
        except Exception:
            return rms > (self.min_rms * 1.5)
