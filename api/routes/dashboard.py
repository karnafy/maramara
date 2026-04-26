"""User dashboard routes (HTML + JSON)."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import csv
import io

from flask import Blueprint, Response, g, jsonify, render_template, request, send_file

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
    """Bucketed emotional timeline across one of 5 ranges.

    range = hour | day | week | month | year (defaults to day)
    """
    range_param = (request.args.get("range") or "day").lower()
    if range_param not in {"hour", "day", "week", "month", "year"}:
        range_param = "day"
    admin = get_admin_client()
    now = datetime.now(timezone.utc)
    series = _build_chart_series(admin, g.user_id, range_param, now)
    return jsonify({"success": True, "data": {"range": range_param, "series": series}})


@bp.get("/api/export")
@require_auth
def api_export():
    """Download all user segments + transcripts + analyses as a CSV file."""
    admin = get_admin_client()

    segments = (
        admin.table("audio_segments")
        .select("id,started_at,ended_at,duration_sec,transcript_status,analysis_status,speaker_match_score")
        .eq("user_id", g.user_id)
        .order("started_at")
        .execute()
        .data
        or []
    )
    if not segments:
        return Response("started_at,transcript,polarity,intensity\n", mimetype="text/csv")

    ids = [s["id"] for s in segments]
    tx = {
        row["audio_segment_id"]: row
        for row in (
            admin.table("transcripts")
            .select("audio_segment_id,transcript_text,language,word_count")
            .in_("audio_segment_id", ids)
            .execute()
            .data
            or []
        )
    }
    an = {
        row["audio_segment_id"]: row
        for row in (
            admin.table("segment_analysis")
            .select("audio_segment_id,polarity,intensity_score,primary_topic,"
                    "trigger_detected,trigger_description,calming_detected,calming_description,"
                    "self_criticism_score,complaint_score,joy_score,worry_score,anger_score")
            .in_("audio_segment_id", ids)
            .execute()
            .data
            or []
        )
    }

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "started_at", "ended_at", "duration_sec", "transcript_status", "analysis_status",
        "language", "word_count", "transcript_text",
        "polarity", "intensity_score", "primary_topic",
        "trigger_detected", "trigger_description",
        "calming_detected", "calming_description",
        "self_criticism_score", "complaint_score",
        "joy_score", "worry_score", "anger_score",
    ])
    for s in segments:
        t = tx.get(s["id"], {})
        a = an.get(s["id"], {})
        writer.writerow([
            s.get("started_at", ""),
            s.get("ended_at", ""),
            s.get("duration_sec", ""),
            s.get("transcript_status", ""),
            s.get("analysis_status", ""),
            t.get("language", ""),
            t.get("word_count", ""),
            (t.get("transcript_text") or "").replace("\n", " ").strip(),
            a.get("polarity", ""),
            a.get("intensity_score", ""),
            a.get("primary_topic", ""),
            a.get("trigger_detected", ""),
            (a.get("trigger_description") or "").replace("\n", " ").strip(),
            a.get("calming_detected", ""),
            (a.get("calming_description") or "").replace("\n", " ").strip(),
            a.get("self_criticism_score", ""),
            a.get("complaint_score", ""),
            a.get("joy_score", ""),
            a.get("worry_score", ""),
            a.get("anger_score", ""),
        ])

    csv_text = "﻿" + buf.getvalue()  # BOM for Excel to detect UTF-8 with Hebrew
    filename = f"maramara-export-{date.today().isoformat()}.csv"
    return Response(
        csv_text,
        mimetype="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@bp.get("/api/my-connections")
@require_auth
def api_my_connections():
    """Return people linked to current user + their live mood score.

    Role-aware:
      - therapist/admin → list of linked patients (reuses mood aggregation)
      - user            → list of linked therapists + prompt to share link
    """
    admin = get_admin_client()
    profile = (
        admin.table("profiles").select("role").eq("id", g.user_id).execute()
    )
    role = (profile.data[0].get("role") if profile.data else "user") or "user"

    if role in ("therapist", "admin"):
        return _connections_for_therapist(admin)
    return _connections_for_user(admin)


def _connections_for_therapist(admin) -> tuple:
    """Same shape as /therapist/api/patients/gallery but callable from dashboard."""
    from datetime import timedelta

    window_start = (datetime.now(timezone.utc) - timedelta(days=7)).isoformat()

    links_resp = (
        admin.table("therapist_patient_links")
        .select("patient:profiles!patient_id(id,full_name,email)")
        .eq("therapist_id", g.user_id)
        .eq("status", "active")
        .execute()
    )
    patients = [l["patient"] for l in (links_resp.data or []) if l.get("patient")]
    if not patients:
        return jsonify({"success": True, "data": {"role": "therapist", "connections": []}})

    ids = [p["id"] for p in patients]
    analyses = (
        admin.table("segment_analysis")
        .select("user_id,polarity,intensity_score,created_at")
        .in_("user_id", ids)
        .gte("created_at", window_start)
        .execute()
        .data
        or []
    )
    latest = (
        admin.table("audio_segments")
        .select("user_id,started_at")
        .in_("user_id", ids)
        .order("started_at", desc=True)
        .limit(200)
        .execute()
        .data
        or []
    )

    buckets: dict[str, dict] = {
        pid: {"pos": 0, "neg": 0, "neu": 0, "mix": 0,
              "segments": 0, "last_active": None} for pid in ids
    }
    for a in analyses:
        b = buckets.get(a.get("user_id"))
        if not b:
            continue
        b["segments"] += 1
        p = a.get("polarity")
        if p == "positive": b["pos"] += 1
        elif p == "negative": b["neg"] += 1
        elif p == "neutral": b["neu"] += 1
        elif p == "mixed": b["mix"] += 1
    for row in latest:
        b = buckets.get(row.get("user_id"))
        if b and b["last_active"] is None:
            b["last_active"] = row.get("started_at")

    out = []
    for p in patients:
        b = buckets[p["id"]]
        total = b["pos"] + b["neg"] + b["neu"] + b["mix"]
        mood = (b["pos"] - b["neg"]) / total if total else 0.0
        out.append({
            "id": p["id"],
            "kind": "patient",
            "full_name": p.get("full_name") or p.get("email"),
            "email": p.get("email"),
            "mood_score": round(mood, 3),
            "segments_7d": b["segments"],
            "last_active": b["last_active"],
            "total_polarity": total,
            "open_url": f"/therapist/patients/{p['id']}",
        })
    return jsonify({"success": True, "data": {"role": "therapist", "connections": out}})


def _connections_for_user(admin) -> tuple:
    """A regular user sees their linked therapists (simpler — no mood gauge)."""
    links = (
        admin.table("therapist_patient_links")
        .select("status,accepted_at,therapist:profiles!therapist_id(id,full_name,email)")
        .eq("patient_id", g.user_id)
        .eq("status", "active")
        .execute()
    )
    out = []
    for l in links.data or []:
        t = l.get("therapist")
        if not t:
            continue
        out.append({
            "id": t["id"],
            "kind": "therapist",
            "full_name": t.get("full_name") or t.get("email"),
            "email": t.get("email"),
            "connected_since": l.get("accepted_at"),
        })
    return jsonify({"success": True, "data": {"role": "user", "connections": out}})


@bp.get("/api/export/pdf")
@require_auth
def api_export_pdf():
    """Designed personal PDF: 30-day metrics + SVG charts + Claude narrative (Hebrew)."""
    from io import BytesIO
    from services.personal_pdf import render_personal_pdf

    admin = get_admin_client()
    user_email = getattr(g, "user_email", None)
    pdf_bytes = render_personal_pdf(admin, g.user_id, user_email)

    filename = f"maramara-report-{date.today().isoformat()}.pdf"
    return send_file(
        BytesIO(pdf_bytes),
        mimetype="application/pdf",
        as_attachment=True,
        download_name=filename,
    )


@bp.get("/api/home")
@require_auth
def api_home():
    """Aggregated data for the home screen: trend, phrases, topics, recents.

    Supports ?range=day|week|month which controls the chart bucketing and the
    rolling window used for top phrases/topics.
    """
    admin = get_admin_client()
    now = datetime.now(timezone.utc)
    range_param = (request.args.get("range") or "week").lower()
    if range_param not in {"day", "week", "month"}:
        range_param = "week"
    window_days = {"day": 1, "week": 7, "month": 30}[range_param]
    window_start_iso = (now - timedelta(days=window_days)).isoformat()

    analyses = (
        admin.table("segment_analysis")
        .select("primary_topic,polarity,topic_mood,intensity_score,created_at")
        .eq("user_id", g.user_id)
        .gte("created_at", window_start_iso)
        .execute()
        .data
        or []
    )

    # Build the chart series based on range
    chart = _build_chart_series(admin, g.user_id, range_param, now)

    topic_counts: dict[str, int] = {}
    for a in analyses:
        t = a.get("primary_topic")
        if t:
            topic_counts[t] = topic_counts.get(t, 0) + 1
    top_topics = sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]

    terms = (
        admin.table("detected_terms")
        .select("term,term_type,created_at")
        .eq("user_id", g.user_id)
        .gte("created_at", window_start_iso)
        .execute()
        .data
        or []
    )
    term_counts: dict[str, dict] = {}
    for t in terms:
        k = t["term"]
        entry = term_counts.setdefault(k, {"term": k, "count": 0, "type": t.get("term_type")})
        entry["count"] += 1
    top_phrases = sorted(term_counts.values(), key=lambda x: x["count"], reverse=True)[:8]

    recents = (
        admin.table("audio_segments")
        .select("id,started_at,duration_sec,transcript_status,analysis_status")
        .eq("user_id", g.user_id)
        .eq("transcript_status", "completed")
        .order("started_at", desc=True)
        .limit(5)
        .execute()
        .data
        or []
    )
    if recents:
        ids = [r["id"] for r in recents]
        tx = {
            row["audio_segment_id"]: row
            for row in (
                admin.table("transcripts")
                .select("audio_segment_id,transcript_text,language")
                .in_("audio_segment_id", ids)
                .execute()
                .data
                or []
            )
        }
        an = {
            row["audio_segment_id"]: row
            for row in (
                admin.table("segment_analysis")
                .select("audio_segment_id,polarity,primary_topic,intensity_score")
                .in_("audio_segment_id", ids)
                .execute()
                .data
                or []
            )
        }
        for r in recents:
            r["transcript"] = tx.get(r["id"])
            r["analysis"] = an.get(r["id"])

    return jsonify({
        "success": True,
        "data": {
            "chart": chart,
            "range": range_param,
            "top_topics": [{"topic": t, "count": c} for t, c in top_topics],
            "top_phrases": top_phrases,
            "recents": recents,
            "total_week_segments": len(analyses),
        },
    })


def _build_chart_series(admin, user_id: str, range_param: str, now: datetime) -> list[dict]:
    """Bucketed time series for charts.

    - hour  -> 12 five-minute buckets of the last hour
    - day   -> 24 hourly buckets from today's midnight (UTC)
    - week  -> 7 daily buckets (last 7 days)
    - month -> 30 daily buckets (last 30 days)
    - year  -> 12 monthly buckets (last 12 months)
    """
    HEB_DAYS = ["א", "ב", "ג", "ד", "ה", "ו", "ש"]
    HEB_MONTHS = ["ינו", "פבר", "מרץ", "אפר", "מאי", "יונ",
                  "יול", "אוג", "ספט", "אוק", "נוב", "דצמ"]

    if range_param == "hour":
        start = now - timedelta(hours=1)
        rows = (
            admin.table("segment_analysis")
            .select("created_at,polarity,intensity_score")
            .eq("user_id", user_id)
            .gte("created_at", start.isoformat())
            .execute()
            .data
            or []
        )
        # 12 buckets × 5 minutes each
        buckets = [{"label": "", "intensity_sum": 0.0, "intensity_n": 0,
                    "positive_count": 0, "negative_count": 0} for _ in range(12)]
        for r in rows:
            try:
                t = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00"))
            except Exception:
                continue
            minutes_ago = int((now - t).total_seconds() // 60)
            idx = 11 - min(11, minutes_ago // 5)
            if idx < 0:
                continue
            b = buckets[idx]
            val = r.get("intensity_score") or 0
            b["intensity_sum"] += float(val)
            b["intensity_n"] += 1
            pol = r.get("polarity")
            if pol == "positive":
                b["positive_count"] += 1
            elif pol == "negative":
                b["negative_count"] += 1
        # Labels: "-55m", "-50m", ... "-0m"
        for i, b in enumerate(buckets):
            b["label"] = f"-{(11 - i) * 5}'"
        return [
            {
                "label": b["label"],
                "intensity_avg": b["intensity_sum"] / b["intensity_n"] if b["intensity_n"] else 0.0,
                "positive_count": b["positive_count"],
                "negative_count": b["negative_count"],
            }
            for b in buckets
        ]

    if range_param == "day":
        start = datetime(now.year, now.month, now.day, tzinfo=timezone.utc)
        rows = (
            admin.table("segment_analysis")
            .select("created_at,polarity,intensity_score")
            .eq("user_id", user_id)
            .gte("created_at", start.isoformat())
            .execute()
            .data
            or []
        )
        buckets = [{"label": f"{h:02d}", "intensity_sum": 0.0, "intensity_n": 0,
                    "positive_count": 0, "negative_count": 0} for h in range(24)]
        for r in rows:
            try:
                hr = datetime.fromisoformat(r["created_at"].replace("Z", "+00:00")).hour
            except Exception:
                continue
            b = buckets[hr]
            val = r.get("intensity_score") or 0
            b["intensity_sum"] += float(val)
            b["intensity_n"] += 1
            pol = r.get("polarity")
            if pol == "positive":
                b["positive_count"] += 1
            elif pol == "negative":
                b["negative_count"] += 1
        return [
            {
                "label": b["label"],
                "intensity_avg": b["intensity_sum"] / b["intensity_n"] if b["intensity_n"] else 0.0,
                "positive_count": b["positive_count"],
                "negative_count": b["negative_count"],
            }
            for b in buckets
        ]

    if range_param == "week":
        start_date = (now - timedelta(days=6)).date()
        daily = (
            admin.table("daily_metrics")
            .select("date,intensity_avg,positive_count,negative_count,calming_count")
            .eq("user_id", user_id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
            .data
            or []
        )
        by_date = {row["date"]: row for row in daily}
        out: list[dict] = []
        for i in range(7):
            d = start_date + timedelta(days=i)
            row = by_date.get(d.isoformat(), {})
            out.append({
                "label": HEB_DAYS[(d.weekday() + 1) % 7],  # Sunday first in Hebrew
                "intensity_avg": row.get("intensity_avg") or 0.0,
                "positive_count": row.get("positive_count") or 0,
                "negative_count": row.get("negative_count") or 0,
            })
        return out

    if range_param == "month":
        start_date = (now - timedelta(days=29)).date()
        daily = (
            admin.table("daily_metrics")
            .select("date,intensity_avg,positive_count,negative_count")
            .eq("user_id", user_id)
            .gte("date", start_date.isoformat())
            .order("date")
            .execute()
            .data
            or []
        )
        by_date = {row["date"]: row for row in daily}
        out: list[dict] = []
        for i in range(30):
            d = start_date + timedelta(days=i)
            row = by_date.get(d.isoformat(), {})
            # Label every 5 days; blank otherwise to keep axis readable
            label = f"{d.day}/{d.month}" if (29 - i) % 5 == 0 else ""
            out.append({
                "label": label,
                "intensity_avg": row.get("intensity_avg") or 0.0,
                "positive_count": row.get("positive_count") or 0,
                "negative_count": row.get("negative_count") or 0,
            })
        return out

    # range_param == "year" → 12 monthly buckets aggregated from daily_metrics
    start_date = date(now.year, now.month, 1) - timedelta(days=365)
    start_date = date(start_date.year, start_date.month, 1)
    daily = (
        admin.table("daily_metrics")
        .select("date,intensity_avg,positive_count,negative_count")
        .eq("user_id", user_id)
        .gte("date", start_date.isoformat())
        .order("date")
        .execute()
        .data
        or []
    )
    months: list[dict] = []
    base_year, base_month = start_date.year, start_date.month
    for i in range(12):
        total = (base_month - 1) + i
        y = base_year + (total // 12)
        m = (total % 12) + 1
        months.append({
            "year": y, "month": m, "label": HEB_MONTHS[m - 1],
            "intensity_sum": 0.0, "intensity_n": 0,
            "positive_count": 0, "negative_count": 0,
        })
    for row in daily:
        try:
            d = date.fromisoformat(row["date"])
        except Exception:
            continue
        for b in months:
            if b["year"] == d.year and b["month"] == d.month:
                val = row.get("intensity_avg") or 0
                if val:
                    b["intensity_sum"] += float(val)
                    b["intensity_n"] += 1
                b["positive_count"] += row.get("positive_count") or 0
                b["negative_count"] += row.get("negative_count") or 0
                break
    return [
        {
            "label": b["label"],
            "intensity_avg": b["intensity_sum"] / b["intensity_n"] if b["intensity_n"] else 0.0,
            "positive_count": b["positive_count"],
            "negative_count": b["negative_count"],
        }
        for b in months
    ]
