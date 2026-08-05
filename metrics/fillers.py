"""Filler-word detection and rate (§4.1 M3).

Requires disfluency-preserving transcription (§6.2) — Whisper strips these
tokens, so a filler-rate metric built on Whisper output measures nothing.
This module only detects what actually made it into the transcript.
"""

from __future__ import annotations

from metrics.models import MetricEvent, Word
from metrics.text_utils import normalize

# Single-word disfluency fillers a verbatim/disfluency-mode STT vendor emits.
SINGLE_WORD_FILLERS = frozenset(
    {"um", "umm", "uh", "uhh", "uh-huh", "erm", "er", "ah", "hmm"}
)

# Multi-word filler phrases, checked as a sliding window over normalized words.
MULTI_WORD_FILLERS: tuple[tuple[str, ...], ...] = (
    ("you", "know"),
    ("i", "mean"),
    ("kind", "of", "like"),
)


def compute_filler_rate(words: list[Word]) -> tuple[float, list[MetricEvent]]:
    """Return (rate_per_100_words, timestamped filler instances)."""
    if not words:
        return 0.0, []

    normalized = [normalize(w.text) for w in words]
    events: list[MetricEvent] = []
    consumed = [False] * len(words)

    i = 0
    while i < len(words):
        if consumed[i]:
            i += 1
            continue
        matched_phrase = False
        for phrase in sorted(MULTI_WORD_FILLERS, key=len, reverse=True):
            n = len(phrase)
            if i + n <= len(words) and tuple(normalized[i : i + n]) == phrase:
                events.append(
                    MetricEvent(
                        type="filler",
                        start_ms=words[i].start_ms,
                        end_ms=words[i + n - 1].end_ms,
                        value=" ".join(phrase),
                    )
                )
                for j in range(i, i + n):
                    consumed[j] = True
                i += n
                matched_phrase = True
                break
        if matched_phrase:
            continue
        if normalized[i] in SINGLE_WORD_FILLERS:
            events.append(
                MetricEvent(
                    type="filler",
                    start_ms=words[i].start_ms,
                    end_ms=words[i].end_ms,
                    value=normalized[i],
                )
            )
            consumed[i] = True
        i += 1

    rate = (len(events) / len(words)) * 100
    return round(rate, 2), events
