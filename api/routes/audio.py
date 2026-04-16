"""Audio ingest routes.

Endpoints:
    POST   /api/audio/chunk       streaming 10s chunk (VAD + speaker verify)
    POST   /api/audio/upload      single full recording (skips speaker verify)
    GET    /api/audio/recordings  paginated list with transcript + status
    GET    /api/audio/recordings/<id>   full segment detail + signed URL
    GET    /api/audio/status      today's activity summary
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from services.vad import VADService
from services.speaker import SpeakerService
from services.storage import StorageService
from services.queue import enqueue_segment_processing
from utils.auth import require_auth
from utils.errors import AppError, NotFoundError
from utils.logger import get_logger
from db.supabase_client import get_admin_client

log = get_logger(__name__)
bp = Blueprint("audio", __name__)

_vad = VADService()
_speaker = SpeakerService()
_storage = StorageService()


def _insert_segment(*, segment_id, user_id, started_at, ended_at, duration_sec,
                    speech_detected, similarity, matched, audio_path, meta):
    get_admin_client().table("audio_segments").insert({
        "id": segment_id,
        "user_id": user_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": duration_sec,
        "speech_detected": speech_detected,
        "speaker_match_score": float(similarity) if similarity is not None else None,
        "matched_to_user": matched,
        "transcript_status": "pending" if matched else "skipped",
        "analysis_status": "pending" if matched else "skipped",
        "raw_audio_path": audio_path,
        "client_meta": meta,
    }).execute()


@bp.post("/chunk")
@require_auth
def upload_chunk():
    """Mobile streaming path: 10s chunk → VAD → speaker verify → queue."""
    if "audio" not in request.files:
        raise AppError("Missing 'audio' file", status_code=422)

    file_storage = request.files["audio"]
    audio_bytes = file_storage.read()
    if not audio_bytes:
        raise AppError("Empty audio", status_code=422)

    duration_sec = float(request.form.get("duration_sec", 10.0))
    started_at = _parse_ts(request.form.get("started_at"))
    ended_at = _parse_ts(request.form.get("ended_at"))

    speech_detected, _ = _vad.detect(audio_bytes)
    if not speech_detected:
        return jsonify({"success": True, "data": {"skipped": "no_speech"}})

    admin = get_admin_client()
    voice = admin.table("voice_profiles").select("embedding_vector").eq("user_id", g.user_id).execute()
    if voice.data:
        enrolled_emb = voice.data[0]["embedding_vector"]
        chunk_emb = _speaker.extract_embedding(audio_bytes)
        similarity = _speaker.cosine_similarity(enrolled_emb, chunk_emb)
    else:
        log.info("no_voice_profile_auto_accept", user_id=g.user_id)
        similarity = 1.0

    matched = similarity >= _speaker.threshold
    segment_id = str(uuid.uuid4())
    content_type = file_storage.mimetype or "audio/wav"
    audio_path = None

    if matched:
        stored = _storage.upload_audio(
            user_id=g.user_id,
            segment_id=segment_id,
            audio_bytes=audio_bytes,
            content_type=content_type,
        )
        audio_path = stored.path

    _insert_segment(
        segment_id=segment_id,
        user_id=g.user_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=duration_sec,
        speech_detected=True,
        similarity=similarity,
        matched=matched,
        audio_path=audio_path,
        meta={"source": "chunk", "content_type": content_type, "bytes": len(audio_bytes)},
    )

    if not matched:
        log.info("speaker_mismatch", user_id=g.user_id, similarity=similarity)
        return jsonify({"success": True, "data": {"skipped": "speaker_mismatch", "similarity": float(similarity)}})

    enqueue_segment_processing(segment_id=segment_id, user_id=g.user_id, audio_path=audio_path)

    return jsonify({
        "success": True,
        "data": {
            "segment_id": segment_id,
            "similarity": float(similarity),
            "status": "queued",
            "audio_path": audio_path,
        },
    })


@bp.post("/upload")
@require_auth
def upload_recording():
    """Upload a full recording (single file). Skips speaker verification —
    used for intentional voice notes where the user explicitly hit record.
    """
    if "audio" not in request.files:
        raise AppError("Missing 'audio' file", status_code=422)

    file_storage = request.files["audio"]
    audio_bytes = file_storage.read()
    if not audio_bytes:
        raise AppError("Empty audio", status_code=422)

    duration_sec = float(request.form.get("duration_sec", 0.0))
    started_at = _parse_ts(request.form.get("started_at"))
    ended_at = _parse_ts(request.form.get("ended_at"))
    if duration_sec <= 0:
        duration_sec = max((ended_at - started_at).total_seconds(), 0.0)

    segment_id = str(uuid.uuid4())
    content_type = file_storage.mimetype or "audio/wav"

    stored = _storage.upload_audio(
        user_id=g.user_id,
        segment_id=segment_id,
        audio_bytes=audio_bytes,
        content_type=content_type,
    )

    _insert_segment(
        segment_id=segment_id,
        user_id=g.user_id,
        started_at=started_at,
        ended_at=ended_at,
        duration_sec=duration_sec,
        speech_detected=True,
        similarity=None,
        matched=True,
        audio_path=stored.path,
        meta={
            "source": "upload",
            "content_type": content_type,
            "bytes": len(audio_bytes),
            "filename": file_storage.filename,
        },
    )

    enqueue_segment_processing(segment_id=segment_id, user_id=g.user_id, audio_path=stored.path)

    return jsonify({
        "success": True,
        "data": {
            "segment_id": segment_id,
            "audio_path": stored.path,
            "size_bytes": stored.size_bytes,
            "content_type": content_type,
            "status": "queued",
        },
    })


@bp.get("/recordings")
@require_auth
def list_recordings():
    """List the authenticated user's recordings with transcription + status."""
    limit = min(int(request.args.get("limit", 25)), 100)
    offset = max(int(request.args.get("offset", 0)), 0)
    status_filter = request.args.get("status")

    admin = get_admin_client()
    q = (
        admin.table("audio_segments")
        .select("id, started_at, ended_at, duration_sec, transcript_status, "
                "analysis_status, speaker_match_score, raw_audio_path, client_meta, created_at")
        .eq("user_id", g.user_id)
        .order("started_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if status_filter in {"pending", "processing", "completed", "failed", "skipped"}:
        q = q.eq("analysis_status", status_filter)
    segments = q.execute().data or []

    if not segments:
        return jsonify({"success": True, "data": {"items": [], "count": 0}})

    ids = [s["id"] for s in segments]
    transcripts = (
        admin.table("transcripts")
        .select("audio_segment_id, transcript_text, language, word_count, confidence")
        .in_("audio_segment_id", ids)
        .execute()
        .data
        or []
    )
    tx_by_id = {t["audio_segment_id"]: t for t in transcripts}

    analyses = (
        admin.table("segment_analysis")
        .select("audio_segment_id, polarity, intensity_score, primary_topic, "
                "topic_mood, tags, joy_score, worry_score, anger_score, laugh_score")
        .in_("audio_segment_id", ids)
        .execute()
        .data
        or []
    )
    an_by_id = {a["audio_segment_id"]: a for a in analyses}

    items = []
    for s in segments:
        items.append({
            "id": s["id"],
            "started_at": s["started_at"],
            "ended_at": s["ended_at"],
            "duration_sec": s["duration_sec"],
            "transcript_status": s["transcript_status"],
            "analysis_status": s["analysis_status"],
            "speaker_match_score": s.get("speaker_match_score"),
            "source": (s.get("client_meta") or {}).get("source", "chunk"),
            "has_audio": bool(s.get("raw_audio_path")),
            "transcript": tx_by_id.get(s["id"]),
            "analysis": an_by_id.get(s["id"]),
            "created_at": s["created_at"],
        })

    return jsonify({"success": True, "data": {"items": items, "count": len(items)}})


@bp.get("/recordings/<segment_id>")
@require_auth
def get_recording(segment_id: str):
    """Full detail for one recording, incl. a short-lived signed URL if audio still exists."""
    admin = get_admin_client()
    seg_resp = (
        admin.table("audio_segments")
        .select("*")
        .eq("id", segment_id)
        .eq("user_id", g.user_id)
        .single()
        .execute()
    )
    segment = seg_resp.data
    if not segment:
        raise NotFoundError("Recording not found")

    transcript = (
        admin.table("transcripts").select("*").eq("audio_segment_id", segment_id).execute().data or []
    )
    analysis = (
        admin.table("segment_analysis").select("*").eq("audio_segment_id", segment_id).execute().data or []
    )
    terms = (
        admin.table("detected_terms").select("term, term_type, count, language")
        .eq("audio_segment_id", segment_id).execute().data or []
    )

    signed_url = None
    if segment.get("raw_audio_path"):
        try:
            signed_url = _storage.signed_url(segment["raw_audio_path"], expires_in_sec=600)
        except Exception as exc:
            log.warning("signed_url_failed", path=segment["raw_audio_path"], error=str(exc))

    return jsonify({
        "success": True,
        "data": {
            "segment": segment,
            "transcript": transcript[0] if transcript else None,
            "analysis": analysis[0] if analysis else None,
            "terms": terms,
            "audio_signed_url": signed_url,
        },
    })


@bp.get("/status")
@require_auth
def status():
    """Today's listening activity + per-status counts for the last 24h."""
    admin = get_admin_client()
    today = datetime.now(timezone.utc).date().isoformat()
    today_metrics = admin.table("daily_metrics").select("*").eq("user_id", g.user_id).eq("date", today).execute()

    counts = (
        admin.table("audio_segments")
        .select("analysis_status")
        .eq("user_id", g.user_id)
        .gte("created_at", today)
        .execute()
        .data
        or []
    )
    status_counts: dict[str, int] = {}
    for row in counts:
        key = row["analysis_status"]
        status_counts[key] = status_counts.get(key, 0) + 1

    return jsonify({
        "success": True,
        "data": {
            "listening": True,
            "today": today_metrics.data[0] if today_metrics.data else None,
            "status_counts": status_counts,
        },
    })


def _parse_ts(raw: str | None) -> datetime:
    if not raw:
        return datetime.now(timezone.utc)
    try:
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except ValueError:
        return datetime.now(timezone.utc)
