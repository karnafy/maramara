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
