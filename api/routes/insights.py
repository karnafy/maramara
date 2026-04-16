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
    """Live aggregations from segment_analysis (no CrewAI needed)."""
    from collections import Counter
    admin = get_admin_client()
    from datetime import datetime, timedelta, timezone
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

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

    rows = analyses.data or []
    tlist = transcripts.data or []

    if not rows:
        return jsonify({"success": True, "data": {
            "segment_count": 0,
            "total_words": 0,
        }})

    polarity_counts = Counter(r["polarity"] for r in rows if r.get("polarity"))
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

    # Hourly intensity heatmap
    hourly: dict[int, list[float]] = {}
    for r in rows:
        try:
            h = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).hour
        except Exception:
            continue
        hourly.setdefault(h, []).append(r.get("intensity_score") or 0)
    hourly_avg = {h: sum(v) / len(v) for h, v in hourly.items()}

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
        "segment_count": len(rows),
        "total_words": total_words,
        "languages": languages.most_common(),
        "polarity_distribution": dict(polarity_counts),
        "top_topics": topics.most_common(8),
        "triggers": triggers,
        "calming": calming,
        "cognitive_patterns": cog.most_common(),
        "hourly_intensity": hourly_avg,
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
