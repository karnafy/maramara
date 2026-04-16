"""CrewAI task definitions for the weekly insight crew."""
from __future__ import annotations

from crewai import Task

from .agents import (
    trigger_pattern_agent,
    regulation_agent,
    self_talk_agent,
    cognitive_distortions_agent,
    escalation_loop_agent,
    phrase_mining_agent,
    progress_agent,
    therapist_summary_agent,
    user_reflection_agent,
    risk_assessment_agent,
)


def build_weekly_tasks(context_json: str, language: str = "he") -> list[Task]:
    """Build the ordered task list for the weekly insight crew.

    `context_json` is a JSON string containing: week_start, segments (array of
    {created_at, transcript, polarity, intensity, primary_topic, ...}), and baseline_metrics.
    """
    lang_instruction = (
        "ענה בעברית, בטון רך, בלי להכליל, בלי שיפוט מוסרי."
        if language == "he"
        else "Respond in English, with gentle tone, avoid generalizations and moral judgment."
    )

    common_header = f"""Analyze the user's weekly speech data below.
{lang_instruction}
Return your output as compact JSON only (no prose). Keys must match what is requested.

DATA:
{context_json}
"""

    return [
        Task(
            description=common_header + """
Find up to 5 recurring triggers. For each: topic, frequency, avg_intensity, example_phrase.
Output JSON: {"triggers": [{"topic": str, "frequency": int, "avg_intensity": float, "example": str}]}
""",
            expected_output="JSON with triggers array",
            agent=trigger_pattern_agent(),
        ),
        Task(
            description=common_header + """
Find up to 5 regulation sources (calming). For each: topic/phrase, frequency, avg_drop_in_intensity.
Output JSON: {"regulations": [{"source": str, "frequency": int, "intensity_drop": float}]}
""",
            expected_output="JSON with regulations array",
            agent=regulation_agent(),
        ),
        Task(
            description=common_header + """
Map self-talk. Categories: supportive, critical, neutral. Count each. Extract 3 example phrases per category.
Output JSON: {"self_talk": {"supportive": {"count": int, "examples": [...]}, "critical": {...}, "neutral": {...}}}
""",
            expected_output="JSON self_talk object",
            agent=self_talk_agent(),
        ),
        Task(
            description=common_header + """
Count occurrences of cognitive distortions (catastrophizing, all_or_nothing, personalization, should_statements, mind_reading, filtering).
Output JSON: {"distortions": {"catastrophizing": int, ...}}
""",
            expected_output="JSON distortions counts",
            agent=cognitive_distortions_agent(),
        ),
        Task(
            description=common_header + """
Identify up to 3 escalation loops. For each: trigger_topic, peak_intensity, time_to_recover_min, resolution_source.
Output JSON: {"loops": [{"trigger_topic": str, "peak": float, "recover_min": float, "resolution": str}]}
""",
            expected_output="JSON loops array",
            agent=escalation_loop_agent(),
        ),
        Task(
            description=common_header + """
Extract top 10 repeated phrases. Mark each as stress_phrase or regulation_phrase.
Output JSON: {"phrases": [{"phrase": str, "count": int, "type": "stress"|"regulation"}]}
""",
            expected_output="JSON phrases array",
            agent=phrase_mining_agent(),
        ),
        Task(
            description=common_header + """
Compare this week vs baseline_metrics in DATA. Rate change in: negativity, intensity, self_criticism.
Output JSON: {"progress": {"negativity_delta": float, "intensity_delta": float, "self_criticism_delta": float, "verdict": "improving"|"stable"|"regressing", "explanation": str}}
""",
            expected_output="JSON progress object",
            agent=progress_agent(),
        ),
        Task(
            description=common_header + """
Scan for risk signals: self-harm, suicidal ideation, severe depression, substance abuse, domestic violence.
Output JSON: {"risk": {"detected": bool, "severity": "info"|"low"|"medium"|"high"|"critical", "description": str|null}}
""",
            expected_output="JSON risk object",
            agent=risk_assessment_agent(),
        ),
        Task(
            description=common_header + """
Using the previous agents' findings (available in your context), write a 200-300 word clinical summary for the therapist.
Output JSON: {"therapist_summary": str}
""",
            expected_output="JSON with therapist_summary string",
            agent=therapist_summary_agent(),
        ),
        Task(
            description=common_header + """
Using the previous findings, write a short (100-150 word) compassionate reflection for the user.
Must not shame. Must use reflective phrasing.
Output JSON: {"user_reflection": str}
""",
            expected_output="JSON with user_reflection string",
            agent=user_reflection_agent(),
        ),
    ]
