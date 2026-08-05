"""Words-per-minute: overall and rolling window (§4.1 M3)."""

from __future__ import annotations

from metrics.models import MetricEvent, Word


def compute_wpm(
    words: list[Word],
    window_ms: int = 30_000,
    step_ms: int = 10_000,
) -> tuple[float, list[MetricEvent]]:
    """Return (overall_wpm, rolling_wpm_events).

    Overall WPM uses total elapsed time from the first word's start to the
    last word's end. Rolling WPM is sampled every `step_ms` over a
    `window_ms`-wide window, reported as a `MetricEvent` of type
    "wpm_rolling" whose `value` is the WPM for that window.
    """
    if not words:
        return 0.0, []

    total_ms = words[-1].end_ms - words[0].start_ms
    overall_wpm = (len(words) / total_ms) * 60_000 if total_ms > 0 else 0.0

    events: list[MetricEvent] = []
    start = words[0].start_ms
    end = words[-1].end_ms
    window_start = start
    while window_start < end:
        window_end = window_start + window_ms
        count = sum(1 for w in words if window_start <= w.start_ms < window_end)
        span_ms = min(window_end, end) - window_start
        wpm = (count / span_ms) * 60_000 if span_ms > 0 else 0.0
        events.append(
            MetricEvent(
                type="wpm_rolling",
                start_ms=window_start,
                end_ms=min(window_end, end),
                value=round(wpm, 1),
            )
        )
        window_start += step_ms

    return round(overall_wpm, 1), events
