"""Deterministic delivery-metrics engine (scope §4.1 M3-M4, §6.3 step 5).

Pure functions only — no model calls, no LLM. Given a word-level transcript
(and optionally raw audio samples), compute the delivery metrics that feed
the coaching layer. Every metric here must be reproducible: the same input
always yields the same output, so a user's improvement is never an artefact
of a model having a different opinion on a re-run.
"""

from metrics.models import Word, Sentence, MetricEvent, MetricsReport
from metrics.report import compute_metrics

__all__ = [
    "Word",
    "Sentence",
    "MetricEvent",
    "MetricsReport",
    "compute_metrics",
]
