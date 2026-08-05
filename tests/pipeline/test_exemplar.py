from __future__ import annotations

import pytest

from api.pipeline.exemplar import MockExemplarProvider, get_exemplar_provider
from metrics.models import Word
from metrics.text_utils import split_sentences


def _words(*specs: tuple[str, int, int]) -> list[Word]:
    return [Word(text=t, start_ms=s, end_ms=e, confidence=0.95) for t, s, e in specs]


def test_strips_hedge_and_leaves_structure_when_point_already_first() -> None:
    words = _words(
        ("we", 0, 100),
        ("should", 110, 200),
        ("maybe", 210, 300),
        ("ship", 310, 400),
        ("it.", 410, 500),
    )
    sentences = split_sentences(words)
    result = MockExemplarProvider().generate(words, sentences)

    assert "maybe" not in result.rewritten_text.lower()
    assert result.original_text != result.rewritten_text
    assert any("hedging" in line.lower() for line in result.explanation)


def test_moves_recommendation_sentence_to_front() -> None:
    words = _words(
        ("the", 0, 100),
        ("budget", 110, 200),
        ("is", 210, 300),
        ("tight.", 310, 400),
        ("we", 410, 500),
        ("should", 510, 600),
        ("ship", 610, 700),
        ("it.", 710, 800),
    )
    sentences = split_sentences(words)
    result = MockExemplarProvider().generate(words, sentences)

    assert result.rewritten_text.lower().startswith("we should ship it.")
    assert any("first sentence" in line.lower() for line in result.explanation)


def test_no_changes_when_already_point_first_and_no_hedging() -> None:
    words = _words(
        ("we", 0, 100),
        ("should", 110, 200),
        ("ship", 210, 300),
        ("it.", 310, 400),
    )
    sentences = split_sentences(words)
    result = MockExemplarProvider().generate(words, sentences)

    assert result.rewritten_text == result.original_text
    assert len(result.explanation) == 1
    assert "no structural changes" in result.explanation[0].lower()


def test_empty_words_does_not_crash() -> None:
    result = MockExemplarProvider().generate([], [])
    assert result.original_text == ""
    assert result.rewritten_text == ""


def test_model_version_is_stable() -> None:
    result = MockExemplarProvider().generate([], [])
    assert result.model_version == "mock-exemplar-v1"


def test_get_exemplar_provider_mock() -> None:
    assert isinstance(get_exemplar_provider("mock"), MockExemplarProvider)


def test_get_exemplar_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_exemplar_provider("openai")
