"""Core data structures shared by every metrics function.

Mirrors the relevant slice of the §6.4 data model: `transcript_segment`
(word-level) and `metric_event` (type, start_ms, end_ms, value).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Word:
    """A single ASR word with timing and confidence.

    `text` is expected verbatim from the STT vendor with disfluency
    detection enabled (§6.2) — fillers like "um"/"uh" must survive, and
    sentence-ending punctuation, when the vendor supplies it, is used for
    sentence segmentation.
    """

    text: str
    start_ms: int
    end_ms: int
    confidence: float = 1.0

    def __post_init__(self) -> None:
        if self.end_ms < self.start_ms:
            raise ValueError(
                f"word {self.text!r} has end_ms < start_ms "
                f"({self.end_ms} < {self.start_ms})"
            )
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"confidence must be in [0, 1], got {self.confidence}")

    @property
    def duration_ms(self) -> int:
        return self.end_ms - self.start_ms


@dataclass(frozen=True)
class Sentence:
    """A contiguous run of words, split on sentence-ending punctuation."""

    words: tuple[Word, ...]

    @property
    def start_ms(self) -> int:
        return self.words[0].start_ms

    @property
    def end_ms(self) -> int:
        return self.words[-1].end_ms

    @property
    def text(self) -> str:
        return " ".join(w.text for w in self.words)


@dataclass(frozen=True)
class MetricEvent:
    """One instance of a timestamped metric, matching the `metric_event` entity."""

    type: str
    start_ms: int
    end_ms: int
    value: Any = None


@dataclass
class MetricsReport:
    """Aggregate output of `compute_metrics`.

    `summary` holds scalar/aggregate values (e.g. `wpm_overall`,
    `filler_rate_per_100_words`); `events` holds every timestamped
    instance (filler occurrences, pauses, hedges, low-intelligibility
    stretches, ...) for evidence-linked coaching (§4.1 M6).
    """

    summary: dict[str, Any] = field(default_factory=dict)
    events: list[MetricEvent] = field(default_factory=list)

    def events_of_type(self, event_type: str) -> list[MetricEvent]:
        return [e for e in self.events if e.type == event_type]
