"""Transcription via OpenAI Whisper API (cloud).

Switched from local faster-whisper to OpenAI API for:
  - Zero heavy ML dependencies in the Railway image
  - Faster build + lower RAM
  - ~$0.006 per minute of audio (negligible at MVP scale)
"""
from __future__ import annotations

import io
from functools import lru_cache

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _client():
    from openai import OpenAI
    return OpenAI(api_key=get_settings().openai_api_key)


class TranscriptionService:
    """Speech-to-text using OpenAI Whisper API."""

    MODEL = "whisper-1"  # 99% accurate for Hebrew + English

    def transcribe(self, audio_bytes: bytes, language: str | None = None) -> dict:
        """Return {text, language, word_count, confidence, model_used}."""
        if not audio_bytes:
            return self._empty()

        try:
            buf = io.BytesIO(audio_bytes)
            buf.name = "chunk.wav"  # OpenAI needs a filename for content-type
            params = {
                "model": self.MODEL,
                "file": buf,
                "response_format": "verbose_json",
                "temperature": 0,
            }
            if language:
                params["language"] = language
            resp = _client().audio.transcriptions.create(**params)

            text = (resp.text or "").strip()
            detected_lang = getattr(resp, "language", None) or language or "he"
            # Whisper API doesn't give per-segment confidence, approximate via no_speech_prob on avg_logprob
            avg_logprob = 0.0
            segs = getattr(resp, "segments", None) or []
            if segs:
                avg_logprob = sum(s.get("avg_logprob", 0) for s in segs) / len(segs)
            import math
            confidence = min(max(math.exp(avg_logprob), 0.0), 1.0) if avg_logprob else 0.85

            return {
                "text": text,
                "language": detected_lang,
                "word_count": len(text.split()),
                "confidence": confidence,
                "model_used": f"openai-{self.MODEL}",
            }
        except Exception as e:
            log.error("transcription_failed", error=str(e))
            return self._empty()

    @staticmethod
    def _empty() -> dict:
        return {
            "text": "",
            "language": "he",
            "word_count": 0,
            "confidence": 0.0,
            "model_used": "none",
        }
