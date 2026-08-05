"""Intelligibility proxy (§4.1 M4).

Combines per-word ASR confidence with local rate-of-speech to flag
stretches that are hard to follow at the pace they were spoken. Framed to
users as a pacing note ("this section is hard to follow at that pace"),
never as a judgement on accent — confidence dips alone are not reported
without a corroborating rate-of-speech spike, since low confidence alone
is at least as likely to be an ASR/audio-quality artefact as a speaker
issue.
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import MetricEvent, Word

DEFAULT_CONFIDENCE_THRESHOLD = 0.6
DEFAULT_WPM_THRESHOLD = 170.0
DEFAULT_WINDOW_WORDS = 8


@dataclass
class IntelligibilitySummary:
    mean_confidence: float
    flagged_stretch_count: int


def compute_intelligibility_proxy(
    words: list[Word],
    confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD,
    wpm_threshold: float = DEFAULT_WPM_THRESHOLD,
    window_words: int = DEFAULT_WINDOW_WORDS,
) -> tuple[IntelligibilitySummary, list[MetricEvent]]:
    if not words:
        return IntelligibilitySummary(0.0, 0), []

    mean_confidence = round(sum(w.confidence for w in words) / len(words), 3)

    events: list[MetricEvent] = []
    i = 0
    while i < len(words):
        window = words[i : i + window_words]
        if len(window) < 2:
            break
        window_confidence = sum(w.confidence for w in window) / len(window)
        span_ms = window[-1].end_ms - window[0].start_ms
        window_wpm = (len(window) / span_ms) * 60_000 if span_ms > 0 else 0.0

        if window_confidence < confidence_threshold and window_wpm > wpm_threshold:
            events.append(
                MetricEvent(
                    type="low_intelligibility_stretch",
                    start_ms=window[0].start_ms,
                    end_ms=window[-1].end_ms,
                    value={
                        "mean_confidence": round(window_confidence, 3),
                        "wpm": round(window_wpm, 1),
                    },
                )
            )
            i += window_words
        else:
            i += 1

    return IntelligibilitySummary(mean_confidence, len(events)), events
