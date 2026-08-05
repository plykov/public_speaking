"""Text normalization and sentence segmentation shared by the metric modules."""

from __future__ import annotations

import re

from metrics.models import Sentence, Word

_SENTENCE_END_RE = re.compile(r"[.!?]+$")
_WORD_CHARS_RE = re.compile(r"[^a-z0-9']+")


def normalize(text: str) -> str:
    """Lowercase and strip surrounding punctuation for pattern matching."""
    return _WORD_CHARS_RE.sub("", text.lower()).strip()


def is_sentence_boundary(word: Word) -> bool:
    """True if this word's text ends a sentence (per ASR punctuation)."""
    return bool(_SENTENCE_END_RE.search(word.text.strip()))


def split_sentences(words: list[Word]) -> list[Sentence]:
    """Group words into sentences using ASR-supplied terminal punctuation.

    If no word in the sequence carries terminal punctuation (some STT
    configurations omit it), the whole sequence is treated as one sentence
    rather than guessing boundaries — guessing would make point-position
    scoring non-deterministic.
    """
    sentences: list[Sentence] = []
    current: list[Word] = []
    for word in words:
        current.append(word)
        if is_sentence_boundary(word):
            sentences.append(Sentence(words=tuple(current)))
            current = []
    if current:
        sentences.append(Sentence(words=tuple(current)))
    return sentences
