"""Personal PDF report — designed export with SVG charts + Claude narrative.

Called from GET /api/export/pdf. Gathers the last 30 days of the user's
metrics + segment analyses, asks Claude Sonnet for a Hebrew deep-analysis
narrative, renders an HTML template with inline SVG charts, and converts
to PDF via WeasyPrint.
"""
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from typing import Any

from flask import render_template

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


HEB_DAYS = ["א", "ב", "ג", "ד", "ה", "ו", "ש"]

BRAND_PURPLE = "#6b5ce7"
BRAND_PURPLE_LIGHT = "#8b7cf0"
BRAND_TEAL = "#6dd5ed"
BRAND_CORAL = "#ef4444"
BRAND_MIDNIGHT = "#104356"
GREY_SOFT = "#94a3b8"


# ---------------------------------------------------------------------------
# Claude narrative
# ---------------------------------------------------------------------------

NARRATIVE_SYSTEM_PROMPT = """אתה מטפל-מנתח. קיבלת סיכום 30 יום של דפוסי דיבור של משתמש,
כולל סטטיסטיקות רגשיות, נושאים חוזרים, טריגרים ואלמנטים מרגיעים.

כתוב ניתוח עומק בעברית, קליני אך חומל, באורך 400-600 מילים. השתמש בחלוקה
לחלקים (בלי Markdown — רק פסקאות נפרדות). אל תשפוט, אל תכתוב "רעיל" או "רע".
נסח תצפיות בלשון רפלקטיבית (למשל "נצפתה נטייה ל..." במקום "אתה תמיד...").

כלול:
1. תמונת מצב כללית — מה המגמה השבועית, רמת אינטנסיביות, פולריות דומיננטית.
2. 2-3 דפוסים מרכזיים שנצפו — מה הנושאים שחוזרים ומתי.
3. טריגרים מובילים — מה מפעיל, באיזה הקשר.
4. אלמנטים מרגיעים — מה עובד, מה שווה להעצים.
5. 3 המלצות עדינות ומעשיות — לא הוראות, אלא הזמנות לתשומת לב.

סיים במשפט אמפתי אחד.
אל תכתוב כותרות או מספורים — פסקאות נקיות בלבד."""


@lru_cache(maxsize=1)
def _anthropic_client():
    from anthropic import Anthropic
    return Anthropic(api_key=get_settings().anthropic_api_key)


def _generate_narrative(summary: dict) -> str:
    """Call Claude with a structured summary, return Hebrew narrative."""
    settings = get_settings()
    if not settings.anthropic_api_key:
        return (
            "הניתוח המעמיק יופיע כאן לאחר הגדרת מפתח ה־Claude API. "
            "בינתיים ניתן לראות את הגרפים והנתונים המפורטים בדוח."
        )

    try:
        client = _anthropic_client()
        resp = client.messages.create(
            model=settings.crewai_model,
            max_tokens=1500,
            system=NARRATIVE_SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": json.dumps(summary, ensure_ascii=False, indent=2),
            }],
        )
        return resp.content[0].text.strip()
    except Exception as e:
        log.error("narrative_generation_failed", error=str(e))
        return (
            "לא הצלחנו לייצר ניתוח מעמיק כרגע. הנתונים המפורטים בהמשך "
            "מציגים את התמונה המלאה."
        )


# ---------------------------------------------------------------------------
# Data gathering
# ---------------------------------------------------------------------------

@dataclass
class ReportData:
    generated_at: str
    window_start: str
    window_end: str
    total_segments: int
    total_minutes: float
    avg_intensity: float
    polarity: dict[str, int]
    daily_series: list[dict]
    top_topics: list[dict]
    top_phrases: list[dict]
    top_triggers: list[dict]
    top_calming: list[dict]
    cognitive_patterns: list[dict]
    sample_transcripts: list[dict]
    narrative: str


