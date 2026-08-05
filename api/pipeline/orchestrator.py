"""Pipeline orchestrator (§6.3, steps 3-9).

Wires normalization → STT → deterministic metrics → LLM rubric →
evidence validation → drill recommendation. Deliberately a plain
function, not a class: each stage is a pure seam (`AudioNormalizer`,
`STTProvider`, `LLMRubricProvider`) that can be swapped independently,
and the deterministic-metrics call never touches a model.

In production, steps 3-8 run in a Celery/Arq worker off the request
path (§6.1); this function is what that worker task calls.
"""

from __future__ import annotations

from dataclasses import dataclass

from metrics.models import MetricsReport, Word
from metrics.report import compute_metrics
from metrics.text_utils import split_sentences

from api.pipeline.drills import RecommendedDrill, recommend_drill
from api.pipeline.evidence import RejectedItem, validate_evidence
from api.pipeline.llm import FeedbackItemDraft, LLMRubricProvider, ScenarioRubric
from api.pipeline.normalize import AudioNormalizer
from api.pipeline.stt import STTProvider


@dataclass(frozen=True)
class PipelineResult:
    words: tuple[Word, ...]
    transcript_text: str
    metrics: MetricsReport
    feedback_items: tuple[FeedbackItemDraft, ...]
    rejected_items: tuple[RejectedItem, ...]
    drill: RecommendedDrill
    rubric_version: str
    model_version: str


def run_pipeline(
    raw_audio: bytes,
    *,
    normalizer: AudioNormalizer,
    stt_provider: STTProvider,
    llm_provider: LLMRubricProvider,
    rubric: ScenarioRubric,
    rubric_version: str,
) -> PipelineResult:
    normalized = normalizer.normalize(raw_audio)

    words = stt_provider.transcribe(normalized.pcm, normalized.sample_rate)
    sentences = split_sentences(words)

    metrics_report = compute_metrics(words)

    llm_result = llm_provider.evaluate(words, sentences, metrics_report, rubric)

    accepted, rejected = validate_evidence(list(llm_result.items), words)

    drill = recommend_drill(accepted)

    return PipelineResult(
        words=tuple(words),
        transcript_text=" ".join(w.text for w in words),
        metrics=metrics_report,
        feedback_items=tuple(accepted[:3]),  # §4.1 M6: maximum three priorities
        rejected_items=tuple(rejected),
        drill=drill,
        rubric_version=rubric_version,
        model_version=llm_result.model_version,
    )
