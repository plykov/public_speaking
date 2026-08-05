"""Speaking time and longest unbroken run (§4.1 M3)."""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import Word


@dataclass
class SpeakingTimeSummary:
    speaking_time_ms: int
    total_duration_ms: int
    longest_run_ms: int


def compute_speaking_time(
    words: list[Word], silence_gap_ms: int = 500
) -> SpeakingTimeSummary:
    """`speaking_time_ms` sums each word's duration. `longest_run_ms` is the
    longest stretch of words with no gap >= `silence_gap_ms` between them.
    """
    if not words:
        return SpeakingTimeSummary(0, 0, 0)

    speaking_time_ms = sum(w.duration_ms for w in words)
    total_duration_ms = words[-1].end_ms - words[0].start_ms

    longest_run_ms = 0
    run_start = words[0].start_ms
    run_end = words[0].end_ms

    for prev, nxt in zip(words, words[1:]):
        gap = nxt.start_ms - prev.end_ms
        if gap >= silence_gap_ms:
            longest_run_ms = max(longest_run_ms, run_end - run_start)
            run_start = nxt.start_ms
        run_end = nxt.end_ms

    longest_run_ms = max(longest_run_ms, run_end - run_start)

    return SpeakingTimeSummary(speaking_time_ms, total_duration_ms, longest_run_ms)
