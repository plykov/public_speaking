"""LLM rubric-evaluation stage (§4.1 M5, §6.3 step 6).

Receives the transcript + scenario rubric + deterministic metrics.
**Never receives raw audio.** Returns structured output with mandatory
evidence spans so every claim can be checked against the transcript
before it reaches a user (see `evidence.py`).

`MockLLMRubricProvider` is a deterministic, rule-based stand-in for a
real frontier-model call. It is intentionally *not* a language model —
it derives feedback straight from the deterministic metrics module
(hedging instances, point-position, filler rate), which keeps it fully
reproducible for tests and demonstrates the evidence-linked-feedback
contract a real LLM provider must also satisfy. Swap in a real provider
behind the same `LLMRubricProvider` interface; keep raw audio out of
the prompt.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from metrics.models import MetricsReport, Sentence, Word


@dataclass(frozen=True)
class ScenarioRubric:
    id: str
    criteria: tuple[str, ...] = (
        "point_first_clarity",
        "structure",
        "concision",
        "relevance",
        "evidence",
        "call_to_action",
    )


@dataclass(frozen=True)
class FeedbackItemDraft:
    criterion: str
    observation: str
    rationale: str
    repair: str
    evidence_text: str
    evidence_start_ms: int
    evidence_end_ms: int


@dataclass(frozen=True)
class LLMRubricResult:
    items: tuple[FeedbackItemDraft, ...]
    model_version: str


class LLMRubricProvider(ABC):
    @abstractmethod
    def evaluate(
        self,
        words: list[Word],
        sentences: list[Sentence],
        metrics_report: MetricsReport,
        rubric: ScenarioRubric,
    ) -> LLMRubricResult: ...


class MockLLMRubricProvider(LLMRubricProvider):
    MODEL_VERSION = "mock-llm-v1"

    def evaluate(
        self,
        words: list[Word],
        sentences: list[Sentence],
        metrics_report: MetricsReport,
        rubric: ScenarioRubric,
    ) -> LLMRubricResult:
        items: list[FeedbackItemDraft] = []

        hedges = metrics_report.events_of_type("hedge")
        if hedges:
            e = hedges[0]
            phrase = (e.value or {}).get("phrase", "")
            suggestion = (e.value or {}).get("rewrite_suggestion", "State it directly.")
            items.append(
                FeedbackItemDraft(
                    criterion="point_first_clarity",
                    observation=f'You hedged with "{phrase}".',
                    rationale="Hedging in the opening of a point reads as tentative rather than authoritative.",
                    repair=suggestion,
                    evidence_text=phrase,
                    evidence_start_ms=e.start_ms,
                    evidence_end_ms=e.end_ms,
                )
            )

        if sentences:
            point_summary = metrics_report.summary.get("point_position", {})
            point_found = point_summary.get("found", False)
            point_sentence_index = point_summary.get("sentence_index")
            if not point_found or (point_sentence_index or 0) > 0:
                first = sentences[0]
                items.append(
                    FeedbackItemDraft(
                        criterion="structure",
                        observation="Your recommendation did not appear in the first sentence.",
                        rationale="Point-first structure lets a busy meeting track the recommendation before the reasoning.",
                        repair="Open with the recommendation, then give the one or two reasons behind it.",
                        evidence_text=first.text,
                        evidence_start_ms=first.start_ms,
                        evidence_end_ms=first.end_ms,
                    )
                )

        fillers = metrics_report.events_of_type("filler")
        filler_rate = metrics_report.summary.get("filler_rate_per_100_words", 0)
        if fillers and filler_rate >= 5:
            e = fillers[0]
            filler_text = e.value or ""
            items.append(
                FeedbackItemDraft(
                    criterion="concision",
                    observation=f'Filler rate is {filler_rate:.1f} per 100 words, e.g. "{filler_text}".',
                    rationale="Frequent fillers make it harder for listeners to track the point at speed.",
                    repair="Pause silently instead of filling the gap with a filler word.",
                    evidence_text=filler_text,
                    evidence_start_ms=e.start_ms,
                    evidence_end_ms=e.end_ms,
                )
            )

        return LLMRubricResult(items=tuple(items[:3]), model_version=self.MODEL_VERSION)


def get_llm_provider(name: str) -> LLMRubricProvider:
    if name == "mock":
        return MockLLMRubricProvider()
    raise NotImplementedError(
        f"LLM provider {name!r} is not wired up yet — integrate a frontier model "
        "behind this same LLMRubricProvider interface, transcript+metrics only, no raw audio."
    )
