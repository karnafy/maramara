"""WeeklyInsightCrew - orchestrates 10 therapeutic agents for a weekly summary."""
from __future__ import annotations

import json
from datetime import date, timedelta

from crewai import Crew, Process

from config import get_settings
from db.supabase_client import get_admin_client
from utils.logger import get_logger

from .tasks import build_weekly_tasks

log = get_logger(__name__)


class WeeklyInsightCrew:
    """Orchestrator for weekly CrewAI insights.

    Flow:
      1. Pull week's segments + baseline from Supabase
      2. Build context JSON
      3. Run 10 agents sequentially (each produces a JSON fragment)
      4. Merge fragments into weekly_metrics.crewai_insights
      5. Also flag risks + update therapist_summary fields
    """

    def __init__(self, user_id: str, week_start: date) -> None:
        self.user_id = user_id
        self.week_start = week_start
        self.week_end = week_start + timedelta(days=7)
        self.settings = get_settings()
        self.admin = get_admin_client()

    def run(self) -> dict:
        context = self._build_context()
        if not context["segments"]:
            log.info("no_segments_for_week", user=self.user_id, week=self.week_start.isoformat())
            return {}

        language = context.get("language", "he")
        tasks = build_weekly_tasks(json.dumps(context, ensure_ascii=False), language=language)
        crew = Crew(
            tasks=tasks,
            agents=[t.agent for t in tasks],
            process=Process.sequential,
            verbose=False,
        )
        log.info("crew_running", user=self.user_id, agents=len(tasks))
        result = crew.kickoff()

        merged = self._merge_outputs(result, tasks)
        self._persist(merged)
        return merged

    def _build_context(self) -> dict:
        segments = self.admin.table("segment_analysis").select(
            "created_at,polarity,intensity_score,primary_topic,secondary_topic,"
            "trigger_detected,trigger_description,calming_detected,calming_description,"
            "self_criticism_score,absolutism_score,blame_score,cognitive_patterns,tags"
        ).eq("user_id", self.user_id).gte(
            "created_at", self.week_start.isoformat()
        ).lt(
            "created_at", self.week_end.isoformat()
        ).order("created_at").execute()

        transcripts = self.admin.table("transcripts").select(
            "audio_segment_id,transcript_text,language,created_at"
        ).eq("user_id", self.user_id).gte(
            "created_at", self.week_start.isoformat()
        ).lt(
            "created_at", self.week_end.isoformat()
        ).execute()

        profile = self.admin.table("profiles").select("language").eq("id", self.user_id).single().execute()

        baseline = self._compute_baseline()

        return {
            "week_start": self.week_start.isoformat(),
            "language": (profile.data or {}).get("language", "he"),
            "segments_count": len(segments.data or []),
            "segments": segments.data or [],
            "transcripts": [{"text": t["transcript_text"], "at": t["created_at"]} for t in (transcripts.data or [])],
            "baseline_metrics": baseline,
        }

    def _compute_baseline(self) -> dict:
        """Simple baseline = average of weekly_metrics from 4 weeks ago until now."""
        from datetime import timedelta
        baseline_start = (self.week_start - timedelta(weeks=4)).isoformat()
        resp = self.admin.table("weekly_metrics").select(
            "negativity_avg,positivity_avg,improvement_score"
        ).eq("user_id", self.user_id).gte("week_start", baseline_start).lt(
            "week_start", self.week_start.isoformat()
        ).execute()
        rows = resp.data or []
        if not rows:
            return {"negativity_avg": 0, "positivity_avg": 0, "improvement_score": 0}
        n = len(rows)
        return {
            "negativity_avg": sum(r["negativity_avg"] or 0 for r in rows) / n,
            "positivity_avg": sum(r["positivity_avg"] or 0 for r in rows) / n,
            "improvement_score": sum(r["improvement_score"] or 0 for r in rows) / n,
        }

    def _merge_outputs(self, kickoff_result, tasks) -> dict:
        """Each task's output is a JSON fragment; merge them."""
        merged: dict = {}
        for i, task in enumerate(tasks):
            raw = str(task.output.raw) if task.output else ""
            try:
                raw = raw.strip()
                if raw.startswith("```"):
                    raw = raw.strip("`").split("\n", 1)[-1]
                    if raw.endswith("```"):
                        raw = raw[:-3]
                fragment = json.loads(raw) if raw else {}
                merged.update(fragment)
            except json.JSONDecodeError:
                log.warning("crew_task_parse_fail", task_index=i, preview=raw[:120])
        return merged

    def _persist(self, merged: dict) -> None:
        self.admin.table("weekly_metrics").upsert({
            "user_id": self.user_id,
            "week_start": self.week_start.isoformat(),
            "top_trigger_topics": [t.get("topic") for t in merged.get("triggers", [])],
            "top_calming_topics": [r.get("source") for r in merged.get("regulations", [])],
            "top_phrases": merged.get("phrases", []),
            "therapist_summary": merged.get("therapist_summary"),
            "crewai_insights": merged,
            "improvement_score": (merged.get("progress") or {}).get("intensity_delta"),
        }, on_conflict="user_id,week_start").execute()

        risk = merged.get("risk") or {}
        if risk.get("detected"):
            self.admin.table("risk_flags").insert({
                "user_id": self.user_id,
                "risk_type": "weekly_crewai",
                "severity": risk.get("severity", "medium"),
                "description": risk.get("description") or "Flagged by weekly crew analysis",
            }).execute()
