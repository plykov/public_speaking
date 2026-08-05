from __future__ import annotations

from metrics.pauses import compute_pause_distribution
from tests.conftest import make_words


def test_no_pauses_below_threshold():
    words = make_words(
        [("a", 0, 100, 1.0), ("b", 150, 250, 1.0), ("c", 280, 380, 1.0)]
    )
    summary, events = compute_pause_distribution(words, min_pause_ms=200)
    assert summary.count == 0
    assert events == []


def test_boundary_pause_classified_from_terminal_punctuation():
    words = make_words(
        [
            ("done.", 0, 200, 1.0),
            ("next", 900, 1000, 1.0),  # 700ms gap after a sentence end
        ]
    )
    summary, events = compute_pause_distribution(words, min_pause_ms=200)
    assert summary.count == 1
    assert summary.boundary_count == 1
    assert summary.mid_clause_count == 0
    assert events[0].value["kind"] == "boundary"
    assert events[0].value["duration_ms"] == 700


def test_mid_clause_pause_classified_without_terminal_punctuation():
    words = make_words(
        [
            ("waiting", 0, 200, 1.0),
            ("here", 900, 1000, 1.0),
        ]
    )
    summary, events = compute_pause_distribution(words, min_pause_ms=200)
    assert summary.mid_clause_count == 1
    assert summary.boundary_count == 0


def test_summary_stats_mean_and_longest():
    words = make_words(
        [
            ("a", 0, 100, 1.0),
            ("b", 400, 500, 1.0),  # 300ms gap
            ("c", 1500, 1600, 1.0),  # 1000ms gap
        ]
    )
    summary, _ = compute_pause_distribution(words, min_pause_ms=200)
    assert summary.count == 2
    assert summary.longest_ms == 1000
    assert summary.mean_ms == 650.0
