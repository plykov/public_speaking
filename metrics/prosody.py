"""Pitch range/variance and energy variance from raw audio (§4.1 M3).

Reported as *vocal variety*, never as "confidence" — pitch and energy
range are not validated proxies for confidence and the scope document is
explicit that this product does not make that claim (§2.3, §9).

Implementation is a plain autocorrelation pitch tracker over numpy arrays
— no external DSP/ML dependency, so it stays a pure, testable function.
It is deliberately simple; a production pipeline may swap in a more
robust tracker (e.g. YIN/CREPE) behind the same interface without
changing the metric semantics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from metrics.models import MetricEvent

MIN_F0_HZ = 70.0
MAX_F0_HZ = 400.0
FRAME_MS = 30
HOP_MS = 10
VOICED_ENERGY_PERCENTILE = 40  # frames below this energy percentile are "unvoiced"/silence


@dataclass
class ProsodySummary:
    f0_mean_hz: float
    f0_range_hz: float
    f0_variance: float
    energy_variance: float
    voiced_frame_ratio: float


def _frame_signal(samples: np.ndarray, sample_rate: int) -> tuple[np.ndarray, list[int]]:
    frame_len = int(sample_rate * FRAME_MS / 1000)
    hop_len = int(sample_rate * HOP_MS / 1000)
    if frame_len <= 0 or hop_len <= 0 or len(samples) < frame_len:
        return np.empty((0, max(frame_len, 1))), []

    starts = list(range(0, len(samples) - frame_len + 1, hop_len))
    frames = np.stack([samples[s : s + frame_len] for s in starts])
    return frames, starts


def _autocorrelation_f0(frame: np.ndarray, sample_rate: int) -> float | None:
    windowed = frame * np.hanning(len(frame))
    autocorr = np.correlate(windowed, windowed, mode="full")
    autocorr = autocorr[len(autocorr) // 2 :]

    min_lag = int(sample_rate / MAX_F0_HZ)
    max_lag = int(sample_rate / MIN_F0_HZ)
    if max_lag >= len(autocorr) or min_lag >= max_lag:
        return None

    search = autocorr[min_lag:max_lag]
    if search.size == 0 or autocorr[0] <= 0:
        return None

    peak_lag = int(np.argmax(search)) + min_lag
    peak_value = autocorr[peak_lag]

    if peak_value <= 0 or peak_value / autocorr[0] < 0.3:
        return None  # not confidently periodic -> unvoiced

    return sample_rate / peak_lag


def compute_prosody_metrics(
    samples: np.ndarray, sample_rate: int
) -> tuple[ProsodySummary, list[MetricEvent]]:
    """`samples` is mono float audio in [-1, 1]."""
    samples = np.asarray(samples, dtype=np.float64)
    frames, starts = _frame_signal(samples, sample_rate)
    if len(starts) == 0:
        return ProsodySummary(0.0, 0.0, 0.0, 0.0, 0.0), []

    energies = np.sqrt(np.mean(frames**2, axis=1))
    energy_threshold = np.percentile(energies, VOICED_ENERGY_PERCENTILE)

    f0_values: list[float] = []
    monotone_windows: list[MetricEvent] = []
    frame_f0s: list[float | None] = []

    for frame, energy in zip(frames, energies):
        if energy < energy_threshold:
            frame_f0s.append(None)
            continue
        f0 = _autocorrelation_f0(frame, sample_rate)
        frame_f0s.append(f0)
        if f0 is not None:
            f0_values.append(f0)

    voiced_ratio = round(len(f0_values) / len(starts), 3) if starts else 0.0

    if not f0_values:
        f0_mean = f0_range = f0_variance = 0.0
    else:
        f0_arr = np.array(f0_values)
        low, high = np.percentile(f0_arr, [5, 95])
        f0_mean = round(float(np.mean(f0_arr)), 1)
        f0_range = round(float(high - low), 1)
        f0_variance = round(float(np.var(f0_arr)), 1)

    energy_variance = round(float(np.var(energies)), 6)

    events = _flag_monotone_stretches(frame_f0s, starts, sample_rate)

    return (
        ProsodySummary(
            f0_mean_hz=f0_mean,
            f0_range_hz=f0_range,
            f0_variance=f0_variance,
            energy_variance=energy_variance,
            voiced_frame_ratio=voiced_ratio,
        ),
        events,
    )


def _flag_monotone_stretches(
    frame_f0s: list[float | None],
    starts: list[int],
    sample_rate: int,
    window_frames: int = 100,  # ~1s of voiced frames at 10ms hop
    variance_threshold_hz2: float = 25.0,
) -> list[MetricEvent]:
    events: list[MetricEvent] = []
    i = 0
    while i < len(frame_f0s):
        window = [f for f in frame_f0s[i : i + window_frames] if f is not None]
        if len(window) >= window_frames // 2:
            variance = float(np.var(window))
            if variance < variance_threshold_hz2:
                start_ms = int(starts[i] / sample_rate * 1000)
                end_idx = min(i + window_frames, len(starts)) - 1
                end_ms = int(starts[end_idx] / sample_rate * 1000) + FRAME_MS
                events.append(
                    MetricEvent(
                        type="monotone_stretch",
                        start_ms=start_ms,
                        end_ms=end_ms,
                        value={"f0_variance": round(variance, 1)},
                    )
                )
                i += window_frames
                continue
        i += window_frames // 4

    return events
