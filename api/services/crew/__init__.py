"""CrewAI therapeutic insight crew.

Activated for WEEKLY insights only (per product decision).
Fast per-chunk analysis uses services/analysis.py.
"""
from .insight_crew import WeeklyInsightCrew

__all__ = ["WeeklyInsightCrew"]
