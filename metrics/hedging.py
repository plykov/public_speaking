"""Hedging index (§4.1 M4) — the L2-specific differentiator metric.

Detects hedging constructions with timestamps and attaches a rewrite
suggestion, so the coaching layer (§4.1 M6) can link straight to the
moment and offer a concrete repair rather than an abstract note.
"""

from __future__ import annotations

from metrics.models import MetricEvent, Word
from metrics.text_utils import normalize

# phrase (as a tuple of normalized tokens) -> rewrite suggestion
HEDGING_PHRASES: dict[tuple[str, ...], str] = {
    ("maybe",): "State it directly, or name the specific uncertainty.",
    ("perhaps",): "State it directly, or name the specific uncertainty.",
    ("i", "think"): 'Drop "I think" — say the recommendation, then give your reasoning.',
    ("i", "guess"): 'Drop "I guess" — commit to the point or name what you\'re unsure of.',
    ("i'm", "not", "sure", "but"): "Name the specific uncertainty instead of hedging the whole point.",
    ("im", "not", "sure", "but"): "Name the specific uncertainty instead of hedging the whole point.",
    ("sort", "of"): "Cut the qualifier — say what it is.",
    ("kind", "of"): "Cut the qualifier — say what it is.",
    ("a", "bit"): "Cut the qualifier or replace with a specific quantity.",
    ("just",): 'Drop "just" — it minimizes the point that follows.',
    ("a", "little"): "Cut the qualifier or replace with a specific quantity.",
}

_MAX_PHRASE_LEN = max(len(p) for p in HEDGING_PHRASES)


def compute_hedging_index(words: list[Word]) -> tuple[float, list[MetricEvent]]:
    """Return (rate_per_100_words, timestamped hedge instances with rewrites)."""
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
        matched = False
        for length in range(_MAX_PHRASE_LEN, 0, -1):
            if i + length > len(words):
                continue
            phrase = tuple(normalized[i : i + length])
            if phrase in HEDGING_PHRASES:
                events.append(
                    MetricEvent(
                        type="hedge",
                        start_ms=words[i].start_ms,
                        end_ms=words[i + length - 1].end_ms,
                        value={
                            "phrase": " ".join(phrase),
                            "rewrite_suggestion": HEDGING_PHRASES[phrase],
                        },
                    )
                )
                for j in range(i, i + length):
                    consumed[j] = True
                i += length
                matched = True
                break
        if not matched:
            i += 1

    rate = (len(events) / len(words)) * 100
    return round(rate, 2), events
