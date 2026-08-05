from __future__ import annotations

from metrics.point_position import compute_point_position_score
from metrics.text_utils import split_sentences
from tests.conftest import make_words


def test_no_sentences_returns_not_found():
    result, events = compute_point_position_score([])
    assert result.found is False
    assert result.score == 0.0
    assert events == []


def test_point_in_first_sentence_scores_one():
    words = make_words(
        [
            ("we", 0, 100, 1.0),
            ("should", 100, 200, 1.0),
            ("ship", 200, 300, 1.0),
            ("today.", 300, 400, 1.0),
            ("the", 500, 600, 1.0),
            ("market", 600, 700, 1.0),
            ("is", 700, 800, 1.0),
            ("ready.", 800, 900, 1.0),
        ]
    )
    sentences = split_sentences(words)
    result, events = compute_point_position_score(sentences)
    assert result.found is True
    assert result.sentence_index == 0
    assert result.score == 1.0
    assert events[0].type == "point_position"


def test_point_in_last_sentence_scores_zero():
    words = make_words(
        [
            ("the", 0, 100, 1.0),
            ("market", 100, 200, 1.0),
            ("shifted.", 200, 300, 1.0),
            ("costs", 400, 500, 1.0),
            ("rose.", 500, 600, 1.0),
            ("we", 700, 800, 1.0),
            ("should", 800, 900, 1.0),
            ("ship.", 900, 1000, 1.0),
        ]
    )
    sentences = split_sentences(words)
    result, _ = compute_point_position_score(sentences)
    assert result.found is True
    assert result.sentence_index == 2
    assert result.score == 0.0


def test_no_marker_found():
    words = make_words(
        [
            ("the", 0, 100, 1.0),
            ("weather", 100, 200, 1.0),
            ("is", 200, 300, 1.0),
            ("nice.", 300, 400, 1.0),
        ]
    )
    sentences = split_sentences(words)
    result, events = compute_point_position_score(sentences)
    assert result.found is False
    assert events == []
