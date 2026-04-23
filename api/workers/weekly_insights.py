"""Worker: run the CrewAI weekly insight pipeline."""
from __future__ import annotations

from datetime import date

from config import get_settings
from db.supabase_client import init_supabase_client
from services.crew import WeeklyInsightCrew
from services.obsidian import ObsidianExporter
from utils.logger import get_logger

log = get_logger(__name__)


def run(user_id: str, week_start_iso: str) -> None:
    settings = get_settings()
    init_supabase_client(settings)
    if not settings.enable_crewai_insights:
        log.info("crewai_disabled_by_flag", user=user_id)
        return
    week_start = date.fromisoformat(week_start_iso)
    crew = WeeklyInsightCrew(user_id, week_start)
    crew.run()
    log.info("weekly_crew_completed", user=user_id, week=week_start_iso)

    # Best-effort export to Obsidian vault; never fail the job on export errors.
    try:
        note = ObsidianExporter().export_weekly(user_id, week_start)
        if note:
            log.info("obsidian_weekly_written", path=str(note.path))
    except Exception:
        log.exception("obsidian_export_failed", user=user_id, week=week_start_iso)
