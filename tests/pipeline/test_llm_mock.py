from __future__ import annotations

from metrics.report import compute_metrics
from metrics.text_utils import split_sentences
from tests.conftest import make_words

from api.pipeline.llm import MockLLMRubricProvider, ScenarioRubric


def test_mock_llm_flags_hedging_with_verbatim_evidence() -> None:
    words = make_words(
        [
            ("maybe", 0, 200, 1.0),
            ("we", 210, 300, 1.0),
            ("should", 310, 500, 1.0),
            ("ship", 510, 650, 1.0),
            ("it.", 660, 800, 1.0),
        ]
    )
    sentences = split_sentences(words)
    report = compute_metrics(words)

    result = MockLLMRubricProvider().evaluate(words, sentences, report, ScenarioRubric(id="general"))

    hedge_items = [i for i in result.items if i.criterion == "point_first_clarity"]
    assert hedge_items, "expected a hedging-flagged feedback item"
    assert hedge_items[0].evidence_text == "maybe"
    assert hedge_items[0].evidence_start_ms == 0


def test_mock_llm_flags_late_point_position() -> None:
    words = make_words(
        [
            ("Context", 0, 200, 1.0),
            ("first.", 210, 400, 1.0),
            ("We", 410, 500, 1.0),
            ("should", 510, 700, 1.0),
            ("ship", 710, 850, 1.0),
            ("it.", 860, 1000, 1.0),
        ]
    )
    sentences = split_sentences(words)
    report = compute_metrics(words)

    result = MockLLMRubricProvider().evaluate(words, sentences, report, ScenarioRubric(id="general"))

    structure_items = [i for i in result.items if i.criterion == "structure"]
    assert structure_items
    assert structure_items[0].evidence_text == sentences[0].text


def test_mock_llm_caps_at_three_items() -> None:
    words = make_words(
        [
            ("maybe", 0, 100, 1.0),
            ("um", 110, 200, 1.0),
            ("Context", 210, 300, 1.0),
            ("first.", 310, 400, 1.0),
            ("we", 410, 500, 1.0),
            ("should", 510, 600, 1.0),
            ("ship", 610, 700, 1.0),
            ("it.", 710, 800, 1.0),
        ]
    )
    sentences = split_sentences(words)
    report = compute_metrics(words)

    result = MockLLMRubricProvider().evaluate(words, sentences, report, ScenarioRubric(id="general"))

    assert len(result.items) <= 3
    assert result.model_version == MockLLMRubricProvider.MODEL_VERSION
