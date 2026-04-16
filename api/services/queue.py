"""Background job queue (RQ + Redis)."""
from __future__ import annotations

import base64
from functools import lru_cache

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_queue():
    from redis import Redis
    from rq import Queue
    settings = get_settings()
    conn = Redis.from_url(settings.redis_url)
    return Queue("maramara-segments", connection=conn)


def enqueue_segment_processing(segment_id: str, user_id: str, audio_bytes: bytes) -> str:
    """Queue full pipeline: transcription + analysis + daily aggregation."""
    q = _get_queue()
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    job = q.enqueue(
        "workers.process_segment.run",
        segment_id,
        user_id,
        b64,
        job_timeout=600,
        result_ttl=3600,
    )
    log.info("segment_enqueued", segment_id=segment_id, job_id=job.id)
    return job.id


def enqueue_daily_aggregation(user_id: str, target_date: str) -> str:
    q = _get_queue()
    job = q.enqueue("workers.aggregate_daily.run", user_id, target_date, job_timeout=300)
    return job.id


def enqueue_weekly_crewai(user_id: str, week_start: str) -> str:
    q = _get_queue()
    job = q.enqueue("workers.weekly_insights.run", user_id, week_start, job_timeout=1800)
    return job.id
