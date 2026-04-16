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
