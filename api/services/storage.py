"""Supabase Storage helper for raw audio recordings.

Storage layout:
    recordings/{user_id}/{segment_id}.{ext}

The service-role client is used so that uploads from background workers
are not blocked by per-row RLS. Per-user RLS still protects direct client
reads (mobile/web never reads files directly in the MVP — a signed URL is
issued on demand via `signed_url()`).
"""
from __future__ import annotations

from dataclasses import dataclass

from config import get_settings
from db.supabase_client import get_admin_client
from utils.logger import get_logger

log = get_logger(__name__)


_MIME_TO_EXT = {
    "audio/wav": "wav",
    "audio/x-wav": "wav",
    "audio/mpeg": "mp3",
    "audio/mp4": "m4a",
    "audio/m4a": "m4a",
    "audio/x-m4a": "m4a",
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/flac": "flac",
}


def ext_for_mime(mime: str | None, fallback: str = "wav") -> str:
    if not mime:
        return fallback
    return _MIME_TO_EXT.get(mime.lower().split(";", 1)[0].strip(), fallback)


@dataclass(frozen=True)
class StoredObject:
    path: str
    bucket: str
    size_bytes: int
    content_type: str


class StorageService:
    """Thin wrapper around Supabase Storage for audio artefacts."""

    def __init__(self) -> None:
        settings = get_settings()
        self._bucket = settings.audio_storage_bucket

    @property
    def bucket(self) -> str:
        return self._bucket

    def upload_audio(
        self,
        *,
        user_id: str,
        segment_id: str,
        audio_bytes: bytes,
        content_type: str = "audio/wav",
    ) -> StoredObject:
        """Upload raw audio and return its storage path.

        Raises on failure so the caller can mark the segment as failed.
        """
        if not audio_bytes:
            raise ValueError("audio_bytes is empty")

        ext = ext_for_mime(content_type)
        path = f"{user_id}/{segment_id}.{ext}"
        client = get_admin_client()

        client.storage.from_(self._bucket).upload(
            path=path,
            file=audio_bytes,
            file_options={
                "content-type": content_type,
                "upsert": "true",
            },
        )
        log.info("audio_uploaded", path=path, size=len(audio_bytes), mime=content_type)
        return StoredObject(
            path=path,
            bucket=self._bucket,
            size_bytes=len(audio_bytes),
            content_type=content_type,
        )

    def download_audio(self, path: str) -> bytes:
        client = get_admin_client()
        return client.storage.from_(self._bucket).download(path)

    def delete_audio(self, path: str) -> None:
        client = get_admin_client()
        try:
            client.storage.from_(self._bucket).remove([path])
            log.info("audio_deleted", path=path)
        except Exception as e:
            log.warning("audio_delete_failed", path=path, error=str(e))

    def signed_url(self, path: str, expires_in_sec: int = 3600) -> str:
        client = get_admin_client()
        resp = client.storage.from_(self._bucket).create_signed_url(path, expires_in_sec)
        if isinstance(resp, dict):
            return resp.get("signedURL") or resp.get("signedUrl") or ""
        return getattr(resp, "signed_url", "") or ""
