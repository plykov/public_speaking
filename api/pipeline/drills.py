"""Repair-loop drill selection (§4.1 M7).

Feedback automatically generates one 2-5 minute drill targeting the top
issue. This is a small static catalog keyed by rubric criterion — the
content-authoring side (§7.3) owns growing it; this module only picks.
"""

from __future__ import annotations

from dataclasses import dataclass

from api.pipeline.llm import FeedbackItemDraft

DRILL_CATALOG: dict[str, dict[str, str]] = {
    "point_first_clarity": {
        "id": "drill-point-first-01",
        "title": "One-breath recommendation",
        "prompt": "State your recommendation in one sentence, under 8 seconds, with no qualifier before it.",
        "duration_minutes": "3",
    },
    "structure": {
        "id": "drill-structure-01",
        "title": "Answer first, context second",
        "prompt": "Given a prompt, answer with the recommendation in sentence one, then explain why in sentences two and three.",
        "duration_minutes": "4",
    },
    "concision": {
        "id": "drill-concision-01",
        "title": "Silent pause swap",
        "prompt": "Re-record the same answer, replacing every filler with a silent pause instead.",
        "duration_minutes": "3",
    },
}

DEFAULT_DRILL = {
    "id": "drill-general-01",
    "title": "General fluency warm-up",
    "prompt": "Answer an impromptu prompt for 60 seconds, prioritising a clear opening sentence.",
    "duration_minutes": "2",
}


@dataclass(frozen=True)
class RecommendedDrill:
    id: str
    title: str
    prompt: str
    duration_minutes: str
    targets_criterion: str | None


def recommend_drill(feedback_items: list[FeedbackItemDraft]) -> RecommendedDrill:
    """Pick one drill targeting the top-ranked (first) surviving feedback item."""
    if not feedback_items:
        return RecommendedDrill(**DEFAULT_DRILL, targets_criterion=None)

    top = feedback_items[0]
    drill = DRILL_CATALOG.get(top.criterion, DEFAULT_DRILL)
    return RecommendedDrill(**drill, targets_criterion=top.criterion)
