from __future__ import annotations

from metrics.fillers import compute_filler_rate
from tests.conftest import make_words


def test_no_fillers():
    words = make_words(
        [
            ("we", 0, 100, 1.0),
            ("should", 100, 200, 1.0),
            ("ship", 200, 300, 1.0),
        ]
    )
    rate, events = compute_filler_rate(words)
    assert rate == 0.0
    assert events == []


def test_single_word_filler_detected_with_timestamp():
    words = make_words(
        [
            ("so", 0, 100, 1.0),
            ("um", 100, 250, 1.0),
            ("we", 250, 350, 1.0),
            ("should", 350, 450, 1.0),
        ]
    )
    rate, events = compute_filler_rate(words)
    assert len(events) == 1
    assert events[0].type == "filler"
    assert events[0].value == "um"
    assert events[0].start_ms == 100
    assert events[0].end_ms == 250
    assert rate == 25.0  # 1 filler / 4 words * 100


def test_multi_word_filler_detected_as_single_event():
    words = make_words(
        [
            ("you", 0, 100, 1.0),
            ("know", 100, 200, 1.0),
            ("it", 200, 300, 1.0),
            ("works", 300, 400, 1.0),
        ]
    )
    rate, events = compute_filler_rate(words)
    assert len(events) == 1
    assert events[0].value == "you know"
    assert events[0].start_ms == 0
    assert events[0].end_ms == 200


def test_filler_matching_is_case_and_punctuation_insensitive():
    words = make_words([("Um,", 0, 100, 1.0), ("okay.", 100, 200, 1.0)])
    rate, events = compute_filler_rate(words)
    assert len(events) == 1
    assert events[0].value == "um"
