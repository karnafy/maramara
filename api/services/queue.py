"""Background job queue (RQ + Redis) with sync fallback for local dev."""
from __future__ import annotations

import base64
from functools import lru_cache

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


@lru_cache(maxsize=1)
def _get_queue():
    """Return an RQ Queue if Redis is reachable, else None (sync fallback)."""
    try:
        from redis import Redis
        from rq import Queue
        settings = get_settings()
        conn = Redis.from_url(settings.redis_url, socket_connect_timeout=2)
        conn.ping()
        log.info("queue_redis_ok")
        return Queue("maramara-segments", connection=conn)
    except Exception as exc:
        log.warning("queue_redis_unavailable_fallback_sync", error=str(exc))
        return None


def enqueue_segment_processing(segment_id: str, user_id: str, audio_bytes: bytes) -> str:
    b64 = base64.b64encode(audio_bytes).decode("ascii")
    q = _get_queue()
    if q is not None:
        job = q.enqueue(
            "workers.process_segment.run",
            segment_id, user_id, b64,
            job_timeout=600, result_ttl=3600,
        )
        log.info("segment_enqueued", segment_id=segment_id, job_id=job.id)
        return job.id
    from workers.process_segment import run as run_segment
    try:
        run_segment(segment_id, user_id, b64)
    except Exception:
        log.exception("sync_segment_failed", segment_id=segment_id)
    return "sync"


def enqueue_daily_aggregation(user_id: str, target_date: str) -> str:
    q = _get_queue()
    if q is not None:
        job = q.enqueue("workers.aggregate_daily.run", user_id, target_date, job_timeout=300)
        return job.id
    from workers.aggregate_daily import run as run_daily
    try:
        run_daily(user_id, target_date)
    except Exception:
        log.exception("sync_daily_failed", user=user_id, date=target_date)
    return "sync"


def enqueue_weekly_crewai(user_id: str, week_start: str) -> str:
    q = _get_queue()
    if q is not None:
        job = q.enqueue("workers.weekly_insights.run", user_id, week_start, job_timeout=1800)
        return job.id
    from workers.weekly_insights import run as run_weekly
    try:
        run_weekly(user_id, week_start)
    except Exception:
        log.exception("sync_weekly_failed", user=user_id, week=week_start)
    return "sync"
