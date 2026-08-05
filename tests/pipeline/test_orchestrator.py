from __future__ import annotations

import json

from api.pipeline.llm import MockLLMRubricProvider, ScenarioRubric
from api.pipeline.normalize import PassthroughNormalizer
from api.pipeline.orchestrator import run_pipeline
from api.pipeline.stt import MockSTTProvider


def _audio_for(words: list[dict]) -> bytes:
    return json.dumps(words).encode("utf-8")


def test_run_pipeline_end_to_end() -> None:
    audio = _audio_for(
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.9},
            {"text": "we", "start_ms": 210, "end_ms": 300, "confidence": 0.95},
            {"text": "should", "start_ms": 310, "end_ms": 500, "confidence": 0.95},
            {"text": "ship", "start_ms": 510, "end_ms": 650, "confidence": 0.95},
            {"text": "it.", "start_ms": 660, "end_ms": 800, "confidence": 0.95},
        ]
    )

    result = run_pipeline(
        audio,
        normalizer=PassthroughNormalizer(),
        stt_provider=MockSTTProvider(),
        llm_provider=MockLLMRubricProvider(),
        rubric=ScenarioRubric(id="standup"),
        rubric_version="rubric-v1",
    )

    assert result.transcript_text == "maybe we should ship it."
    assert result.metrics.summary["word_count"] == 5
    assert len(result.feedback_items) <= 3
    assert result.rejected_items == ()  # mock provider only emits verifiable evidence
    assert result.rubric_version == "rubric-v1"
    assert result.model_version == MockLLMRubricProvider.MODEL_VERSION
    assert result.drill.targets_criterion in {i.criterion for i in result.feedback_items} | {None}


def test_run_pipeline_is_deterministic() -> None:
    audio = _audio_for(
        [
            {"text": "we", "start_ms": 0, "end_ms": 200},
            {"text": "should", "start_ms": 210, "end_ms": 400},
            {"text": "ship", "start_ms": 410, "end_ms": 600},
            {"text": "it.", "start_ms": 610, "end_ms": 800},
        ]
    )

    kwargs = dict(
        normalizer=PassthroughNormalizer(),
        stt_provider=MockSTTProvider(),
        llm_provider=MockLLMRubricProvider(),
        rubric=ScenarioRubric(id="standup"),
        rubric_version="rubric-v1",
    )

    first = run_pipeline(audio, **kwargs)
    second = run_pipeline(audio, **kwargs)

    assert first.metrics.summary == second.metrics.summary
    assert first.feedback_items == second.feedback_items
