"""Aggregates every deterministic metric into one `MetricsReport` (§6.3 step 5).

This is the only entry point the pipeline should call. It never makes a
model/network call — audio in, transcript in, structured metrics out,
always reproducibly.
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

import numpy as np

from metrics.fillers import compute_filler_rate
from metrics.hedging import compute_hedging_index
from metrics.intelligibility import compute_intelligibility_proxy
from metrics.models import MetricsReport, Word
from metrics.pauses import compute_pause_distribution
from metrics.point_position import compute_point_position_score
from metrics.prosody import compute_prosody_metrics
from metrics.repetitions import compute_repetition_rate
from metrics.speaking_time import compute_speaking_time
from metrics.text_utils import split_sentences
from metrics.wpm import compute_wpm


def compute_metrics(
    words: list[Word],
    audio_samples: np.ndarray | None = None,
    audio_sample_rate: int | None = None,
) -> MetricsReport:
    """Compute the full deterministic metrics suite for one attempt.

    `audio_samples`/`audio_sample_rate` are optional — omit them (e.g. when
    only a transcript is available) and prosody metrics are skipped rather
    than fabricated.
    """
    report = MetricsReport()

    if not words:
        return report

    sentences = split_sentences(words)

    overall_wpm, wpm_events = compute_wpm(words)
    filler_rate, filler_events = compute_filler_rate(words)
    pause_summary, pause_events = compute_pause_distribution(words)
    repetition_rate, repetition_events = compute_repetition_rate(words)
    hedging_rate, hedging_events = compute_hedging_index(words)
    point_position, point_events = compute_point_position_score(sentences)
    intelligibility_summary, intelligibility_events = compute_intelligibility_proxy(words)
    speaking_time_summary = compute_speaking_time(words)

    summary: dict[str, Any] = {
        "wpm_overall": overall_wpm,
        "filler_rate_per_100_words": filler_rate,
        "pause": asdict(pause_summary),
        "repetition_rate_per_100_words": repetition_rate,
        "hedging_rate_per_100_words": hedging_rate,
        "point_position": asdict(point_position),
        "intelligibility": asdict(intelligibility_summary),
        "speaking_time": asdict(speaking_time_summary),
        "word_count": len(words),
        "sentence_count": len(sentences),
    }

    report.events.extend(wpm_events)
    report.events.extend(filler_events)
    report.events.extend(pause_events)
    report.events.extend(repetition_events)
    report.events.extend(hedging_events)
    report.events.extend(point_events)
    report.events.extend(intelligibility_events)

    if audio_samples is not None and audio_sample_rate is not None:
        prosody_summary, prosody_events = compute_prosody_metrics(
            audio_samples, audio_sample_rate
        )
        summary["prosody"] = asdict(prosody_summary)
        report.events.extend(prosody_events)

    report.summary = summary
    return report
