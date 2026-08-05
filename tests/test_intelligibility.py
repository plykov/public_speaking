from __future__ import annotations

from metrics.intelligibility import compute_intelligibility_proxy
from tests.conftest import make_words


def test_high_confidence_normal_pace_no_flags():
    words = make_words(
        [(f"w{i}", i * 300, i * 300 + 250, 0.95) for i in range(10)]
    )
    summary, events = compute_intelligibility_proxy(words)
    assert events == []
    assert summary.mean_confidence == 0.95


def test_low_confidence_fast_stretch_flagged():
    # 8 words crammed into 1000ms (~480 wpm) with low confidence.
    words = make_words(
        [(f"w{i}", i * 125, i * 125 + 100, 0.4) for i in range(8)]
    )
    summary, events = compute_intelligibility_proxy(words, window_words=8)
    assert summary.flagged_stretch_count == 1
    assert events[0].type == "low_intelligibility_stretch"
    assert events[0].value["mean_confidence"] < 0.6


def test_low_confidence_but_slow_pace_not_flagged():
    words = make_words(
        [(f"w{i}", i * 1000, i * 1000 + 200, 0.4) for i in range(8)]
    )
    summary, events = compute_intelligibility_proxy(words, window_words=8)
    assert events == []
