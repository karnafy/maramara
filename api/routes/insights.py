"""Insight routes: terms, topics, triggers, calming patterns."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, request

from utils.auth import require_auth
from db.supabase_client import get_admin_client

bp = Blueprint("insights", __name__)


@bp.get("/terms")
@require_auth
def top_terms():
    """Top detected terms grouped by type."""
    term_type = request.args.get("type")
    limit = int(request.args.get("limit", 20))
    admin = get_admin_client()
    q = admin.table("detected_terms").select("term,term_type,count").eq("user_id", g.user_id)
    if term_type:
        q = q.eq("term_type", term_type)
    resp = q.order("count", desc=True).limit(limit).execute()
    return jsonify({"success": True, "data": resp.data})


@bp.get("/topics")
@require_auth
def top_topics():
    """Primary topic frequency from segment_analysis."""
    admin = get_admin_client()
    # Aggregate in Python (Supabase JS client doesn't do GROUP BY via rest; use rpc for prod).
    resp = admin.table("segment_analysis").select("primary_topic").eq("user_id", g.user_id).execute()
    counts: dict[str, int] = {}
    for row in resp.data or []:
        t = row.get("primary_topic")
        if t:
            counts[t] = counts.get(t, 0) + 1
    data = sorted(({"topic": k, "count": v} for k, v in counts.items()), key=lambda x: -x["count"])
    return jsonify({"success": True, "data": data[:20]})


@bp.get("/triggers")
@require_auth
def triggers():
    """Detected triggers over last 30 days."""
    admin = get_admin_client()
    resp = admin.table("segment_analysis").select(
        "primary_topic,trigger_description,intensity_score,created_at"
    ).eq("user_id", g.user_id).eq("trigger_detected", True).order(
        "created_at", desc=True
    ).limit(50).execute()
    return jsonify({"success": True, "data": resp.data})


@bp.get("/calming")
@require_auth
def calming():
    """Detected calming moments over last 30 days."""
    admin = get_admin_client()
    resp = admin.table("segment_analysis").select(
        "primary_topic,calming_description,intensity_score,created_at"
    ).eq("user_id", g.user_id).eq("calming_detected", True).order(
        "created_at", desc=True
    ).limit(50).execute()
    return jsonify({"success": True, "data": resp.data})


@bp.get("/weekly")
@require_auth
def weekly():
    """Latest weekly insight (CrewAI-generated)."""
    admin = get_admin_client()
    resp = admin.table("weekly_metrics").select("*").eq("user_id", g.user_id).order(
        "week_start", desc=True
    ).limit(1).execute()
    return jsonify({"success": True, "data": resp.data[0] if resp.data else None})


@bp.get("/live")
@require_auth
def live():
    """Live aggregations from segment_analysis (no CrewAI needed).

    Supports ?range=day|week|month|year (default: week).
    """
    from collections import Counter
    admin = get_admin_client()
    from datetime import datetime, timedelta, timezone

    window_days = {"day": 1, "week": 7, "month": 30, "year": 365}
    rng = (request.args.get("range") or "week").lower()
    if rng not in window_days:
        rng = "week"
    # PostgREST-safe timestamp: the "+00:00" suffix breaks URL encoding when sent
    # as a query-param filter (the "+" becomes a space). Strip microseconds and
    # use the Z suffix.
    since = (datetime.now(timezone.utc) - timedelta(days=window_days[rng])).replace(
        microsecond=0, tzinfo=None
    ).isoformat() + "Z"

    analyses = admin.table("segment_analysis").select(
        "polarity,intensity_score,complaint_score,curse_score,calming_score,"
        "self_criticism_score,primary_topic,secondary_topic,trigger_detected,"
        "trigger_description,calming_detected,calming_description,"
        "cognitive_patterns,tags,created_at"
    ).eq("user_id", g.user_id).gte("created_at", since).order(
        "created_at", desc=True
    ).execute()

    transcripts = admin.table("transcripts").select(
        "transcript_text,created_at,language,word_count"
    ).eq("user_id", g.user_id).gte("created_at", since).execute()

    try:
        segments = admin.table("audio_segments").select(
            "duration_sec,started_at"
        ).eq("user_id", g.user_id).gte("started_at", since).execute()
        seg_error = None
        seglist = segments.data or []
    except Exception as e:
        seg_error = f"{type(e).__name__}: {e}"
        seglist = []

    rows = analyses.data or []
    tlist = transcripts.data or []
    total_duration_sec = sum(float(s.get("duration_sec") or 0) for s in seglist)
    # Debug info exposed in response for troubleshooting; remove once stable.
    _debug = {
        "since": since,
        "user_id": g.user_id,
        "segments_fetched": len(seglist),
        "total_duration_sec": total_duration_sec,
        "seg_error": seg_error,
    }

    if not rows:
        return jsonify({"success": True, "data": {
            "segment_count": 0,
            "total_duration_sec": total_duration_sec,
            "total_words": 0,
            "_debug": _debug,
        }})

    polarity_counts = Counter(r["polarity"] for r in rows if r.get("polarity"))

    # Finer-grained split: positive segments are divided into "strong" vs "mild"
    # based on intensity_score (>=6 is strong). This gives us 5 categories that
    # map 1:1 to the 5 colored zones on the mood gauge.
    STRONG_INTENSITY = 6.0
    polarity_detailed: dict[str, int] = {
        "strong_negative": 0, "negative": 0, "neutral": 0,
        "mixed": 0, "positive": 0, "strong_positive": 0,
    }
    for r in rows:
        p = r.get("polarity")
        i = float(r.get("intensity_score") or 0)
        if p == "negative":
            key = "strong_negative" if i >= STRONG_INTENSITY else "negative"
        elif p == "positive":
            key = "strong_positive" if i >= STRONG_INTENSITY else "positive"
        elif p == "mixed":
            key = "mixed"
        else:
            key = "neutral"
        polarity_detailed[key] = polarity_detailed.get(key, 0) + 1
    topics = Counter(r["primary_topic"] for r in rows if r.get("primary_topic"))

    triggers = [
        {"topic": r.get("primary_topic"), "desc": r.get("trigger_description"), "when": r["created_at"], "intensity": r.get("intensity_score")}
        for r in rows if r.get("trigger_detected")
    ][:10]
    calming = [
        {"topic": r.get("primary_topic"), "desc": r.get("calming_description"), "when": r["created_at"]}
        for r in rows if r.get("calming_detected")
    ][:10]

    # Cognitive patterns
    cog = Counter()
    for r in rows:
        for p in (r.get("cognitive_patterns") or []):
            cog[p] += 1

    # Hourly intensity heatmap (kept for backwards compatibility)
    hourly: dict[int, list[float]] = {}
    for r in rows:
        try:
            h = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).hour
        except Exception:
            continue
        hourly.setdefault(h, []).append(r.get("intensity_score") or 0)
    hourly_avg = {h: sum(v) / len(v) for h, v in hourly.items()}

    # Range-aware intensity buckets: day→24 hours, week→7 days,
    # month→30 days, year→12 months. Each value is average intensity.
    HEB_DAYS = ['א', 'ב', 'ג', 'ד', 'ה', 'ו', 'ש']
    HEB_MONTHS = ['ינו', 'פבר', 'מרץ', 'אפר', 'מאי', 'יונ',
                  'יול', 'אוג', 'ספט', 'אוק', 'נוב', 'דצמ']
    now = datetime.now(timezone.utc)
    if rng == "day":
        buckets = [{"label": f"{h:02d}", "sum": 0.0, "n": 0} for h in range(24)]
        for r in rows:
            try:
                t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            except Exception:
                continue
            b = buckets[t.hour]
            b["sum"] += float(r.get("intensity_score") or 0)
            b["n"] += 1
    elif rng == "week":
        start = (now - timedelta(days=6)).date()
        buckets = []
        for i in range(7):
            d = start + timedelta(days=i)
            buckets.append({"date": d, "label": HEB_DAYS[(d.weekday() + 1) % 7],
                            "sum": 0.0, "n": 0})
        for r in rows:
            try:
                t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).date()
            except Exception:
                continue
            for b in buckets:
                if b["date"] == t:
                    b["sum"] += float(r.get("intensity_score") or 0)
                    b["n"] += 1
                    break
    elif rng == "month":
        start = (now - timedelta(days=29)).date()
        buckets = []
        for i in range(30):
            d = start + timedelta(days=i)
            label = f"{d.day}/{d.month}" if i % 5 == 0 or i == 29 else ""
            buckets.append({"date": d, "label": label, "sum": 0.0, "n": 0})
        for r in rows:
            try:
                t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).date()
            except Exception:
                continue
            for b in buckets:
                if b["date"] == t:
                    b["sum"] += float(r.get("intensity_score") or 0)
                    b["n"] += 1
                    break
    else:  # year
        buckets = []
        ym = now
        for i in range(12):
            delta_months = 11 - i
            y = ym.year
            m = ym.month - delta_months
            while m <= 0:
                m += 12
                y -= 1
            buckets.append({"ym": (y, m), "label": HEB_MONTHS[m - 1],
                            "sum": 0.0, "n": 0})
        for r in rows:
            try:
                t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            except Exception:
                continue
            for b in buckets:
                if b["ym"] == (t.year, t.month):
                    b["sum"] += float(r.get("intensity_score") or 0)
                    b["n"] += 1
                    break

    intensity_buckets = [
        {"label": b["label"],
         "value": (b["sum"] / b["n"]) if b["n"] else 0.0,
         "count": b["n"]}
        for b in buckets
    ]

    # Top tags
    tag_counts = Counter()
    for r in rows:
        for t in (r.get("tags") or []):
            if t:
                tag_counts[t] += 1

    total_words = sum(t.get("word_count", 0) or 0 for t in tlist)
    languages = Counter(t.get("language", "?") for t in tlist)

    self_critic_avg = (
        sum((r.get("self_criticism_score") or 0) for r in rows) / len(rows)
    ) if rows else 0
    intensity_avg = sum((r.get("intensity_score") or 0) for r in rows) / len(rows)

    return jsonify({"success": True, "data": {
        "range": rng,
        "segment_count": len(rows),
        "total_words": total_words,
        "languages": languages.most_common(),
        "polarity_distribution": dict(polarity_counts),
        "polarity_detailed": polarity_detailed,
        "total_duration_sec": total_duration_sec,
        "top_topics": topics.most_common(8),
        "triggers": triggers,
        "calming": calming,
        "cognitive_patterns": cog.most_common(),
        "hourly_intensity": hourly_avg,
        "intensity_buckets": intensity_buckets,
        "_debug": _debug,
        "top_tags": tag_counts.most_common(12),
        "self_criticism_avg": self_critic_avg,
        "intensity_avg": intensity_avg,
    }})


@bp.post("/generate-weekly")
@require_auth
def generate_weekly():
    """Manually trigger CrewAI weekly insights for the current user."""
    from datetime import date, timedelta
    from services.queue import enqueue_weekly_crewai
    week_start = (date.today() - timedelta(days=date.today().weekday())).isoformat()
    job_id = enqueue_weekly_crewai(g.user_id, week_start)
    return jsonify({"success": True, "data": {"job_id": job_id, "week_start": week_start}})
