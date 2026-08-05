from __future__ import annotations

from metrics.speaking_time import compute_speaking_time
from tests.conftest import make_words


def test_empty_words():
    summary = compute_speaking_time([])
    assert summary.speaking_time_ms == 0
    assert summary.longest_run_ms == 0


def test_continuous_speech_is_one_run():
    words = make_words(
        [("a", 0, 200, 1.0), ("b", 200, 400, 1.0), ("c", 400, 600, 1.0)]
    )
    summary = compute_speaking_time(words, silence_gap_ms=500)
    assert summary.speaking_time_ms == 600
    assert summary.total_duration_ms == 600
    assert summary.longest_run_ms == 600


def test_silence_gap_splits_runs():
    words = make_words(
        [
            ("a", 0, 200, 1.0),
            ("b", 200, 400, 1.0),  # run 1: 0-400 (400ms)
            ("c", 1500, 1700, 1.0),
            ("d", 1700, 1900, 1.0),
            ("e", 1900, 2600, 1.0),  # run 2: 1500-2600 (1100ms)
        ]
    )
    summary = compute_speaking_time(words, silence_gap_ms=500)
    assert summary.longest_run_ms == 1100
