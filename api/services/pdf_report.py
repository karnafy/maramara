"""PDF generation for therapist weekly reports using ReportLab."""
from __future__ import annotations

from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    PageBreak,
)


def generate_weekly_pdf(weekly: dict) -> bytes:
    """Render a weekly_metrics row into a PDF byte-string."""
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title="MARAMARA Weekly Report",
    )
    styles = getSampleStyleSheet()
    h1 = ParagraphStyle("H1", parent=styles["Heading1"], textColor=colors.HexColor("#4F46E5"))
    story: list = []

    story.append(Paragraph("MARAMARA — Weekly Behavioural Report", h1))
    story.append(Paragraph(f"Week of {weekly.get('week_start')}", styles["Heading3"]))
    story.append(Spacer(1, 6 * mm))

    summary_rows = [
        ["Improvement Score", f"{weekly.get('improvement_score', 0):.2f}"],
        ["Avg Negativity", f"{weekly.get('negativity_avg', 0):.2f}"],
        ["Avg Positivity", f"{weekly.get('positivity_avg', 0):.2f}"],
        ["Curse Delta", f"{weekly.get('curse_delta', 0):+.2f}"],
    ]
    t = Table(summary_rows, colWidths=[60 * mm, 50 * mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EEF2FF")),
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.grey),
        ("INNERGRID", (0, 0), (-1, -1), 0.25, colors.grey),
        ("PADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 8 * mm))

    story.append(Paragraph("Top Trigger Topics", styles["Heading3"]))
    for item in weekly.get("top_trigger_topics") or []:
        story.append(Paragraph(f"• {item}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    story.append(Paragraph("Top Calming Topics", styles["Heading3"]))
    for item in weekly.get("top_calming_topics") or []:
        story.append(Paragraph(f"• {item}", styles["Normal"]))
    story.append(Spacer(1, 4 * mm))

    if weekly.get("therapist_summary"):
        story.append(PageBreak())
        story.append(Paragraph("AI-Generated Therapeutic Summary", h1))
        story.append(Spacer(1, 4 * mm))
        story.append(Paragraph(weekly["therapist_summary"], styles["BodyText"]))

    doc.build(story)
    return buf.getvalue()
