"""Speaker verification using SpeechBrain ECAPA-TDNN (192-dim)."""
from __future__ import annotations

import io
from functools import lru_cache

import numpy as np

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _load_encoder():
    """Load SpeechBrain ECAPA-TDNN model once."""
    from speechbrain.inference.speaker import EncoderClassifier
    classifier = EncoderClassifier.from_hparams(
        source="speechbrain/spkrec-ecapa-voxceleb",
        savedir="models/spkrec-ecapa",
        run_opts={"device": "cpu"},
    )
    return classifier


# In-memory enrollment cache (per-user). For prod, swap to Redis.
_enrollment_cache: dict[str, dict[int, bytes]] = {}


class SpeakerService:
    """Voice embedding extraction + cosine similarity.

    Embedding dim: 192 (ECAPA-TDNN)
    Similarity threshold: configurable via env (default 0.75)
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self.threshold = self.settings.speaker_similarity_threshold

    def extract_embedding(self, audio_bytes: bytes) -> np.ndarray:
        import torch
        import soundfile as sf
        buf = io.BytesIO(audio_bytes)
        data, sr = sf.read(buf, dtype="float32")
        if data.ndim > 1:
            data = data.mean(axis=1)
        if sr != self.settings.audio_sample_rate:
            import librosa
            data = librosa.resample(data, orig_sr=sr, target_sr=self.settings.audio_sample_rate)
        tensor = torch.from_numpy(np.asarray(data, dtype=np.float32)).unsqueeze(0)
        encoder = _load_encoder()
        emb = encoder.encode_batch(tensor)
        return emb.squeeze().detach().cpu().numpy()

    def cosine_similarity(self, a, b) -> float:
        a = np.asarray(a, dtype=np.float32).flatten()
        b = np.asarray(b, dtype=np.float32).flatten()
        denom = (np.linalg.norm(a) * np.linalg.norm(b)) or 1e-9
        return float(np.dot(a, b) / denom)

    # ---- Enrollment ----

    def cache_enrollment_chunk(self, user_id: str, index: int, audio_bytes: bytes) -> None:
        _enrollment_cache.setdefault(user_id, {})[index] = audio_bytes

    def finalize_enrollment(self, user_id: str) -> tuple[np.ndarray, float]:
        chunks = _enrollment_cache.get(user_id) or {}
        if len(chunks) < 3:
            raise ValueError(f"Enrollment needs 3 chunks, received {len(chunks)}")

        embeddings = []
        total_duration = 0.0
        for idx in sorted(chunks.keys()):
            emb = self.extract_embedding(chunks[idx])
            embeddings.append(emb)
            total_duration += self._audio_duration(chunks[idx])

        mean_embedding = np.mean(embeddings, axis=0)
        # Normalize
        norm = np.linalg.norm(mean_embedding) or 1e-9
        mean_embedding = mean_embedding / norm

        # Clear cache
        _enrollment_cache.pop(user_id, None)
        log.info("enrollment_complete", user_id=user_id, duration=total_duration, dims=mean_embedding.shape[0])
        return mean_embedding, total_duration

    def _audio_duration(self, audio_bytes: bytes) -> float:
        import soundfile as sf
        buf = io.BytesIO(audio_bytes)
        data, sr = sf.read(buf)
        return len(data) / sr
