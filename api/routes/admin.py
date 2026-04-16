"""Admin routes: user management, system stats, moderation."""
from __future__ import annotations

from flask import Blueprint, g, jsonify, render_template, request

from utils.auth import require_role
from db.supabase_client import get_admin_client

bp = Blueprint("admin", __name__)


@bp.get("/")
@require_role("admin")
def dashboard():
    admin = get_admin_client()
    users = admin.table("profiles").select("id,role").execute()
    stats = {
        "total_users": len(users.data or []),
        "users": sum(1 for u in users.data or [] if u["role"] == "user"),
        "therapists": sum(1 for u in users.data or [] if u["role"] == "therapist"),
        "admins": sum(1 for u in users.data or [] if u["role"] == "admin"),
    }
    return render_template("admin/dashboard.html", stats=stats)


@bp.get("/users")
@require_role("admin")
def users_page():
    return render_template("admin/users.html")


@bp.get("/api/users")
@require_role("admin")
def api_users():
    admin = get_admin_client()
    resp = admin.table("profiles").select(
        "id,email,full_name,role,language,onboarding_completed,created_at,deleted_at"
    ).order("created_at", desc=True).execute()
    return jsonify({"success": True, "data": resp.data})


@bp.patch("/api/users/<user_id>/role")
@require_role("admin")
def change_role(user_id: str):
    body = request.get_json(force=True)
    new_role = body.get("role")
    if new_role not in ("user", "therapist", "admin"):
        return jsonify({"success": False, "error": {"message": "invalid role"}}), 422
    admin = get_admin_client()
    admin.table("profiles").update({"role": new_role}).eq("id", user_id).execute()
    return jsonify({"success": True})


@bp.delete("/api/users/<user_id>")
@require_role("admin")
def delete_user(user_id: str):
    """Soft-delete (GDPR). Hard delete requires a separate job."""
    admin = get_admin_client()
    from datetime import datetime, timezone
    admin.table("profiles").update({"deleted_at": datetime.now(timezone.utc).isoformat()}).eq(
        "id", user_id
    ).execute()
    return jsonify({"success": True})


@bp.get("/api/risk-flags")
@require_role("admin")
def risk_flags():
    admin = get_admin_client()
    resp = admin.table("risk_flags").select("*").eq("status", "open").order(
        "severity", desc=True
    ).execute()
    return jsonify({"success": True, "data": resp.data})
