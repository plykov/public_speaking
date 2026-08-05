"""Audio normalization stage (§6.3 step 3: 16 kHz mono WAV).

The real implementation resamples/downmixes with ffmpeg or a library
like pydub/soundfile. That's an infra dependency this module doesn't
pull in; `AudioNormalizer` is the seam so it can be swapped in without
touching the orchestrator.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class NormalizedAudio:
    pcm: bytes
    sample_rate: int
    channels: int


class AudioNormalizer(ABC):
    @abstractmethod
    def normalize(self, raw_audio: bytes) -> NormalizedAudio: ...


class PassthroughNormalizer(AudioNormalizer):
    """Dev/test stand-in: assumes the input is already 16 kHz mono PCM.

    Never wire this to production — it performs no resampling or
    downmixing. It exists so the pipeline can be exercised end-to-end
    without an ffmpeg dependency.
    """

    def __init__(self, sample_rate: int = 16_000, channels: int = 1) -> None:
        self._sample_rate = sample_rate
        self._channels = channels

    def normalize(self, raw_audio: bytes) -> NormalizedAudio:
        return NormalizedAudio(
            pcm=raw_audio, sample_rate=self._sample_rate, channels=self._channels
        )
