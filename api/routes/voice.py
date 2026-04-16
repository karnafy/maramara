"""Voice enrollment routes: 3 guided recordings → voice embedding."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from services.speaker import SpeakerService
from utils.auth import require_auth
from utils.errors import AppError
from db.supabase_client import get_admin_client

bp = Blueprint("voice", __name__)
_speaker = SpeakerService()


@bp.post("/enroll/start")
@require_auth
def enroll_start():
    """Signal start of enrollment - clears any existing profile."""
    admin = get_admin_client()
    admin.table("voice_profiles").delete().eq("user_id", g.user_id).execute()
    return jsonify({
        "success": True,
        "data": {
            "instructions": [
                {"index": 1, "duration_sec": 10, "prompt_he": "ספר על יום רגיל שלך", "prompt_en": "Talk about a normal day"},
                {"index": 2, "duration_sec": 12, "prompt_he": "איזה מקום אתה הכי אוהב", "prompt_en": "Your favourite place"},
                {"index": 3, "duration_sec": 13, "prompt_he": "תאר תחושה שהרגשת השבוע", "prompt_en": "A feeling from this week"},
            ],
            "sample_rate": 16000,
        },
    })


@bp.post("/enroll/chunk")
@require_auth
def enroll_chunk():
    """Upload a single enrollment chunk (multipart form)."""
    if "audio" not in request.files:
        raise AppError("Missing 'audio' file", status_code=422)
    chunk_index = int(request.form.get("index", 0))
    audio_bytes = request.files["audio"].read()
    if not audio_bytes:
        raise AppError("Empty audio", status_code=422)
    # Cache chunks in memory via user context (simplified - in prod use Redis)
    _speaker.cache_enrollment_chunk(g.user_id, chunk_index, audio_bytes)
    return jsonify({"success": True, "data": {"index": chunk_index, "bytes": len(audio_bytes)}})


@bp.post("/enroll/complete")
@require_auth
def enroll_complete():
    """Finalize enrollment - combine chunks + extract embedding + store."""
    try:
        embedding, duration = _speaker.finalize_enrollment(g.user_id)
    except ValueError as e:
        raise AppError(str(e), status_code=422) from e

    admin = get_admin_client()
    admin.table("voice_profiles").upsert({
        "user_id": g.user_id,
        "embedding_vector": embedding.tolist() if hasattr(embedding, "tolist") else list(embedding),
        "sample_duration_sec": duration,
        "model_version": "speechbrain/spkrec-ecapa-voxceleb",
        "confidence_baseline": 1.0,
        "sample_count": 3,
    }, on_conflict="user_id").execute()

    admin.table("profiles").update({"onboarding_completed": True}).eq("id", g.user_id).execute()

    return jsonify({
        "success": True,
        "data": {"duration_sec": duration, "embedding_dims": len(embedding)},
    })


@bp.post("/retrain")
@require_auth
def retrain():
    """Re-enroll voice (increments retrained_count)."""
    admin = get_admin_client()
    admin.table("voice_profiles").update({
        "retrained_count": {"$increment": 1},
    }).eq("user_id", g.user_id).execute()
    return jsonify({"success": True, "data": {"message": "Retraining initiated. Start new enrollment."}})
