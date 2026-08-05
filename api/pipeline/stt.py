"""Transcription stage (§6.3 step 4, §6.2 hard constraint).

`STTProvider` is the seam for AssemblyAI / Deepgram Nova-3 with
disfluency detection. **Do not implement this with Whisper** — Whisper
removes disfluencies and lacks native word-level timestamps, which
breaks the filler/hedging metrics this product is built on (§6.2).

`MockSTTProvider` is a development/testing stand-in only. It does not
decode audio. It expects the "audio" payload to be a UTF-8 JSON array of
`{"text", "start_ms", "end_ms", "confidence"}` objects — i.e. the
caller supplies the transcript a real vendor would have produced, so
the rest of the pipeline (metrics, rubric, evidence validation,
persistence) can be exercised end-to-end without a live STT dependency
or API key.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod

from metrics.models import Word


class TranscriptionError(Exception):
    pass


class STTProvider(ABC):
    @abstractmethod
    def transcribe(self, pcm: bytes, sample_rate: int) -> list[Word]: ...


class MockSTTProvider(STTProvider):
    def transcribe(self, pcm: bytes, sample_rate: int) -> list[Word]:
        try:
            raw = json.loads(pcm.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise TranscriptionError(
                "MockSTTProvider expects a JSON word-list payload, not real audio — "
                "see api/pipeline/stt.py docstring. Configure a real STT_PROVIDER "
                "(AssemblyAI/Deepgram) to transcribe actual audio."
            ) from exc

        try:
            return [
                Word(
                    text=w["text"],
                    start_ms=w["start_ms"],
                    end_ms=w["end_ms"],
                    confidence=w.get("confidence", 1.0),
                )
                for w in raw
            ]
        except (KeyError, TypeError) as exc:
            raise TranscriptionError(f"malformed mock transcript entry: {exc}") from exc


def get_stt_provider(name: str) -> STTProvider:
    if name == "mock":
        return MockSTTProvider()
    raise NotImplementedError(
        f"STT provider {name!r} is not wired up yet. Only 'mock' is available in this "
        "module — integrate AssemblyAI or Deepgram Nova-3 with disfluency mode on (§6.2)."
    )
