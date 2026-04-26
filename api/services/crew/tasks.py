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
Return your output as valid JSON only (no prose around it). Keys must match what is requested.
String values inside the JSON may be long, multi-paragraph, and richly detailed when the task asks for it —
do not shorten them to feel "compact". Use "\\n\\n" between paragraphs inside string values.

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
Then write a WARM, SPECIFIC explanation (80-140 Hebrew words) that references concrete moments from the week,
and add one key strength you noticed, one key challenge, and one gentle micro-invitation for next week
(phrased as an invitation, not an order — e.g. "אפשר לנסות...", "מוזמן לשים לב ל...").

Output JSON: {"progress": {
  "negativity_delta": float,
  "intensity_delta": float,
  "self_criticism_delta": float,
  "verdict": "improving"|"stable"|"regressing",
  "explanation": str,
  "key_strength": str,
  "key_challenge": str,
  "micro_invitation": str
}}
""",
            expected_output="JSON progress object with rich explanation and three qualitative fields",
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
Using the previous agents' findings, write a DETAILED 500-650 Hebrew word clinical summary
for the therapist. This is not a tweet — it must be long, specific, and cite real data.
Use EXACTLY 4 paragraphs separated by a blank line (\\n\\n). Each paragraph opens with a bold-style label
("תמונת שבוע:", "דפוסים שנצפו:", "אלמנטים מחזקים:", "המלצות התערבות:") followed by flowing prose — no bullets,
no markdown headings, no numbering.

Paragraph 1 — "תמונת שבוע:" (~120-150 words)
  Overall emotional arc across the week. Cite: total segments, polarity split (pos/neu/neg %),
  average intensity, dominant topic, and 1-2 notable days or time-windows.

Paragraph 2 — "דפוסים שנצפו:" (~150-180 words)
  Specific patterns with citations: top triggers (with frequency), cognitive distortions observed
  (with counts), self-talk critical/supportive ratio, escalation loops (with recovery time).
  Quote 1-2 example phrases the user actually said.

Paragraph 3 — "אלמנטים מחזקים:" (~100-130 words)
  Regulation sources, supportive self-talk examples, de-escalation moments. Quote at least one
  specific regulating phrase. Note what reliably brings intensity down.

Paragraph 4 — "המלצות התערבות:" (~130-160 words)
  3 concrete, clinically-grounded therapeutic angles to explore in the next session, each tied
  to evidence from the week. Phrase as options for the clinician to consider, not prescriptions.

Output JSON: {"therapist_summary": str}
""",
            expected_output="JSON with a long (500-650 words), structured, cited therapist_summary string",
            agent=therapist_summary_agent(),
        ),
        Task(
            description=common_header + """
Write a LONG, DEEPLY PERSONAL reflection for the user — 500-650 Hebrew words. This is the most important
output in the entire crew: the user MUST feel truly seen when they read it. Short, generic, or
greeting-card output is a failure.

Hard rules:
  * 5-7 paragraphs separated by a blank line (\\n\\n). No markdown, no headings, no bullet lists — flowing prose.
  * Quote AT LEAST 2-3 actual phrases from THEIR transcripts (use Hebrew quotation marks "…").
  * Reference at least 2 specific time-windows or days from the week (e.g. "ביום שישי בערב", "באמצע השבוע").
  * Second-person, warm, slow. Like a trusted coach who listened to every recording.
  * Forbidden: "רעיל", "בעייתי", "אתה תמיד", "אתה צריך", shame/judgment, generic advice, clichés.
  * Preferred openers: "שמעתי אותך...", "ישבתי עם מה שאמרת ב...", "שמתי לב שב...", "ראיתי את עצמך...".

Paragraph structure (use this shape, not these exact sentences):

  Paragraph 1 — Warm opening. Name what you sensed in their voice/mood overall this week, in one image or one feeling.
  Paragraph 2 — Name 2-3 SPECIFIC moments of struggle you witnessed, with quoted phrases and context.
  Paragraph 3 — Name 2 SPECIFIC moments of strength, regulation, or self-kindness you witnessed, with specifics.
  Paragraph 4 — Gently reflect on ONE recurring pattern (trigger, self-talk loop, escalation) you noticed, non-judgmentally.
  Paragraph 5 — Acknowledge what was HARD this week, and validate that the effort mattered even if the feelings didn't resolve.
  Paragraph 6 — Offer 2-3 gentle invitations for the coming week ("מוזמן לשים לב", "אפשר לנסות"). No orders.
  Paragraph 7 — Close with one warm, specific sentence of recognition — not praise, recognition.

Output JSON: {"user_reflection": str}
""",
            expected_output="JSON with a 500-650 word, deeply personalized, quote-rich user_reflection string, paragraphs separated by \\n\\n",
            agent=user_reflection_agent(),
        ),
    ]
