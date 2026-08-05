"""Pause distribution: count, mean, longest, mid-clause vs boundary (§4.1 M3)."""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import MetricEvent, Word
from metrics.text_utils import is_sentence_boundary


@dataclass
class PauseSummary:
    count: int
    mean_ms: float
    longest_ms: int
    mid_clause_count: int
    boundary_count: int


def compute_pause_distribution(
    words: list[Word], min_pause_ms: int = 200
) -> tuple[PauseSummary, list[MetricEvent]]:
    """A pause is a gap between consecutive words >= `min_pause_ms`.

    A pause is classified as `boundary` if the preceding word ends a
    sentence (terminal punctuation), otherwise `mid_clause`.
    """
    if len(words) < 2:
        return PauseSummary(0, 0.0, 0, 0, 0), []

    events: list[MetricEvent] = []
    durations: list[int] = []
    mid_clause = 0
    boundary = 0

    for prev, nxt in zip(words, words[1:]):
        gap = nxt.start_ms - prev.end_ms
        if gap < min_pause_ms:
            continue
        durations.append(gap)
        kind = "boundary" if is_sentence_boundary(prev) else "mid_clause"
        if kind == "boundary":
            boundary += 1
        else:
            mid_clause += 1
        events.append(
            MetricEvent(
                type="pause",
                start_ms=prev.end_ms,
                end_ms=nxt.start_ms,
                value={"duration_ms": gap, "kind": kind},
            )
        )

    if not durations:
        return PauseSummary(0, 0.0, 0, 0, 0), []

    summary = PauseSummary(
        count=len(durations),
        mean_ms=round(sum(durations) / len(durations), 1),
        longest_ms=max(durations),
        mid_clause_count=mid_clause,
        boundary_count=boundary,
    )
    return summary, events
