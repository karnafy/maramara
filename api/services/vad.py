"""Voice Activity Detection - simple RMS energy + zero-crossing threshold.

Replaces Silero VAD (which needs torch). Good enough for MVP:
gates out pure silence before wasting Whisper API calls.

Real VAD (Silero) can be re-added later as a heavier worker image.
"""
from __future__ import annotations

import io

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


class VADService:
    """Lightweight RMS-based speech detector.

    Input: bytes of a WAV/PCM/mp3/etc chunk.
    Output: (has_speech: bool, confidence: float in [0,1])
    """

    # Thresholds tuned for 16kHz mono speech vs background noise.
    RMS_MIN = 0.008         # below this = silence
    ZERO_CROSSING_MIN = 0.02  # speech has more zero-crossings than steady hiss

    def __init__(self) -> None:
        self.settings = get_settings()

    def detect(self, audio_bytes: bytes) -> tuple[bool, float]:
        try:
            import numpy as np
            import soundfile as sf
            buf = io.BytesIO(audio_bytes)
            data, sr = sf.read(buf, dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            if len(data) == 0:
                return False, 0.0

            rms = float(np.sqrt(np.mean(data.astype("float64") ** 2)))
            zero_cross = float(np.mean(np.abs(np.diff(np.signbit(data).astype(int)))))

            has_speech = rms > self.RMS_MIN and zero_cross > self.ZERO_CROSSING_MIN
            confidence = min(1.0, (rms / (self.RMS_MIN * 4)) * (zero_cross / (self.ZERO_CROSSING_MIN * 4)))
            return has_speech, confidence
        except Exception as e:
            log.warning("vad_failed", error=str(e))
            # Fail open - assume speech, let downstream (Whisper) decide
            return True, 0.5
