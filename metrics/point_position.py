"""Point-position score (§4.1 M4): does the recommendation lead or trail?

Deterministic and rule-based — no semantic judgement, no LLM. Detects the
first sentence containing a recognised recommendation/point marker
("I recommend", "we should", "let's", ...) and scores how early it lands
relative to the whole response. Target is the first sentence (§7.1
Point-first track: BLUF, recommendation before context).

This is a lexical proxy, not an understanding of the point's *quality* —
that judgement belongs to the LLM rubric layer (§4.1 M5), which is scoped
out of this deterministic module.
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import MetricEvent, Sentence
from metrics.text_utils import normalize

# Phrases (as normalized token tuples) that mark a recommendation/point.
POINT_MARKERS: tuple[tuple[str, ...], ...] = (
    ("i", "recommend"),
    ("my", "recommendation", "is"),
    ("we", "should"),
    ("we", "need", "to"),
    ("i", "suggest"),
    ("i", "propose"),
    ("let's",),
    ("lets",),
    ("the", "answer", "is"),
    ("bottom", "line"),
    ("in", "short"),
)


@dataclass
class PointPositionResult:
    found: bool
    sentence_index: int | None
    total_sentences: int
    score: float


def compute_point_position_score(sentences: list[Sentence]) -> tuple[PointPositionResult, list[MetricEvent]]:
    """Score in [0, 1]: 1.0 if the point is in the first sentence, 0.0 if
    it's in the last (or absent). Linear decay by sentence position.
    """
    if not sentences:
        return PointPositionResult(False, None, 0, 0.0), []

    for idx, sentence in enumerate(sentences):
        tokens = tuple(normalize(w.text) for w in sentence.words)
        for marker in POINT_MARKERS:
            n = len(marker)
            for start in range(len(tokens) - n + 1):
                if tokens[start : start + n] == marker:
                    total = len(sentences)
                    score = 1.0 if total == 1 else round(1.0 - idx / (total - 1), 2)
                    result = PointPositionResult(
                        found=True,
                        sentence_index=idx,
                        total_sentences=total,
                        score=score,
                    )
                    event = MetricEvent(
                        type="point_position",
                        start_ms=sentence.start_ms,
                        end_ms=sentence.end_ms,
                        value={
                            "sentence_index": idx,
                            "total_sentences": total,
                            "marker": " ".join(marker),
                        },
                    )
                    return result, [event]

    return PointPositionResult(False, None, len(sentences), 0.0), []
