from __future__ import annotations

import numpy as np

from metrics.report import compute_metrics
from tests.conftest import make_words


def _sample_words():
    # "So, um, I think we should maybe ship it today. The market is ready."
    specs = [
        ("So,", 0, 150, 0.95),
        ("um,", 150, 350, 0.9),
        ("I", 350, 450, 0.97),
        ("think", 450, 600, 0.96),
        ("we", 600, 700, 0.98),
        ("should", 700, 850, 0.97),
        ("maybe", 850, 1050, 0.95),
        ("ship", 1050, 1200, 0.96),
        ("it", 1200, 1300, 0.97),
        ("today.", 1300, 1500, 0.95),
        ("The", 2000, 2100, 0.96),
        ("market", 2100, 2300, 0.95),
        ("is", 2300, 2400, 0.97),
        ("ready.", 2400, 2600, 0.96),
    ]
    return make_words(specs)


def test_empty_input_returns_empty_report():
    report = compute_metrics([])
    assert report.summary == {}
    assert report.events == []


def test_report_contains_all_expected_summary_keys():
    report = compute_metrics(_sample_words())
    expected_keys = {
        "wpm_overall",
        "filler_rate_per_100_words",
        "pause",
        "repetition_rate_per_100_words",
        "hedging_rate_per_100_words",
        "point_position",
        "intelligibility",
        "speaking_time",
        "word_count",
        "sentence_count",
    }
    assert expected_keys.issubset(report.summary.keys())
    assert report.summary["word_count"] == 14
    assert report.summary["sentence_count"] == 2


def test_report_detects_filler_and_hedge_and_point_position():
    report = compute_metrics(_sample_words())
    filler_events = report.events_of_type("filler")
    hedge_events = report.events_of_type("hedge")
    point_events = report.events_of_type("point_position")

    assert any(e.value == "um" for e in filler_events)
    assert any(e.value["phrase"] == "i think" for e in hedge_events)
    assert any(e.value["phrase"] == "maybe" for e in hedge_events)
    # The recommendation ("we should ... ship it today") is in sentence 0 of 2.
    assert point_events[0].value["sentence_index"] == 0


def test_report_is_deterministic_across_repeated_runs():
    words = _sample_words()
    report_a = compute_metrics(words)
    report_b = compute_metrics(words)
    assert report_a.summary == report_b.summary
    assert [e.__dict__ for e in report_a.events] == [e.__dict__ for e in report_b.events]


def test_report_includes_prosody_when_audio_provided():
    words = _sample_words()
    sample_rate = 16000
    duration_s = 2.6
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    audio = 0.5 * np.sin(2 * np.pi * 140 * t)

    report = compute_metrics(words, audio_samples=audio, audio_sample_rate=sample_rate)
    assert "prosody" in report.summary


def test_report_omits_prosody_without_audio():
    report = compute_metrics(_sample_words())
    assert "prosody" not in report.summary
