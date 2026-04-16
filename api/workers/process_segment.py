"""Worker: transcribe + analyze a single segment.

Input: a storage path (e.g. "user-uuid/segment-uuid.wav").
The worker downloads the audio from Supabase Storage, runs Whisper,
inserts a transcript, runs Claude analysis, and updates status along
the way.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

from config import get_settings
from db.supabase_client import init_supabase_client, get_admin_client
from services.storage import StorageService
from services.transcription import TranscriptionService
from services.analysis import AnalysisService
from utils.logger import get_logger

log = get_logger(__name__)


def _looks_like_noise(text: str) -> bool:
    """Detect obvious Whisper hallucinations on silence/noise.

    Flags: empty, single repeated character ("אההההה"), or very short text
    dominated by one character class (typical of ambient-noise hallucination).
    """
    cleaned = (text or "").strip()
    if len(cleaned) < 3:
        return True
    # Collapse whitespace and count unique non-whitespace chars
    compact = re.sub(r"\s+", "", cleaned)
    if len(compact) >= 4 and len(set(compact)) <= 2:
        return True
    # Single-word outputs are usually hallucinated noise
    if len(cleaned.split()) < 2 and len(compact) < 8:
        return True
    return False


ALLOWED_ANALYSIS_COLUMNS = {
    "polarity", "intensity_score", "complaint_score", "curse_score",
    "calming_score", "self_talk_score", "self_criticism_score",
    "absolutism_score", "blame_score", "primary_topic", "secondary_topic",
    "trigger_detected", "trigger_description", "calming_detected",
    "calming_description", "cognitive_patterns", "tags", "llm_model_used",
    "laugh_score", "joy_score", "worry_score", "anger_score", "topic_mood",
}


def run(segment_id: str, user_id: str, audio_path: str) -> None:
    """Full pipeline for a single audio segment stored at `audio_path`."""
    settings = get_settings()
    init_supabase_client(settings)
    admin = get_admin_client()
    storage = StorageService()

    try:
        admin.table("audio_segments").update({
            "transcript_status": "processing",
        }).eq("id", segment_id).execute()

        audio_bytes = storage.download_audio(audio_path)

        ts = TranscriptionService()
        result = ts.transcribe(audio_bytes)
        transcript_text = result["text"]

        if not transcript_text or _looks_like_noise(transcript_text):
            log.info("transcript_noise_skipped", segment_id=segment_id,
                     preview=(transcript_text or "")[:40])
            admin.table("audio_segments").update({
                "transcript_status": "skipped",
                "analysis_status": "skipped",
            }).eq("id", segment_id).execute()
            return

        admin.table("transcripts").insert({
            "audio_segment_id": segment_id,
            "user_id": user_id,
            "transcript_text": transcript_text,
            "language": result["language"],
            "word_count": result["word_count"],
            "confidence": result["confidence"],
            "model_used": result["model_used"],
        }).execute()
        admin.table("audio_segments").update({
            "transcript_status": "completed",
            "analysis_status": "processing",
        }).eq("id", segment_id).execute()

        a = AnalysisService()
        analysis = a.analyze(transcript_text, language=result["language"])

        detected_terms = analysis.pop("detected_terms", [])
        analysis.pop("_error", None)
        filtered = {k: v for k, v in analysis.items() if k in ALLOWED_ANALYSIS_COLUMNS}

        admin.table("segment_analysis").insert({
            "audio_segment_id": segment_id,
            "user_id": user_id,
            **filtered,
        }).execute()

        for term in detected_terms:
            if isinstance(term, dict) and term.get("term") and term.get("type"):
                admin.table("detected_terms").insert({
                    "user_id": user_id,
                    "audio_segment_id": segment_id,
                    "term": term["term"][:200],
                    "term_type": term["type"],
                    "language": result["language"],
                }).execute()

        admin.table("audio_segments").update({
            "analysis_status": "completed",
        }).eq("id", segment_id).execute()

        # Optional: drop raw audio if retention disabled
        if not settings.retain_raw_audio:
            storage.delete_audio(audio_path)
            admin.table("audio_segments").update({
                "raw_audio_path": None,
            }).eq("id", segment_id).execute()

        from services.queue import enqueue_daily_aggregation
        today = datetime.now(timezone.utc).date().isoformat()
        enqueue_daily_aggregation(user_id, today)

        log.info("segment_processed", segment_id=segment_id)
    except Exception:
        log.exception("segment_process_failed", segment_id=segment_id)
        admin.table("audio_segments").update({
            "analysis_status": "failed",
        }).eq("id", segment_id).execute()
        raise
