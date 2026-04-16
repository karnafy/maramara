"""Transcription via faster-whisper large-v3 (Hebrew + English)."""
from __future__ import annotations

import io
from functools import lru_cache

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_whisper():
    from faster_whisper import WhisperModel
    settings = get_settings()
    model = WhisperModel(
        settings.whisper_model,
        device=settings.whisper_device,
        compute_type=settings.whisper_compute_type,
    )
    log.info("whisper_loaded", model=settings.whisper_model, device=settings.whisper_device)
    return model


class TranscriptionService:
    """Speech-to-text using faster-whisper."""

    def __init__(self) -> None:
        self.settings = get_settings()

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> dict:
        """Return {text, language, words, confidence}."""
        model = _load_whisper()
        segments_iter, info = model.transcribe(
            io.BytesIO(audio_bytes),
            language=language,  # auto-detect if None
            beam_size=5,
            vad_filter=True,
            word_timestamps=False,
        )
        parts = []
        total_logprob = 0.0
        count = 0
        for seg in segments_iter:
            parts.append(seg.text)
            total_logprob += seg.avg_logprob or 0.0
            count += 1
        text = "".join(parts).strip()
        confidence = float(2.71828 ** (total_logprob / count)) if count else 0.0
        return {
            "text": text,
            "language": info.language,
            "word_count": len(text.split()),
            "confidence": min(max(confidence, 0.0), 1.0),
            "model_used": f"faster-whisper-{self.settings.whisper_model}",
        }
