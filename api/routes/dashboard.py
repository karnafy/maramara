"""User dashboard routes (HTML + JSON)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, render_template, request

from utils.auth import require_auth, require_role
from db.supabase_client import get_admin_client

bp = Blueprint("dashboard", __name__)


# -------- HTML pages (user web view) --------

@bp.get("/")
@require_role("user")
def home():
    return render_template("user/home.html", user=g.user_id)


@bp.get("/timeline")
@require_role("user")
def timeline():
    return render_template("user/timeline.html")


@bp.get("/insights")
@require_role("user")
def insights_page():
    return render_template("user/insights.html")


@bp.get("/listen")
@require_role("user")
def listen_page():
    return render_template("user/listen.html")


@bp.get("/settings")
@require_role("user")
def settings_page():
    return render_template("user/settings.html")


@bp.get("/recordings")
@require_role("user")
def recordings_page():
    return render_template("user/recordings.html")


# -------- JSON API --------

@bp.get("/api/today")
@require_auth
def api_today():
    admin = get_admin_client()
    today = date.today().isoformat()
    metrics = admin.table("daily_metrics").select("*").eq("user_id", g.user_id).eq("date", today).execute()
    return jsonify({"success": True, "data": metrics.data[0] if metrics.data else {}})


@bp.get("/api/week")
@require_auth
def api_week():
    admin = get_admin_client()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    metrics = admin.table("daily_metrics").select("*").eq("user_id", g.user_id).gte(
        "date", week_ago
    ).order("date", desc=False).execute()
    return jsonify({"success": True, "data": metrics.data})


@bp.get("/api/segments")
@require_auth
def api_segments():
    """List user's recent audio segments with transcript + analysis."""
    limit = min(int(request.args.get("limit", 50)), 200)
    admin = get_admin_client()

    segments = admin.table("audio_segments").select(
        "id,started_at,ended_at,duration_sec,speech_detected,"
        "speaker_match_score,matched_to_user,transcript_status,analysis_status"
    ).eq("user_id", g.user_id).order("started_at", desc=True).limit(limit).execute()

    if not segments.data:
        return jsonify({"success": True, "data": []})

    seg_ids = [s["id"] for s in segments.data]

    transcripts = admin.table("transcripts").select(
        "audio_segment_id,transcript_text,language,word_count,confidence"
    ).in_("audio_segment_id", seg_ids).execute()
    tmap = {t["audio_segment_id"]: t for t in (transcripts.data or [])}

    analyses = admin.table("segment_analysis").select(
        "audio_segment_id,polarity,intensity_score,primary_topic,"
        "trigger_detected,trigger_description,calming_detected,"
        "calming_description,tags"
    ).in_("audio_segment_id", seg_ids).execute()
    amap = {a["audio_segment_id"]: a for a in (analyses.data or [])}

    merged = []
    for s in segments.data:
        merged.append({
            **s,
            "transcript": tmap.get(s["id"]),
            "analysis": amap.get(s["id"]),
        })
    return jsonify({"success": True, "data": merged})


@bp.get("/api/timeline")
@require_auth
def api_timeline():
    """Hourly emotional timeline for a given date."""
    target_date = request.args.get("date", date.today().isoformat())
    admin = get_admin_client()
    segments = admin.table("segment_analysis").select(
        "created_at,polarity,intensity_score,primary_topic,trigger_detected,calming_detected"
    ).eq("user_id", g.user_id).gte(
        "created_at", f"{target_date}T00:00:00"
    ).lt(
        "created_at", f"{target_date}T23:59:59"
    ).order("created_at").execute()
    return jsonify({"success": True, "data": segments.data})
