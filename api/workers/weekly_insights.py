"""Worker: run the CrewAI weekly insight pipeline."""
from __future__ import annotations

from datetime import date

from config import get_settings
from db.supabase_client import init_supabase_client
from services.crew import WeeklyInsightCrew
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
