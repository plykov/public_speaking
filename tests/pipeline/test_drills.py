from __future__ import annotations

from api.pipeline.drills import DEFAULT_DRILL, recommend_drill
from api.pipeline.llm import FeedbackItemDraft


def _item(criterion: str) -> FeedbackItemDraft:
    return FeedbackItemDraft(
        criterion=criterion,
        observation="o",
        rationale="r",
        repair="f",
        evidence_text="x",
        evidence_start_ms=0,
        evidence_end_ms=100,
    )


def test_recommends_default_drill_when_no_feedback() -> None:
    drill = recommend_drill([])
    assert drill.id == DEFAULT_DRILL["id"]
    assert drill.targets_criterion is None


def test_recommends_catalog_drill_for_top_item() -> None:
    items = [_item("structure"), _item("concision")]
    drill = recommend_drill(items)
    assert drill.targets_criterion == "structure"
    assert drill.id == "drill-structure-01"


def test_falls_back_to_default_for_unmapped_criterion() -> None:
    drill = recommend_drill([_item("evidence")])
    assert drill.id == DEFAULT_DRILL["id"]
    assert drill.targets_criterion == "evidence"
