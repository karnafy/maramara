"""Therapist routes: invite patients, view overview, add notes."""
from __future__ import annotations

import secrets
from datetime import date, datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, render_template, request
from pydantic import BaseModel, EmailStr, Field

from utils.auth import require_role
from utils.errors import AppError, ForbiddenError, NotFoundError
from db.supabase_client import get_admin_client

bp = Blueprint("therapist", __name__)


class InviteRequest(BaseModel):
    patient_email: EmailStr


class NoteRequest(BaseModel):
    patient_id: str
    title: str | None = None
    body: str = Field(min_length=1, max_length=10000)
    tags: list[str] = []
    is_intervention: bool = False
    note_date: date | None = None


# -------- HTML pages --------

@bp.get("/")
@require_role("therapist", "admin")
def overview():
    admin = get_admin_client()
    links = admin.table("therapist_patient_links").select(
        "id,status,accepted_at,patient:profiles!patient_id(id,full_name,email,language)"
    ).eq("therapist_id", g.user_id).order("accepted_at", desc=True).execute()
    return render_template("therapist/overview.html", links=links.data or [])


@bp.get("/patients")
@require_role("therapist", "admin")
def patients_page():
    return render_template("therapist/patients.html")


@bp.get("/patients/<patient_id>")
@require_role("therapist", "admin")
def patient_detail(patient_id: str):
    _assert_access(g.user_id, patient_id)
    return render_template("therapist/patient_detail.html", patient_id=patient_id)


@bp.get("/reports")
@require_role("therapist", "admin")
def reports_page():
    return render_template("therapist/reports.html")


@bp.get("/notes")
@require_role("therapist", "admin")
def notes_page():
    return render_template("therapist/notes.html")


# -------- JSON API --------

@bp.post("/api/invite")
@require_role("therapist", "admin")
def api_invite():
    """Invite a patient by email."""
    payload = InviteRequest(**request.get_json(force=True))
    admin = get_admin_client()

    # Find or create patient placeholder profile
    existing = admin.table("profiles").select("id").eq("email", payload.patient_email).execute()
    if not existing.data:
        raise AppError(
            f"No user registered with {payload.patient_email}. Ask them to sign up first, then invite.",
            status_code=404,
        )
    patient_id = existing.data[0]["id"]

    invite_token = secrets.token_urlsafe(32)
    admin.table("therapist_patient_links").upsert({
        "therapist_id": g.user_id,
        "patient_id": patient_id,
        "status": "pending",
        "invite_token": invite_token,
    }, on_conflict="therapist_id,patient_id").execute()

    return jsonify({
        "success": True,
        "data": {"patient_id": patient_id, "invite_token": invite_token},
    })


@bp.get("/api/patients")
@require_role("therapist", "admin")
def api_patients():
    admin = get_admin_client()
    links = admin.table("therapist_patient_links").select(
        "id,status,accepted_at,patient:profiles!patient_id(id,full_name,email,language)"
    ).eq("therapist_id", g.user_id).execute()
    return jsonify({"success": True, "data": links.data or []})


