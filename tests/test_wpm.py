from __future__ import annotations

from metrics.wpm import compute_wpm
from tests.conftest import make_words


def test_empty_words_returns_zero():
    overall, events = compute_wpm([])
    assert overall == 0.0
    assert events == []


def test_overall_wpm_matches_hand_calculation():
    words = make_words(
        [(f"w{i}", i * 1000, i * 1000 + 200, 1.0) for i in range(5)]
    )
    overall, _ = compute_wpm(words)
    # total_ms = 4200 (last end 4200 - first start 0); 5 words
    expected = round((5 / 4200) * 60_000, 1)
    assert overall == expected


def test_rolling_window_produces_events_covering_full_span():
    words = make_words(
        [(f"w{i}", i * 1000, i * 1000 + 200, 1.0) for i in range(10)]
    )
    _, events = compute_wpm(words, window_ms=3000, step_ms=1000)
    assert all(e.type == "wpm_rolling" for e in events)
    assert events[0].start_ms == 0
    assert events[-1].end_ms <= words[-1].end_ms
    assert all(e.value >= 0 for e in events)


def test_zero_duration_span_has_zero_overall_wpm():
    words = make_words([("hello", 0, 0, 1.0)])
    overall, events = compute_wpm(words)
    assert overall == 0.0
    assert events == []
