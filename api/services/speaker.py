"""Speaker verification - MVP stub (trust the JWT).

Full ML-based speaker verification (ECAPA-TDNN, Resemblyzer) requires
torch. For MVP we accept the authenticated user's JWT as sufficient
identity proof: the mobile app will only record on the owner's device.

When we re-introduce on-server speaker verification, we'll swap this
stub for a worker that reads the `voice_profiles.embedding_vector`
(pgvector) and compares a fresh embedding. Endpoint contracts stay
identical.
"""
from __future__ import annotations

import io
import hashlib
from typing import Any

import numpy as np

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)

# In-memory enrollment cache (per-user). For prod → Redis.
_enrollment_cache: dict[str, dict[int, bytes]] = {}

# Embedding dimension kept at 192 to match pgvector column + future ECAPA model.
EMBEDDING_DIM = 192


class SpeakerService:
    """MVP-compatible stub with the same contract as a real ML implementation."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.threshold = self.settings.speaker_similarity_threshold

    # ---------- Runtime verification ----------

    def extract_embedding(self, audio_bytes: bytes) -> np.ndarray:
        """Return a deterministic-from-content 192-dim pseudo embedding.

        Uses audio hash → seeded RNG so identical bytes → identical vector.
        Good enough to exercise the DB pipeline; will be replaced with real
        ECAPA-TDNN output when we re-enable local ML.
        """
        digest = hashlib.sha256(audio_bytes).digest()
        seed = int.from_bytes(digest[:4], "big")
        rng = np.random.default_rng(seed)
        vec = rng.standard_normal(EMBEDDING_DIM).astype("float32")
        norm = np.linalg.norm(vec) or 1e-9
        return vec / norm

    def cosine_similarity(self, a: Any, b: Any) -> float:
        a_arr = np.asarray(a, dtype=np.float32).flatten()
        b_arr = np.asarray(b, dtype=np.float32).flatten()
        denom = (np.linalg.norm(a_arr) * np.linalg.norm(b_arr)) or 1e-9
        return float(np.dot(a_arr, b_arr) / denom)

    # ---------- Enrollment ----------

    def cache_enrollment_chunk(self, user_id: str, index: int, audio_bytes: bytes) -> None:
        _enrollment_cache.setdefault(user_id, {})[index] = audio_bytes

    def finalize_enrollment(self, user_id: str) -> tuple[np.ndarray, float]:
        chunks = _enrollment_cache.get(user_id) or {}
        if len(chunks) < 3:
            raise ValueError(f"Enrollment needs 3 chunks, received {len(chunks)}")

        embeddings = []
        total_duration = 0.0
        for idx in sorted(chunks.keys()):
            embeddings.append(self.extract_embedding(chunks[idx]))
            total_duration += self._audio_duration(chunks[idx])

        mean_emb = np.mean(embeddings, axis=0)
        mean_emb = mean_emb / (np.linalg.norm(mean_emb) or 1e-9)
        _enrollment_cache.pop(user_id, None)
        log.info("enrollment_complete_stub", user_id=user_id, duration=total_duration, dims=mean_emb.shape[0])
        return mean_emb, total_duration

    def _audio_duration(self, audio_bytes: bytes) -> float:
        try:
            import soundfile as sf
            data, sr = sf.read(io.BytesIO(audio_bytes))
            return len(data) / sr
        except Exception:
            # Fallback: assume 10 seconds
            return 10.0
