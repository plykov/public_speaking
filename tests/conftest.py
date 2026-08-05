from __future__ import annotations

from metrics.models import Word


def make_words(specs: list[tuple[str, int, int, float]]) -> list[Word]:
    """specs: list of (text, start_ms, end_ms, confidence)."""
    return [Word(text=t, start_ms=s, end_ms=e, confidence=c) for t, s, e, c in specs]
