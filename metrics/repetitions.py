"""Repetition and restart detection (§4.1 M3).

Per §6.2, self-repairs and restarts are "substantially harder" to detect
than simple fillers (open models correct them correctly only ~40% of the
time). This module only claims the narrow, reliable case: immediate
word-level repetition. It flags a broader "possible restart" case as a
lower-confidence heuristic and labels it as such rather than reporting a
false precision.
"""

from __future__ import annotations

from metrics.models import MetricEvent, Word
from metrics.text_utils import normalize

RESTART_LOOKAHEAD = 4


def compute_repetition_rate(words: list[Word]) -> tuple[float, list[MetricEvent]]:
    """Return (rate_per_100_words, timestamped instances).

    Two event types:
    - "repetition": the same normalized word immediately repeated
      (e.g. "the the report").
    - "possible_restart": the same normalized word recurs within the next
      `RESTART_LOOKAHEAD` words after a break, a weak proxy for a
      self-correction. Reported with lower confidence and should be
      surfaced to users as "possible", never asserted.
    """
    if len(words) < 2:
        return 0.0, []

    normalized = [normalize(w.text) for w in words]
    events: list[MetricEvent] = []
    consumed = [False] * len(words)

    for i in range(len(words) - 1):
        if consumed[i] or not normalized[i]:
            continue
        if normalized[i] == normalized[i + 1]:
            events.append(
                MetricEvent(
                    type="repetition",
                    start_ms=words[i].start_ms,
                    end_ms=words[i + 1].end_ms,
                    value=words[i].text,
                )
            )
            consumed[i] = True
            consumed[i + 1] = True

    for i in range(len(words)):
        if consumed[i] or not normalized[i]:
            continue
        for j in range(i + 2, min(i + 1 + RESTART_LOOKAHEAD, len(words))):
            if consumed[j]:
                continue
            if normalized[j] == normalized[i]:
                events.append(
                    MetricEvent(
                        type="possible_restart",
                        start_ms=words[i].start_ms,
                        end_ms=words[j].end_ms,
                        value=words[i].text,
                    )
                )
                consumed[i] = True
                consumed[j] = True
                break

    rate = (len(events) / len(words)) * 100
    return round(rate, 2), events
