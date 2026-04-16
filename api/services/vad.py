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
            data = self._decode(audio_bytes)
            if data is None or len(data) == 0:
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

    @staticmethod
    def _decode(audio_bytes: bytes):
        """Decode WAV/PCM via soundfile, or WEBM/OGG/MP4 via pydub+ffmpeg."""
        import numpy as np
        # Try soundfile first (WAV/FLAC/OGG)
        try:
            import soundfile as sf
            data, _sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
            if data.ndim > 1:
                data = data.mean(axis=1)
            return data
        except Exception:
            pass
        # Fallback: pydub (needs ffmpeg for webm/mp4)
        try:
            from pydub import AudioSegment
            seg = AudioSegment.from_file(io.BytesIO(audio_bytes))
            samples = np.array(seg.get_array_of_samples()).astype("float32")
            if seg.channels > 1:
                samples = samples.reshape(-1, seg.channels).mean(axis=1)
            # Normalize to [-1, 1]
            max_val = float(1 << (8 * seg.sample_width - 1))
            return samples / max_val
        except Exception as e:
            log.debug("pydub_decode_failed", error=str(e))
            return None
