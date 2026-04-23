"""Export MARAMARA insights as markdown notes into an Obsidian vault.

Layout inside the vault:
    <vault>/MARAMARA-Insights/<user_email>/<YYYY-MM-DD>.md

Each note includes YAML frontmatter so Dataview can query across weeks.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from config import get_settings
from db.supabase_client import get_admin_client
from utils.logger import get_logger

log = get_logger(__name__)


@dataclass(frozen=True)
class ExportedNote:
    path: Path
    week_start: str
    user_email: str


class ObsidianExporter:
    """Writes weekly insight notes into an Obsidian vault folder."""

    def __init__(self) -> None:
        s = get_settings()
        self._vault_path = Path(s.obsidian_vault_path).expanduser()
        self._insights_dir = s.obsidian_insights_dir
        self._enabled = s.enable_obsidian_export and self._vault_path.exists()
        if not self._enabled:
            log.info(
                "obsidian_export_disabled",
                reason="flag_off" if not s.enable_obsidian_export else "vault_missing",
                vault=str(self._vault_path),
            )

    @property
    def enabled(self) -> bool:
        return self._enabled

    def export_weekly(self, user_id: str, week_start: date) -> ExportedNote | None:
        if not self._enabled:
            return None

        admin = get_admin_client()
        profile = (
            admin.table("profiles")
            .select("email, full_name")
            .eq("id", user_id)
            .single()
            .execute()
            .data
            or {}
        )
        metrics = (
            admin.table("weekly_metrics")
            .select("*")
            .eq("user_id", user_id)
            .eq("week_start", week_start.isoformat())
            .execute()
            .data
        )
        if not metrics:
            log.info("obsidian_no_metrics", user_id=user_id, week=week_start.isoformat())
            return None

        row = metrics[0]
        user_email = profile.get("email") or user_id[:8]
        md = self._render_markdown(row, profile)

        folder = self._vault_path / self._insights_dir / _safe(user_email)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / f"{week_start.isoformat()}.md"
        path.write_text(md, encoding="utf-8")
        log.info("obsidian_exported", path=str(path), user_id=user_id)

        return ExportedNote(path=path, week_start=week_start.isoformat(), user_email=user_email)

    # ---------- rendering ----------

    def _render_markdown(self, row: dict[str, Any], profile: dict[str, Any]) -> str:
        insights = row.get("crewai_insights") or {}
        frontmatter = self._frontmatter(row, profile, insights)
        body = self._body(row, insights)
        return f"---\n{frontmatter}---\n\n{body}"

    def _frontmatter(
        self,
        row: dict[str, Any],
        profile: dict[str, Any],
        insights: dict[str, Any],
    ) -> str:
        progress = insights.get("progress") or {}
        risk = insights.get("risk") or {}
        items: list[tuple[str, Any]] = [
            ("type", "maramara-weekly"),
            ("week_start", row.get("week_start")),
            ("user_email", profile.get("email", "")),
            ("user_name", profile.get("full_name", "")),
            ("improvement_score", row.get("improvement_score")),
            ("intensity_delta", progress.get("intensity_delta")),
            ("risk_detected", bool(risk.get("detected"))),
            ("risk_severity", risk.get("severity")),
        ]
        lines = [f"{k}: {_yaml_value(v)}" for k, v in items if v not in (None, "")]

        tags = ["maramara", "weekly-insight"]
        if risk.get("detected"):
            tags.append("risk")
        for topic in (row.get("top_trigger_topics") or [])[:3]:
            if topic:
                tags.append(f"trigger/{_tag_safe(topic)}")
        lines.append(f"tags: [{', '.join(tags)}]")
        return "\n".join(lines) + "\n"

    def _body(self, row: dict[str, Any], insights: dict[str, Any]) -> str:
        chunks: list[str] = []
        chunks.append(f"# שבוע של {row.get('week_start', '?')}")

        summary = row.get("therapist_summary") or insights.get("therapist_summary")
        if summary:
            chunks.append(f"## סיכום\n{summary}")

        user_ref = insights.get("user_reflection")
        if user_ref:
            chunks.append(f"## השבוע במילותיך\n{user_ref}")

        triggers = row.get("top_trigger_topics") or []
        if triggers:
            chunks.append("## טריגרים מובילים\n" + _bullets(triggers))

        calming = row.get("top_calming_topics") or []
        if calming:
            chunks.append("## מרגיעים מובילים\n" + _bullets(calming))

        phrases = row.get("top_phrases") or []
        if phrases:
            pretty = [
                f"{p.get('phrase','?')} — {p.get('count', '?')} פעמים"
                if isinstance(p, dict)
                else str(p)
                for p in phrases[:10]
            ]
            chunks.append("## ביטויים חוזרים\n" + _bullets(pretty))

        patterns = insights.get("cognitive_patterns") or []
        if patterns:
            chunks.append("## דפוסים קוגניטיביים\n" + _bullets(patterns))

        progress = insights.get("progress") or {}
        if progress:
            delta = progress.get("intensity_delta")
            note = progress.get("note") or progress.get("summary")
            parts = []
            if delta is not None:
                parts.append(f"- שינוי באינטנסיביות: **{delta:+.2f}**")
            if note:
                parts.append(f"- {note}")
            if parts:
                chunks.append("## התקדמות\n" + "\n".join(parts))

        risk = insights.get("risk") or {}
        if risk.get("detected"):
            chunks.append(
                "## ⚠️ דגל סיכון\n"
                f"- רמה: **{risk.get('severity','?')}**\n"
                f"- תיאור: {risk.get('description','')}"
            )

        chunks.append("---\n*נוצר אוטומטית על ידי MARAMARA*")
        return "\n\n".join(chunks) + "\n"


# ---------- helpers ----------

def _bullets(items: Iterable[Any]) -> str:
    return "\n".join(f"- {x}" for x in items if x)


def _yaml_value(v: Any) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    s = str(v).replace('"', '\\"')
    return f'"{s}"'


def _safe(value: str) -> str:
    """Make a string safe to use as a filesystem path segment (ASCII only)."""
    return "".join(c if c.isalnum() or c in "-_." else "-" for c in value).strip("-")


def _tag_safe(value: str) -> str:
    """Make a string safe as an Obsidian tag (allow Hebrew + letters + digits)."""
    return "".join(c if c.isalnum() or c in "-_" else "-" for c in value).strip("-")
