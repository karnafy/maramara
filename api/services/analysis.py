"""Per-segment NLP analysis via Claude/Gemini (layers 2-9 of the pipeline).

Output schema matches `segment_analysis` table columns.
"""
from __future__ import annotations

import json
from functools import lru_cache

from config import get_settings
from utils.logger import get_logger

log = get_logger(__name__)


SYSTEM_PROMPT_HE = """אתה מנתח דיבור טיפולי. קבל קטע שיח של משתמש ותחזיר JSON בלבד עם השדות הבאים:
- polarity: אחד מ "positive","neutral","negative","mixed"
- intensity_score: מספר 0-10
- complaint_score: 0-1
- curse_score: 0-1
- calming_score: 0-1
- self_talk_score: 0-1 (כמה המשתמש מדבר על עצמו)
- self_criticism_score: 0-1
- absolutism_score: 0-1 ("תמיד","אף פעם","בכלל")
- blame_score: 0-1
- primary_topic: קטגוריה (work/relationships/family/health/money/self/environment/other)
- secondary_topic: קטגוריה משנית או null
- trigger_detected: true אם יש טריגר ברור
- trigger_description: תיאור קצר בעברית (מקסימום 120 תווים) או null
- calming_detected: true אם יש אלמנט מרגיע
- calming_description: תיאור קצר בעברית (מקסימום 120 תווים) או null
- cognitive_patterns: מערך של ["catastrophizing","all_or_nothing","personalization","should_statements","mind_reading","filtering"] - רק מה שקיים
- tags: מערך של עד 5 מילות מפתח חשובות
- detected_terms: מערך אובייקטים {term, type} כאשר type הוא positive/negative/curse/trigger/calming/gratitude/self_criticism/absolutist

החזר JSON בלבד, ללא הסבר, ללא Markdown."""


SYSTEM_PROMPT_EN = """You are a therapeutic speech analyzer. Receive a user speech segment and return ONLY JSON with fields:
- polarity: one of "positive","neutral","negative","mixed"
- intensity_score: 0-10
- complaint_score: 0-1
- curse_score: 0-1
- calming_score: 0-1
- self_talk_score: 0-1 (user speaking about self)
- self_criticism_score: 0-1
- absolutism_score: 0-1 ("always","never","completely")
- blame_score: 0-1
- primary_topic: category (work/relationships/family/health/money/self/environment/other)
- secondary_topic: secondary category or null
- trigger_detected: true if clear trigger
- trigger_description: short text ≤120 chars or null
- calming_detected: true if calming element
- calming_description: short text ≤120 chars or null
- cognitive_patterns: array of ["catastrophizing","all_or_nothing","personalization","should_statements","mind_reading","filtering"]
- tags: array of up to 5 keyword tags
- detected_terms: array of {term,type} where type is positive/negative/curse/trigger/calming/gratitude/self_criticism/absolutist

Return ONLY JSON. No prose. No markdown."""


@lru_cache(maxsize=1)
def _anthropic_client():
    from anthropic import Anthropic
    settings = get_settings()
    return Anthropic(api_key=settings.anthropic_api_key)


class AnalysisService:
    """Single-segment analyzer. Called per-chunk from worker."""

    def analyze(self, transcript_text: str, language: str = "he") -> dict:
        if not transcript_text.strip():
            return self._empty_result()

        prompt = SYSTEM_PROMPT_HE if language == "he" else SYSTEM_PROMPT_EN
        client = _anthropic_client()
        try:
            resp = client.messages.create(
                model=get_settings().crewai_model,
                max_tokens=1024,
                system=prompt,
                messages=[{"role": "user", "content": transcript_text}],
            )
            raw = resp.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.strip("`").split("\n", 1)[-1]
                if raw.endswith("```"):
                    raw = raw[:-3]
            data = json.loads(raw)
            data["llm_model_used"] = get_settings().crewai_model
            return data
        except Exception as e:
            log.error("analysis_failed", error=str(e), transcript_preview=transcript_text[:80])
            return self._empty_result(error=str(e))

    @staticmethod
    def _empty_result(error: str | None = None) -> dict:
        return {
            "polarity": "neutral",
            "intensity_score": 0.0,
            "complaint_score": 0.0,
            "curse_score": 0.0,
            "calming_score": 0.0,
            "self_talk_score": 0.0,
            "self_criticism_score": 0.0,
            "absolutism_score": 0.0,
            "blame_score": 0.0,
            "primary_topic": "other",
            "secondary_topic": None,
            "trigger_detected": False,
            "trigger_description": None,
            "calming_detected": False,
            "calming_description": None,
            "cognitive_patterns": [],
            "tags": [],
            "detected_terms": [],
            "llm_model_used": None,
            "_error": error,
        }
