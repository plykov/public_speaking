"""Evidence validator (§6.3 step 7).

Every quoted span an LLM (or the mock rubric provider) produces must
exist verbatim — modulo case and punctuation — in the transcript at the
timestamps claimed. An item that fails this check is dropped rather
than surfaced: "fail the item if not, never surface an unverifiable
claim."
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import Word
from metrics.text_utils import normalize

from api.pipeline.llm import FeedbackItemDraft


@dataclass(frozen=True)
class RejectedItem:
    item: FeedbackItemDraft
    reason: str


def _normalized_span_text(words: list[Word], start_ms: int, end_ms: int) -> str:
    span_words = [w for w in words if w.start_ms >= start_ms and w.end_ms <= end_ms]
    return " ".join(normalize(w.text) for w in span_words if normalize(w.text))


def validate_evidence(
    items: list[FeedbackItemDraft], words: list[Word]
) -> tuple[list[FeedbackItemDraft], list[RejectedItem]]:
    accepted: list[FeedbackItemDraft] = []
    rejected: list[RejectedItem] = []

    for item in items:
        if item.evidence_end_ms < item.evidence_start_ms:
            rejected.append(RejectedItem(item, "evidence_end_ms before evidence_start_ms"))
            continue

        span_text = _normalized_span_text(words, item.evidence_start_ms, item.evidence_end_ms)
        evidence_normalized = normalize(item.evidence_text)

        if not evidence_normalized:
            rejected.append(RejectedItem(item, "evidence_text is empty after normalization"))
            continue

        if evidence_normalized not in span_text.replace(" ", ""):
            rejected.append(
                RejectedItem(
                    item,
                    f"evidence_text {item.evidence_text!r} not found verbatim "
                    f"in transcript span [{item.evidence_start_ms}, {item.evidence_end_ms}]ms",
                )
            )
            continue

        accepted.append(item)

    return accepted, rejected
