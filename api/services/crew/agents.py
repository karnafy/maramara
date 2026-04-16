"""CrewAI agent definitions - 10 specialized therapeutic agents."""
from __future__ import annotations

from functools import lru_cache
from crewai import Agent
from langchain_anthropic import ChatAnthropic

from config import get_settings


@lru_cache(maxsize=1)
def _llm() -> ChatAnthropic:
    s = get_settings()
    return ChatAnthropic(
        model=s.crewai_model,
        api_key=s.anthropic_api_key,
        temperature=0.3,
        max_tokens=2048,
    )


def trigger_pattern_agent() -> Agent:
    return Agent(
        role="Emotional Trigger Analyst",
        goal="Identify recurring emotional triggers across the user's weekly speech data.",
        backstory=(
            "A clinical psychologist specializing in cognitive-behavioural pattern recognition. "
            "You look at transcripts, topics, and intensity peaks to find what consistently activates stress."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def regulation_agent() -> Agent:
    return Agent(
        role="Emotional Regulation Analyst",
        goal="Find what consistently calms the user - language, topics, people.",
        backstory=(
            "A DBT-trained therapist focused on identifying self-soothing mechanisms and "
            "external regulators that reliably reduce emotional intensity."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def self_talk_agent() -> Agent:
    return Agent(
        role="Self-Talk Pattern Analyst",
        goal="Map the user's internal dialogue - supportive vs critical vs neutral.",
        backstory=(
            "A cognitive therapy specialist who tracks the ratio of supportive vs critical "
            "self-talk, absolutist language, and compassion toward self over time."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def cognitive_distortions_agent() -> Agent:
    return Agent(
        role="Cognitive Distortion Detector",
        goal="Detect and categorize cognitive distortions in the weekly transcripts.",
        backstory=(
            "A CBT expert trained to spot all-or-nothing thinking, catastrophizing, "
            "mind-reading, personalization, should-statements, and filtering."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def escalation_loop_agent() -> Agent:
    return Agent(
        role="Escalation Loop Analyst",
        goal="Detect recurring Trigger→Escalation→Peak→Recovery cycles.",
        backstory=(
            "A behavioral analyst specialized in stress cycles. You look at intensity over time "
            "to identify loops and quantify time-to-recover."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def phrase_mining_agent() -> Agent:
    return Agent(
        role="Phrase Mining Specialist",
        goal="Extract repeated language patterns - both destructive and healing.",
        backstory=(
            "A linguistic therapist who extracts signature phrases the user repeats under stress "
            "and phrases they use when they regulate themselves."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def progress_agent() -> Agent:
    return Agent(
        role="Progress Comparison Analyst",
        goal="Compare this week to baseline and previous weeks to measure improvement.",
        backstory=(
            "A therapeutic outcome researcher. You compare metrics across time windows and "
            "explain in plain language whether the user is improving, stable, or regressing."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def therapist_summary_agent() -> Agent:
    return Agent(
        role="Therapist Summary Writer",
        goal="Write a clinical-grade paragraph summary addressed to the therapist.",
        backstory=(
            "A clinical documentation specialist. You synthesize other agents' findings into "
            "a 200-300 word summary appropriate for a licensed therapist's review."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def user_reflection_agent() -> Agent:
    return Agent(
        role="User Reflection Writer",
        goal="Write a short, compassionate, non-judgmental reflection for the user.",
        backstory=(
            "An empathic coach. You translate analytical findings into gentle reflective "
            "sentences that the user can read without feeling shamed. Never use words like 'toxic' "
            "or 'bad'. Use phrasing like 'You tended to... during...'."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )


def risk_assessment_agent() -> Agent:
    return Agent(
        role="Risk Assessment Analyst",
        goal="Flag any language indicating self-harm, severe depression, or crisis.",
        backstory=(
            "A mental health first responder. You err on the side of caution and flag anything "
            "that requires human therapist attention."
        ),
        llm=_llm(),
        allow_delegation=False,
        verbose=False,
    )
