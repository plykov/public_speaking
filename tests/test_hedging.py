from __future__ import annotations

from metrics.hedging import compute_hedging_index
from tests.conftest import make_words


def test_no_hedging():
    words = make_words(
        [("ship", 0, 100, 1.0), ("it", 100, 200, 1.0), ("today", 200, 300, 1.0)]
    )
    rate, events = compute_hedging_index(words)
    assert rate == 0.0
    assert events == []


def test_single_word_hedge_has_rewrite_suggestion():
    words = make_words(
        [("maybe", 0, 100, 1.0), ("we", 100, 200, 1.0), ("ship", 200, 300, 1.0)]
    )
    rate, events = compute_hedging_index(words)
    assert len(events) == 1
    assert events[0].value["phrase"] == "maybe"
    assert "rewrite_suggestion" in events[0].value


def test_multi_word_hedge_detected_as_one_event():
    words = make_words(
        [
            ("i", 0, 100, 1.0),
            ("think", 100, 200, 1.0),
            ("we", 200, 300, 1.0),
            ("should", 300, 400, 1.0),
        ]
    )
    rate, events = compute_hedging_index(words)
    assert len(events) == 1
    assert events[0].value["phrase"] == "i think"
    assert events[0].start_ms == 0
    assert events[0].end_ms == 200


def test_multiple_distinct_hedges_counted_separately():
    words = make_words(
        [
            ("i", 0, 100, 1.0),
            ("think", 100, 200, 1.0),
            ("we", 200, 300, 1.0),
            ("should", 300, 400, 1.0),
            ("just", 400, 500, 1.0),
            ("wait", 500, 600, 1.0),
        ]
    )
    rate, events = compute_hedging_index(words)
    assert len(events) == 2
    phrases = {e.value["phrase"] for e in events}
    assert phrases == {"i think", "just"}
