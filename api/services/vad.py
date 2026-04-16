"""Voice Activity Detection using Silero VAD."""
from __future__ import annotations

import io
from functools import lru_cache

import numpy as np

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_silero():
    """Load Silero VAD model once."""
    import torch
    model, utils = torch.hub.load(
        repo_or_dir="snakers4/silero-vad",
        model="silero_vad",
        trust_repo=True,
        verbose=False,
    )
    return model, utils


class VADService:
    """Silero VAD wrapper.

    Input: raw bytes of 16kHz mono WAV / PCM audio.
    Output: (speech_detected: bool, confidence: float)
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.threshold = self.settings.vad_threshold
        self.sample_rate = self.settings.audio_sample_rate

    def detect(self, audio_bytes: bytes) -> tuple[bool, float]:
        """Return True if speech is present above threshold."""
        try:
            audio = self._bytes_to_tensor(audio_bytes)
        except Exception as e:
            log.warning("vad_decode_failed", error=str(e))
            return False, 0.0

        model, utils = _load_silero()
        get_speech_timestamps = utils[0]
        timestamps = get_speech_timestamps(
            audio,
            model,
            sampling_rate=self.sample_rate,
            threshold=self.threshold,
        )
        if not timestamps:
            return False, 0.0
        total_speech = sum(seg["end"] - seg["start"] for seg in timestamps)
        total = len(audio)
        ratio = total_speech / max(total, 1)
        return True, float(ratio)

    def _bytes_to_tensor(self, audio_bytes: bytes):
        import torch
        import soundfile as sf
        buf = io.BytesIO(audio_bytes)
        data, sr = sf.read(buf, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)  # mono
        if sr != self.sample_rate:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=self.sample_rate)
        return torch.from_numpy(np.asarray(data, dtype=np.float32))
