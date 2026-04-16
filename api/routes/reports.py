"""Report routes: daily/weekly + PDF export."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import Blueprint, g, jsonify, render_template, request, send_file
from pydantic import BaseModel

from utils.auth import require_auth, require_role
from utils.errors import AppError
from services.pdf_report import generate_weekly_pdf
from db.supabase_client import get_admin_client

bp = Blueprint("reports", __name__)


class ExportRequest(BaseModel):
    patient_id: str | None = None  # therapist-initiated export
    week_start: date


@bp.get("/daily/<d>")
@require_auth
def daily_report(d: str):
    admin = get_admin_client()
    resp = admin.table("daily_metrics").select("*").eq("user_id", g.user_id).eq("date", d).execute()
    return jsonify({"success": True, "data": resp.data[0] if resp.data else None})


@bp.get("/weekly/<week_start>")
@require_auth
def weekly_report(week_start: str):
    admin = get_admin_client()
    resp = admin.table("weekly_metrics").select("*").eq("user_id", g.user_id).eq(
        "week_start", week_start
    ).execute()
    return jsonify({"success": True, "data": resp.data[0] if resp.data else None})


@bp.post("/export")
@require_role("therapist", "admin", "user")
def export_pdf():
    payload = ExportRequest(**request.get_json(force=True))
    target_user = payload.patient_id or g.user_id
    admin = get_admin_client()
    resp = admin.table("weekly_metrics").select("*").eq(
        "user_id", target_user
    ).eq("week_start", payload.week_start.isoformat()).execute()
    if not resp.data:
        raise AppError("No report for that week", status_code=404)

    pdf_bytes = generate_weekly_pdf(resp.data[0])
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=f"maramara-weekly-{payload.week_start.isoformat()}.pdf",
    )