def _gather(admin, user_id: str) -> ReportData:
    now = datetime.now(timezone.utc)
    window_start = (now - timedelta(days=30)).date()
    window_end = now.date()

    segments = (
        admin.table("audio_segments")
        .select("id,duration_sec,started_at")
        .eq("user_id", user_id)
        .gte("started_at", window_start.isoformat())
        .execute()
        .data
        or []
    )
    seg_ids = [s["id"] for s in segments]
    total_minutes = round(sum(s.get("duration_sec") or 0 for s in segments) / 60.0, 1)

    analyses: list[dict] = []
    if seg_ids:
        analyses = (
            admin.table("segment_analysis")
            .select(
                "audio_segment_id,polarity,intensity_score,primary_topic,topic_mood,"
                "trigger_detected,trigger_description,calming_detected,calming_description,"
                "self_criticism_score,complaint_score,joy_score,worry_score,anger_score,"
                "cognitive_patterns,created_at"
            )
            .in_("audio_segment_id", seg_ids)
            .execute()
            .data
            or []
        )

    polarity = {"positive": 0, "neutral": 0, "negative": 0, "mixed": 0}
    intensity_sum = 0.0
    intensity_n = 0
    topic_counts: dict[str, int] = {}
    trigger_counts: dict[str, int] = {}
    calming_counts: dict[str, int] = {}
    pattern_counts: dict[str, int] = {}
    for a in analyses:
        p = a.get("polarity") or "neutral"
        polarity[p] = polarity.get(p, 0) + 1
        if a.get("intensity_score"):
            intensity_sum += float(a["intensity_score"])
            intensity_n += 1
        t = a.get("primary_topic")
        if t:
            topic_counts[t] = topic_counts.get(t, 0) + 1
        if a.get("trigger_detected") and a.get("trigger_description"):
            key = a["trigger_description"][:80]
            trigger_counts[key] = trigger_counts.get(key, 0) + 1
        if a.get("calming_detected") and a.get("calming_description"):
            key = a["calming_description"][:80]
            calming_counts[key] = calming_counts.get(key, 0) + 1
        for cp in (a.get("cognitive_patterns") or []):
            pattern_counts[cp] = pattern_counts.get(cp, 0) + 1

    avg_intensity = round(intensity_sum / intensity_n, 2) if intensity_n else 0.0

    # Daily series: join 30 days of daily_metrics
    daily = (
        admin.table("daily_metrics")
        .select("date,intensity_avg,positive_count,negative_count")
        .eq("user_id", user_id)
        .gte("date", window_start.isoformat())
        .order("date")
        .execute()
        .data
        or []
    )
    by_date = {row["date"]: row for row in daily}
    daily_series: list[dict] = []
    for i in range(30):
        d = window_start + timedelta(days=i)
        row = by_date.get(d.isoformat(), {})
        daily_series.append({
            "date": d.isoformat(),
            "label": f"{d.day}/{d.month}",
            "day_of_week": HEB_DAYS[(d.weekday() + 1) % 7],
            "intensity_avg": float(row.get("intensity_avg") or 0),
            "positive_count": int(row.get("positive_count") or 0),
            "negative_count": int(row.get("negative_count") or 0),
        })

    top_topics = [
        {"topic": t, "count": c}
        for t, c in sorted(topic_counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
    ]

    top_triggers = [
        {"text": t, "count": c}
        for t, c in sorted(trigger_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    ]
    top_calming = [
        {"text": t, "count": c}
        for t, c in sorted(calming_counts.items(), key=lambda kv: kv[1], reverse=True)[:5]
    ]

    # Top phrases from detected_terms
    terms = (
        admin.table("detected_terms")
        .select("term,term_type")
        .eq("user_id", user_id)
        .gte("created_at", window_start.isoformat())
        .execute()
        .data
        or []
    )
    term_counts: dict[tuple[str, str], int] = {}
    for t in terms:
        key = (t["term"], t.get("term_type") or "")
        term_counts[key] = term_counts.get(key, 0) + 1
    top_phrases = [
        {"term": k[0], "type": k[1], "count": v}
        for k, v in sorted(term_counts.items(), key=lambda kv: kv[1], reverse=True)[:12]
    ]

    cognitive_patterns = [
        {"pattern": p, "count": c}
        for p, c in sorted(pattern_counts.items(), key=lambda kv: kv[1], reverse=True)[:6]
    ]

    # Sample transcripts: last 5 completed
    samples: list[dict] = []
    if seg_ids:
        last_ids = [s["id"] for s in sorted(segments, key=lambda s: s["started_at"], reverse=True)[:5]]
        txs = (
            admin.table("transcripts")
            .select("audio_segment_id,transcript_text")
            .in_("audio_segment_id", last_ids)
            .execute()
            .data
            or []
        )
        tx_by_seg = {t["audio_segment_id"]: t for t in txs}
        ans_by_seg = {a["audio_segment_id"]: a for a in analyses}
        seg_map = {s["id"]: s for s in segments}
        for sid in last_ids:
            t = tx_by_seg.get(sid)
            a = ans_by_seg.get(sid)
            s = seg_map.get(sid)
            if not t or not a:
                continue
            samples.append({
                "started_at": s.get("started_at", ""),
                "text": (t.get("transcript_text") or "").strip()[:400],
                "polarity": a.get("polarity", "neutral"),
                "topic": a.get("primary_topic") or "",
                "intensity": float(a.get("intensity_score") or 0),
            })

    summary_for_llm = {
        "חלון": f"{window_start} עד {window_end}",
        "סך_קטעים": len(segments),
        "סך_דקות": total_minutes,
        "אינטנסיביות_ממוצעת": avg_intensity,
        "פולריות": polarity,
        "נושאים_עיקריים": top_topics,
        "טריגרים_עיקריים": top_triggers,
        "אלמנטים_מרגיעים": top_calming,
        "דפוסים_קוגניטיביים": cognitive_patterns,
        "ביטויים_בולטים": top_phrases[:8],
    }
    narrative = _generate_narrative(summary_for_llm)

    return ReportData(
        generated_at=now.strftime("%d/%m/%Y %H:%M"),
        window_start=window_start.strftime("%d/%m/%Y"),
        window_end=window_end.strftime("%d/%m/%Y"),
        total_segments=len(segments),
        total_minutes=total_minutes,
        avg_intensity=avg_intensity,
        polarity=polarity,
        daily_series=daily_series,
        top_topics=top_topics,
        top_phrases=top_phrases,
        top_triggers=top_triggers,
        top_calming=top_calming,
        cognitive_patterns=cognitive_patterns,
        sample_transcripts=samples,
        narrative=narrative,
    )


# ---------------------------------------------------------------------------
# SVG chart builders (pure Python, no deps)
# ---------------------------------------------------------------------------

def _line_chart_svg(series: list[dict], width: int = 720, height: int = 220) -> str:
    """Smooth line chart of intensity_avg over 30 days."""
    if not series:
        return ""
    pad_left, pad_right, pad_top, pad_bottom = 40, 16, 16, 40
    inner_w = width - pad_left - pad_right
    inner_h = height - pad_top - pad_bottom
    n = len(series)
    max_v = max((p["intensity_avg"] for p in series), default=1.0) or 1.0
    max_v = max(max_v, 1.0)

    def xy(i: int, v: float) -> tuple[float, float]:
        x = pad_left + (inner_w * i / (n - 1 if n > 1 else 1))
        y = pad_top + inner_h - (inner_h * (v / max_v))
        return x, y

    points = [xy(i, p["intensity_avg"]) for i, p in enumerate(series)]
    path = "M " + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
    # Fill path (area under curve)
    fill = (
        f"M {points[0][0]:.1f},{pad_top + inner_h} "
        + " L ".join(f"{x:.1f},{y:.1f}" for x, y in points)
        + f" L {points[-1][0]:.1f},{pad_top + inner_h} Z"
    )

    # Gridlines + y-axis labels (0, mid, max)
    gridlines = []
    for frac, label_v in [(0.0, 0), (0.5, max_v / 2), (1.0, max_v)]:
        gy = pad_top + inner_h - inner_h * frac
        gridlines.append(
            f'<line x1="{pad_left}" y1="{gy:.1f}" x2="{width - pad_right}" y2="{gy:.1f}" '
            f'stroke="#e2e8f0" stroke-width="0.5" stroke-dasharray="2 3" />'
        )
        gridlines.append(
            f'<text x="{pad_left - 8}" y="{gy + 3:.1f}" fill="{GREY_SOFT}" font-size="10" '
            f'text-anchor="end">{label_v:.1f}</text>'
        )

    # X labels: every 5th day
    x_labels = []
    for i in range(0, n, 5):
        x = pad_left + (inner_w * i / (n - 1 if n > 1 else 1))
        x_labels.append(
            f'<text x="{x:.1f}" y="{height - pad_bottom + 18}" fill="{GREY_SOFT}" '
            f'font-size="10" text-anchor="middle">{series[i]["label"]}</text>'
        )

    return f"""
<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}">
  <defs>
    <linearGradient id="lineGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="{BRAND_PURPLE}" stop-opacity="0.35"/>
      <stop offset="100%" stop-color="{BRAND_TEAL}" stop-opacity="0.02"/>
    </linearGradient>
  </defs>
  {"".join(gridlines)}
  <path d="{fill}" fill="url(#lineGrad)" stroke="none" />
  <path d="{path}" fill="none" stroke="{BRAND_PURPLE}" stroke-width="2.2" stroke-linejoin="round" stroke-linecap="round" />
  {"".join(x_labels)}
</svg>"""


def _donut_chart_svg(polarity: dict[str, int], size: int = 220) -> str:
    """Donut chart of polarity mix."""
    total = sum(polarity.values()) or 1
    colors = {
        "positive": BRAND_TEAL,
        "neutral": GREY_SOFT,
        "negative": BRAND_CORAL,
        "mixed": BRAND_PURPLE_LIGHT,
    }
    labels_he = {
        "positive": "חיובי",
        "neutral": "נייטרלי",
        "negative": "שלילי",
        "mixed": "מעורב",
    }
    cx, cy, r = size / 2, size / 2, size * 0.38
    inner_r = r * 0.62

    def arc_path(start_angle: float, end_angle: float) -> str:
        start = (cx + r * math.cos(start_angle), cy + r * math.sin(start_angle))
        end = (cx + r * math.cos(end_angle), cy + r * math.sin(end_angle))
        inner_start = (cx + inner_r * math.cos(end_angle), cy + inner_r * math.sin(end_angle))
        inner_end = (cx + inner_r * math.cos(start_angle), cy + inner_r * math.sin(start_angle))
        large = 1 if (end_angle - start_angle) > math.pi else 0
        return (
            f"M {start[0]:.1f},{start[1]:.1f} "
            f"A {r:.1f},{r:.1f} 0 {large} 1 {end[0]:.1f},{end[1]:.1f} "
            f"L {inner_start[0]:.1f},{inner_start[1]:.1f} "
            f"A {inner_r:.1f},{inner_r:.1f} 0 {large} 0 {inner_end[0]:.1f},{inner_end[1]:.1f} Z"
        )

    arcs = []
    angle = -math.pi / 2
    for key in ["positive", "neutral", "negative", "mixed"]:
        val = polarity.get(key, 0)
        if val <= 0:
            continue
        frac = val / total
        new_angle = angle + frac * 2 * math.pi
        arcs.append(
            f'<path d="{arc_path(angle, new_angle)}" fill="{colors[key]}" opacity="0.88" />'
        )
        angle = new_angle

    # Center label: dominant polarity
    dominant = max(polarity.items(), key=lambda kv: kv[1])[0] if total > 0 else "neutral"
    dom_label = labels_he.get(dominant, "")
    dom_pct = round(100 * polarity.get(dominant, 0) / total)

    # Legend
    legend_y = size - 18
    legend_items = []
    legend_x = 20
    for key in ["positive", "neutral", "negative", "mixed"]:
        if polarity.get(key, 0) <= 0:
            continue
        legend_items.append(
            f'<rect x="{legend_x}" y="{legend_y - 8}" width="10" height="10" '
            f'rx="2" fill="{colors[key]}" />'
            f'<text x="{legend_x + 16}" y="{legend_y + 1}" font-size="10" fill="#334155">'
            f'{labels_he[key]} ({polarity[key]})</text>'
        )
        legend_x += 80

    return f"""
<svg viewBox="0 0 {size} {size + 10}" xmlns="http://www.w3.org/2000/svg" width="{size}" height="{size + 10}">
  {"".join(arcs)}
  <text x="{cx}" y="{cy - 4}" text-anchor="middle" font-size="13" fill="{GREY_SOFT}">{dom_label}</text>
  <text x="{cx}" y="{cy + 16}" text-anchor="middle" font-size="22" font-weight="700" fill="{BRAND_MIDNIGHT}">{dom_pct}%</text>
  {"".join(legend_items)}
</svg>"""


def _bar_chart_svg(items: list[dict], key_label: str, key_count: str,
                   width: int = 360, bar_h: int = 22) -> str:
    """Horizontal bar chart for top topics / triggers / phrases."""
    if not items:
        return ""
    max_v = max(it[key_count] for it in items) or 1
    row_h = bar_h + 10
    height = row_h * len(items) + 10
    # For RTL: bars grow from right to left.
    label_w = 140
    bar_area = width - label_w - 20

    rows = []
    for i, it in enumerate(items):
        y = 8 + i * row_h
        frac = it[key_count] / max_v
        bw = bar_area * frac
        bar_x = width - label_w - bw
        label_x = width - 4  # text-anchor=end; RTL label on the right
        rows.append(
            f'<text x="{label_x}" y="{y + bar_h - 6}" text-anchor="end" font-size="11" '
            f'fill="{BRAND_MIDNIGHT}" font-weight="600">{it[key_label]}</text>'
            f'<rect x="{bar_x:.1f}" y="{y}" width="{bw:.1f}" height="{bar_h}" rx="6" '
            f'fill="url(#barGrad)" opacity="0.9" />'
            f'<text x="{bar_x - 6:.1f}" y="{y + bar_h - 6}" text-anchor="end" font-size="10" '
            f'fill="{GREY_SOFT}">{it[key_count]}</text>'
        )

    return f"""
<svg viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" width="100%" height="{height}">
  <defs>
    <linearGradient id="barGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="{BRAND_TEAL}"/>
      <stop offset="100%" stop-color="{BRAND_PURPLE}"/>
    </linearGradient>
  </defs>
  {"".join(rows)}
</svg>"""


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def render_personal_pdf(admin, user_id: str, user_email: str | None = None) -> bytes:
    """Gather data, render HTML, convert to PDF bytes."""
    data = _gather(admin, user_id)

    charts = {
        "trend": _line_chart_svg(data.daily_series),
        "polarity": _donut_chart_svg(data.polarity),
        "topics": _bar_chart_svg(data.top_topics, "topic", "count"),
        "phrases": _bar_chart_svg(
            [{"term": p["term"], "count": p["count"]} for p in data.top_phrases[:8]],
            "term", "count",
        ),
    }

    html = render_template(
        "exports/personal_pdf.html",
        data=data,
        charts=charts,
        user_email=user_email or "",
    )

    # WeasyPrint import is lazy so the rest of the app doesn't pay the import cost.
    from weasyprint import HTML
    return HTML(string=html).write_pdf()
