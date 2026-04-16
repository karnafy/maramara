"""Audio ingest routes: receive mobile chunks → VAD → speaker → enqueue."""
from __future__ import annotations

import uuid
from datetime import datetime, timezone

from flask import Blueprint, g, jsonify, request

from services.vad import VADService
from services.speaker import SpeakerService
from services.queue import enqueue_segment_processing
from utils.auth import require_auth
from utils.errors import AppError
from utils.logger import get_logger
from db.supabase_client import get_admin_client

log = get_logger(__name__)
bp = Blueprint("audio", __name__)

_vad = VADService()
_speaker = SpeakerService()


@bp.post("/chunk")
@require_auth
def upload_chunk():
    """Receive a single audio chunk from mobile.

    Pipeline (fast path on request thread):
      1. VAD - skip if no speech
      2. Speaker verify - skip if not the enrolled user
      3. Create audio_segments row
      4. Enqueue transcription + analysis job
    """
    if "audio" not in request.files:
        raise AppError("Missing 'audio' file", status_code=422)

    started_at_str = request.form.get("started_at")
    duration_sec = float(request.form.get("duration_sec", 10.0))
    started_at = datetime.fromisoformat(started_at_str) if started_at_str else datetime.now(timezone.utc)
    ended_at = datetime.fromisoformat(request.form.get("ended_at")) if request.form.get("ended_at") else datetime.now(timezone.utc)

    audio_bytes = request.files["audio"].read()
    if not audio_bytes:
        raise AppError("Empty audio", status_code=422)

    # Step 1: VAD
    speech_detected, _ = _vad.detect(audio_bytes)
    if not speech_detected:
        return jsonify({"success": True, "data": {"skipped": "no_speech"}})

    # Step 2: Speaker verify (requires prior enrollment)
    admin = get_admin_client()
    voice = admin.table("voice_profiles").select("embedding_vector").eq("user_id", g.user_id).execute()
    if voice.data:
        enrolled_emb = voice.data[0]["embedding_vector"]
        chunk_emb = _speaker.extract_embedding(audio_bytes)
        similarity = _speaker.cosine_similarity(enrolled_emb, chunk_emb)
    else:
        # MVP mode: no enrollment yet → auto-accept (trust the JWT).
        # Full ML speaker verification re-enabled after onboarding.
        log.info("no_voice_profile_auto_accept", user_id=g.user_id)
        similarity = 1.0

    segment_id = str(uuid.uuid4())
    matched = similarity >= _speaker.threshold

    # Step 3: Create audio_segments row
    admin.table("audio_segments").insert({
        "id": segment_id,
        "user_id": g.user_id,
        "started_at": started_at.isoformat(),
        "ended_at": ended_at.isoformat(),
        "duration_sec": duration_sec,
        "speech_detected": True,
        "speaker_match_score": float(similarity),
        "matched_to_user": matched,
        "transcript_status": "pending" if matched else "skipped",
        "analysis_status": "pending" if matched else "skipped",
    }).execute()

    if not matched:
        log.info("speaker_mismatch", user_id=g.user_id, similarity=similarity)
        return jsonify({"success": True, "data": {"skipped": "speaker_mismatch", "similarity": float(similarity)}})

    # Step 4: Enqueue background processing
    enqueue_segment_processing(segment_id=segment_id, user_id=g.user_id, audio_bytes=audio_bytes)

    return jsonify({
        "success": True,
        "data": {"segment_id": segment_id, "similarity": float(similarity), "status": "queued"},
    })


@bp.get("/status")
@require_auth
def status():
    """Get current listening status + today's stats."""
    admin = get_admin_client()
    today = datetime.now(timezone.utc).date().isoformat()
    today_metrics = admin.table("daily_metrics").select("*").eq("user_id", g.user_id).eq("date", today).execute()

    return jsonify({
        "success": True,
        "data": {
            "listening": True,
            "today": today_metrics.data[0] if today_metrics.data else None,
        },
    })
