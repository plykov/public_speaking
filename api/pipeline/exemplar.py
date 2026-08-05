"""Exemplar mode (§4.2 — "after the user's attempt, show a stronger version
and explain the delta").

Same seam-plus-mock pattern as `api.pipeline.llm`: a real implementation
would ask a frontier model to compose a genuinely stronger, more natural
rewrite. `MockExemplarProvider` is deliberately *not* a language model — it
only reorders and removes what the speaker already said (strip detected
hedges, move the sentence containing a recognized recommendation marker to
the front), using the same deterministic `metrics.hedging`/
`metrics.point_position` detectors already in the pipeline. That keeps it
honest about what it is: a mechanical demonstration of the "show the
delta" UX, not evidence of rewrite quality a real LLM would provide.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from metrics.hedging import compute_hedging_index
from metrics.models import Sentence, Word
from metrics.point_position import compute_point_position_score


@dataclass(frozen=True)
class ExemplarResult:
    original_text: str
    rewritten_text: str
    explanation: list[str]
    model_version: str


def _sentence_text(sentence: Sentence) -> str:
    return " ".join(w.text for w in sentence.words)


def _strip_hedges(words: list[Word]) -> tuple[list[Word], list[str]]:
    _, hedge_events = compute_hedging_index(words)
    if not hedge_events:
        return list(words), []
    removed_ranges = [(e.start_ms, e.end_ms) for e in hedge_events]
    phrases = [(e.value or {}).get("phrase", "") for e in hedge_events]
    kept = [
        w
        for w in words
        if not any(start <= w.start_ms <= end for start, end in removed_ranges)
    ]
    return kept, phrases


class ExemplarProvider(ABC):
    @abstractmethod
    def generate(self, words: list[Word], sentences: list[Sentence]) -> ExemplarResult: ...


class MockExemplarProvider(ExemplarProvider):
    MODEL_VERSION = "mock-exemplar-v1"

    def generate(self, words: list[Word], sentences: list[Sentence]) -> ExemplarResult:
        original_text = " ".join(w.text for w in words)
        explanation: list[str] = []

        point_result, _ = compute_point_position_score(sentences)
        reordered = list(sentences)
        if point_result.found and (point_result.sentence_index or 0) > 0:
            idx = point_result.sentence_index
            moved = reordered.pop(idx)
            reordered.insert(0, moved)
            explanation.append(
                f'Moved your recommendation ("{_sentence_text(moved)}") to the first sentence.'
            )

        rewritten_words: list[Word] = [w for s in reordered for w in s.words]
        stripped_words, hedge_phrases = _strip_hedges(rewritten_words)
        if hedge_phrases:
            quoted = ", ".join(f'"{p}"' for p in hedge_phrases)
            explanation.append(
                f"Removed {len(hedge_phrases)} hedging phrase(s): {quoted}."
            )

        rewritten_text = " ".join(w.text for w in stripped_words)

        if not explanation:
            explanation.append(
                "Your attempt already leads with the point and has no detected hedging — "
                "no structural changes to suggest here."
            )

        return ExemplarResult(
            original_text=original_text,
            rewritten_text=rewritten_text or original_text,
            explanation=explanation,
            model_version=self.MODEL_VERSION,
        )


def get_exemplar_provider(name: str) -> ExemplarProvider:
    if name == "mock":
        return MockExemplarProvider()
    raise NotImplementedError(
        f"Exemplar provider {name!r} is not wired up yet — integrate a frontier model "
        "behind this same ExemplarProvider interface, transcript-only, no raw audio."
    )
