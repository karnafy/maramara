"""Patient → Therapist connect flow via signed shareable links.

The patient generates a signed token from their user_id, shares the URL
(WhatsApp / SMS / email). When a therapist opens the link and accepts,
a `therapist_patient_links` row is created with status='active'.

Tokens are signed with the Flask SECRET_KEY via itsdangerous and expire
after 30 days — no DB storage needed for pending invites.
"""
from __future__ import annotations

from datetime import datetime, timezone

from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    render_template,
    request,
    session,
)
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from db.supabase_client import get_admin_client
from utils.auth import require_auth, require_role
from utils.errors import AppError

bp = Blueprint("connect", __name__)

_SALT = "patient-share-v1"
_MAX_AGE_SECONDS = 60 * 60 * 24 * 30  # 30 days


def _serializer() -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt=_SALT)


# ---------------------------------------------------------------------------
# Patient: generate a share URL
# ---------------------------------------------------------------------------

@bp.post("/dashboard/api/share-link")
@require_auth
def create_share_link():
    """Patient generates a signed token for their user_id."""
    token = _serializer().dumps(g.user_id)
    base = request.host_url.rstrip("/")
    return jsonify({
        "success": True,
        "data": {
            "token": token,
            "url": f"{base}/connect/{token}",
            "expires_in_days": _MAX_AGE_SECONDS // (60 * 60 * 24),
        },
    })


# ---------------------------------------------------------------------------
# Shared: landing page when therapist/anyone opens the link
# ---------------------------------------------------------------------------

@bp.get("/connect/<token>")
def connect_landing(token: str):
    try:
        patient_id = _serializer().loads(token, max_age=_MAX_AGE_SECONDS)
    except SignatureExpired:
        return render_template("connect/landing.html", state="expired"), 410
    except BadSignature:
        return render_template("connect/landing.html", state="invalid"), 400

    admin = get_admin_client()
    patient_resp = (
        admin.table("profiles").select("id,full_name,email").eq("id", patient_id).execute()
    )
    patient = patient_resp.data[0] if patient_resp.data else None
    if not patient:
        return render_template("connect/landing.html", state="invalid"), 404

    user = session.get("user")
    if not user:
        return render_template(
            "connect/landing.html",
            state="needs_login",
            patient=patient,
            token=token,
        )

    if user["id"] == patient_id:
        return render_template(
            "connect/landing.html",
            state="self_view",
            patient=patient,
            share_url=request.url,
        )

    if user.get("role") not in ("therapist", "admin"):
        return render_template(
            "connect/landing.html",
            state="wrong_role",
            patient=patient,
            user=user,
        )

    existing = (
        admin.table("therapist_patient_links")
        .select("status")
        .eq("therapist_id", user["id"])
        .eq("patient_id", patient_id)
        .execute()
    )
    already_active = bool(existing.data) and existing.data[0]["status"] == "active"

    return render_template(
        "connect/landing.html",
        state="already_active" if already_active else "ready_to_accept",
        patient=patient,
        token=token,
        user=user,
    )


# ---------------------------------------------------------------------------
# Therapist: accept the link
# ---------------------------------------------------------------------------

@bp.post("/connect/<token>/accept")
@require_role("therapist", "admin")
def connect_accept(token: str):
    try:
        patient_id = _serializer().loads(token, max_age=_MAX_AGE_SECONDS)
    except (BadSignature, SignatureExpired):
        raise AppError("הקישור פג תוקף או לא תקין", status_code=400)

    if g.user_id == patient_id:
        raise AppError("לא ניתן לקבל קישור שיתוף שלך־עצמך", status_code=400)

    admin = get_admin_client()
    admin.table("therapist_patient_links").upsert(
        {
            "therapist_id": g.user_id,
            "patient_id": patient_id,
            "status": "active",
            "invite_token": token[:60],
            "accepted_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="therapist_id,patient_id",
    ).execute()

    return jsonify({"success": True, "data": {"redirect": "/therapist/"}})
