"""Worker: aggregate a single user's daily metrics."""
from __future__ import annotations

from datetime import datetime
from collections import Counter

from config import get_settings
from db.supabase_client import init_supabase_client, get_admin_client
from utils.logger import get_logger

log = get_logger(__name__)


def run(user_id: str, date_str: str) -> None:
    settings = get_settings()
    init_supabase_client(settings)
    admin = get_admin_client()

    start_iso = f"{date_str}T00:00:00+00:00"
    end_iso = f"{date_str}T23:59:59+00:00"

    analyses = admin.table("segment_analysis").select(
        "polarity,intensity_score,complaint_score,curse_score,calming_score,"
        "self_criticism_score,primary_topic,trigger_detected,calming_detected,created_at"
    ).eq("user_id", user_id).gte("created_at", start_iso).lte(
        "created_at", end_iso
    ).execute()

    rows = analyses.data or []
    if not rows:
        return

    positive = sum(1 for r in rows if r["polarity"] == "positive")
    negative = sum(1 for r in rows if r["polarity"] == "negative")
    curse_count = sum(1 for r in rows if (r["curse_score"] or 0) > 0.5)
    complaint_count = sum(1 for r in rows if (r["complaint_score"] or 0) > 0.5)
    calming_count = sum(1 for r in rows if r["calming_detected"])
    self_criticism_count = sum(1 for r in rows if (r["self_criticism_score"] or 0) > 0.5)
    intensity_avg = sum(r["intensity_score"] or 0 for r in rows) / len(rows)

    # Polarity score: positive count - negative count, normalized
    polarity_score = (positive - negative) / max(len(rows), 1)

    trigger_topics = [r["primary_topic"] for r in rows if r["trigger_detected"] and r["primary_topic"]]
    calming_topics = [r["primary_topic"] for r in rows if r["calming_detected"] and r["primary_topic"]]
    top_trigger = Counter(trigger_topics).most_common(1)
    top_calming = Counter(calming_topics).most_common(1)

    # Peak frustration hour
    hour_intensity: dict[int, list[float]] = {}
    for r in rows:
        try:
            h = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).hour
        except Exception:
            continue
        hour_intensity.setdefault(h, []).append(r["intensity_score"] or 0)
    peak_hour = None
    if hour_intensity:
        peak_hour = max(hour_intensity.items(), key=lambda kv: sum(kv[1]) / len(kv[1]))[0]

    admin.table("daily_metrics").upsert({
        "user_id": user_id,
        "date": date_str,
        "positive_count": positive,
        "negative_count": negative,
        "curse_count": curse_count,
        "complaint_count": complaint_count,
        "calming_count": calming_count,
        "self_criticism_count": self_criticism_count,
        "polarity_score": polarity_score,
        "intensity_avg": intensity_avg,
        "peak_frustration_hour": peak_hour,
        "top_trigger_topic": top_trigger[0][0] if top_trigger else None,
        "top_calming_topic": top_calming[0][0] if top_calming else None,
        "total_segments": len(rows),
    }, on_conflict="user_id,date").execute()

    log.info("daily_aggregated", user_id=user_id, date=date_str, segments=len(rows))