@bp.get("/api/patients/gallery")
@require_role("therapist", "admin")
def api_patients_gallery():
    """Live gallery: each active patient + mood score + last activity."""
    from collections import Counter

    admin = get_admin_client()
    since = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    links_resp = (
        admin.table("therapist_patient_links")
        .select("patient:profiles!patient_id(id,full_name,email)")
        .eq("therapist_id", g.user_id)
        .eq("status", "active")
        .execute()
    )
    patients = [l["patient"] for l in (links_resp.data or []) if l.get("patient")]
    if not patients:
        return jsonify({"success": True, "data": []})

    patient_ids = [p["id"] for p in patients]

    analyses = (
        admin.table("segment_analysis")
        .select("user_id,polarity,intensity_score,created_at")
        .in_("user_id", patient_ids)
        .gte("created_at", since)
        .execute()
        .data
        or []
    )

    latest = (
        admin.table("audio_segments")
        .select("user_id,started_at")
        .in_("user_id", patient_ids)
        .order("started_at", desc=True)
        .limit(500)
        .execute()
        .data
        or []
    )

    # Aggregate per patient
    per_patient: dict[str, dict] = {}
    for pid in patient_ids:
        per_patient[pid] = {
            "pos": 0, "neg": 0, "neu": 0, "mix": 0,
            "segments_7d": 0,
            "intensity_sum": 0.0,
            "intensity_n": 0,
            "last_active": None,
        }
    for a in analyses:
        pid = a.get("user_id")
        if pid not in per_patient:
            continue
        b = per_patient[pid]
        b["segments_7d"] += 1
        p = a.get("polarity")
        if p == "positive": b["pos"] += 1
        elif p == "negative": b["neg"] += 1
        elif p == "neutral": b["neu"] += 1
        elif p == "mixed": b["mix"] += 1
        if a.get("intensity_score"):
            b["intensity_sum"] += float(a["intensity_score"])
            b["intensity_n"] += 1
    for row in latest:
        pid = row.get("user_id")
        if pid in per_patient and per_patient[pid]["last_active"] is None:
            per_patient[pid]["last_active"] = row.get("started_at")

    def mood(b):
        total = b["pos"] + b["neg"] + b["neu"] + b["mix"]
        if not total:
            return 0.0
        return (b["pos"] - b["neg"]) / total

    gallery = []
    for p in patients:
        b = per_patient[p["id"]]
        total = b["pos"] + b["neg"] + b["neu"] + b["mix"]
        gallery.append({
            "id": p["id"],
            "full_name": p.get("full_name") or p.get("email"),
            "email": p.get("email"),
            "mood_score": round(mood(b), 3),
            "segments_7d": b["segments_7d"],
            "intensity_avg": round(b["intensity_sum"] / b["intensity_n"], 2) if b["intensity_n"] else 0.0,
            "polarity": {"positive": b["pos"], "negative": b["neg"], "neutral": b["neu"], "mixed": b["mix"]},
            "total_polarity": total,
            "last_active": b["last_active"],
        })

    return jsonify({"success": True, "data": gallery})


@bp.get("/api/patients/<patient_id>/overview")
@require_role("therapist", "admin")
def api_patient_overview(patient_id: str):
    _assert_access(g.user_id, patient_id)
    _log_access(g.user_id, patient_id, "view_overview")
    admin = get_admin_client()
    week_ago = (datetime.now(timezone.utc) - timedelta(days=7)).date().isoformat()
    daily = admin.table("daily_metrics").select("*").eq("user_id", patient_id).gte(
        "date", week_ago
    ).order("date").execute()
    latest_weekly = admin.table("weekly_metrics").select("*").eq("user_id", patient_id).order(
        "week_start", desc=True
    ).limit(1).execute()
    return jsonify({
        "success": True,
        "data": {
            "daily": daily.data,
            "latest_weekly": latest_weekly.data[0] if latest_weekly.data else None,
        },
    })


@bp.post("/api/notes")
@require_role("therapist", "admin")
def api_add_note():
    payload = NoteRequest(**request.get_json(force=True))
    _assert_access(g.user_id, payload.patient_id)
    admin = get_admin_client()
    resp = admin.table("therapist_notes").insert({
        "therapist_id": g.user_id,
        "patient_id": payload.patient_id,
        "title": payload.title,
        "body": payload.body,
        "tags": payload.tags,
        "is_intervention_marker": payload.is_intervention,
        "note_date": (payload.note_date or date.today()).isoformat(),
    }).execute()
    _log_access(g.user_id, payload.patient_id, "add_note")
    return jsonify({"success": True, "data": resp.data[0] if resp.data else None}), 201


# -------- Helpers --------

def _assert_access(therapist_id: str, patient_id: str) -> None:
    admin = get_admin_client()
    link = admin.table("therapist_patient_links").select("status").eq(
        "therapist_id", therapist_id
    ).eq("patient_id", patient_id).execute()
    if not link.data:
        raise NotFoundError("No link to this patient")
    if link.data[0]["status"] != "active":
        raise ForbiddenError("Patient has not accepted the invitation")


def _log_access(therapist_id: str, patient_id: str, action: str) -> None:
    admin = get_admin_client()
    admin.table("therapist_access_log").insert({
        "therapist_id": therapist_id,
        "patient_id": patient_id,
        "action": action,
        "ip_address": request.remote_addr,
        "user_agent": request.headers.get("User-Agent", "")[:500],
    }).execute()
