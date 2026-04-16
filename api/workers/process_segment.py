"""Worker: transcribe + analyze a single segment."""
from __future__ import annotations

import base64
from datetime import datetime, timezone

from config import get_settings
from db.supabase_client import init_supabase_client, get_admin_client
from services.transcription import TranscriptionService
from services.analysis import AnalysisService
from utils.logger import get_logger

log = get_logger(__name__)


def run(segment_id: str, user_id: str, audio_b64: str) -> None:
    """Full pipeline for a single audio segment."""
    settings = get_settings()
    init_supabase_client(settings)
    admin = get_admin_client()

    try:
        admin.table("audio_segments").update({
            "transcript_status": "processing",
        }).eq("id", segment_id).execute()

        audio_bytes = base64.b64decode(audio_b64)

        # 1. Transcription
        ts = TranscriptionService()
        result = ts.transcribe(audio_bytes)
        transcript_text = result["text"]

        if not transcript_text:
            log.info("empty_transcript", segment_id=segment_id)
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

        # 2. Analysis (LLM)
        a = AnalysisService()
        analysis = a.analyze(transcript_text, language=result["language"])

        detected_terms = analysis.pop("detected_terms", [])
        analysis.pop("_error", None)

        admin.table("segment_analysis").insert({
            "audio_segment_id": segment_id,
            "user_id": user_id,
            **analysis,
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

        # 3. Enqueue daily aggregation
        from services.queue import enqueue_daily_aggregation
        today = datetime.now(timezone.utc).date().isoformat()
        enqueue_daily_aggregation(user_id, today)

        log.info("segment_processed", segment_id=segment_id)
    except Exception as e:
        log.exception("segment_process_failed", segment_id=segment_id)
        admin.table("audio_segments").update({
            "analysis_status": "failed",
        }).eq("id", segment_id).execute()
        raise
