from __future__ import annotations

from metrics.repetitions import compute_repetition_rate
from tests.conftest import make_words


def test_no_repetition():
    words = make_words(
        [("we", 0, 100, 1.0), ("should", 100, 200, 1.0), ("ship", 200, 300, 1.0)]
    )
    rate, events = compute_repetition_rate(words)
    assert rate == 0.0
    assert events == []


def test_immediate_repetition_detected():
    words = make_words(
        [
            ("the", 0, 100, 1.0),
            ("the", 100, 200, 1.0),
            ("report", 200, 300, 1.0),
        ]
    )
    rate, events = compute_repetition_rate(words)
    assert len(events) == 1
    assert events[0].type == "repetition"
    assert events[0].start_ms == 0
    assert events[0].end_ms == 200


def test_possible_restart_within_lookahead():
    words = make_words(
        [
            ("we", 0, 100, 1.0),
            ("need", 100, 200, 1.0),
            ("we", 200, 300, 1.0),
            ("must", 300, 400, 1.0),
        ]
    )
    rate, events = compute_repetition_rate(words)
    assert len(events) == 1
    assert events[0].type == "possible_restart"


def test_repetition_rate_scales_per_100_words():
    words = make_words(
        [(f"w{i}", i * 100, i * 100 + 100, 1.0) for i in range(8)]
    )
    words[2] = words[2].__class__(text=words[1].text, start_ms=200, end_ms=300, confidence=1.0)
    rate, events = compute_repetition_rate(words)
    assert len(events) == 1
    assert rate == round((1 / 8) * 100, 2)
