from __future__ import annotations

from tests.conftest import make_words

from api.pipeline.evidence import validate_evidence
from api.pipeline.llm import FeedbackItemDraft


def _item(**overrides) -> FeedbackItemDraft:
    base = dict(
        criterion="structure",
        observation="obs",
        rationale="why",
        repair="fix",
        evidence_text="we should ship it",
        evidence_start_ms=0,
        evidence_end_ms=800,
    )
    base.update(overrides)
    return FeedbackItemDraft(**base)


def test_accepts_evidence_that_matches_transcript_span() -> None:
    words = make_words(
        [
            ("We", 0, 200, 1.0),
            ("should", 210, 400, 1.0),
            ("ship", 410, 600, 1.0),
            ("it.", 610, 800, 1.0),
        ]
    )
    accepted, rejected = validate_evidence([_item()], words)

    assert len(accepted) == 1
    assert rejected == []


def test_rejects_evidence_text_not_present_in_transcript() -> None:
    words = make_words(
        [
            ("We", 0, 200, 1.0),
            ("should", 210, 400, 1.0),
            ("ship", 410, 600, 1.0),
            ("it.", 610, 800, 1.0),
        ]
    )
    fabricated = _item(evidence_text="this was never said")

    accepted, rejected = validate_evidence([fabricated], words)

    assert accepted == []
    assert len(rejected) == 1
    assert "not found verbatim" in rejected[0].reason


def test_rejects_inverted_timestamp_range() -> None:
    words = make_words([("We", 0, 200, 1.0)])
    bad = _item(evidence_start_ms=800, evidence_end_ms=0)

    accepted, rejected = validate_evidence([bad], words)

    assert accepted == []
    assert "before" in rejected[0].reason


def test_rejects_evidence_outside_claimed_timestamp_window() -> None:
    words = make_words(
        [
            ("We", 0, 200, 1.0),
            ("should", 210, 400, 1.0),
            ("ship", 410, 600, 1.0),
            ("it.", 610, 800, 1.0),
        ]
    )
    # Text is real, but claims a timestamp window that doesn't contain it.
    wrong_window = _item(evidence_start_ms=0, evidence_end_ms=200)

    accepted, rejected = validate_evidence([wrong_window], words)

    assert accepted == []
    assert len(rejected) == 1
