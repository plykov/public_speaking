from __future__ import annotations

import numpy as np

from metrics.prosody import compute_prosody_metrics


def _sine(freq_hz: float, duration_s: float, sample_rate: int, amplitude: float = 0.6) -> np.ndarray:
    t = np.linspace(0, duration_s, int(sample_rate * duration_s), endpoint=False)
    return amplitude * np.sin(2 * np.pi * freq_hz * t)


def test_silence_yields_zero_summary():
    sample_rate = 16000
    samples = np.zeros(sample_rate)  # 1s of silence
    summary, events = compute_prosody_metrics(samples, sample_rate)
    assert summary.f0_mean_hz == 0.0
    assert summary.voiced_frame_ratio == 0.0
    assert events == []


def test_constant_tone_detects_expected_f0_and_flags_monotone():
    sample_rate = 16000
    freq = 150.0
    samples = _sine(freq, duration_s=2.0, sample_rate=sample_rate)
    summary, events = compute_prosody_metrics(samples, sample_rate)

    assert abs(summary.f0_mean_hz - freq) < 5.0
    assert summary.voiced_frame_ratio > 0.5
    # a pure constant tone has ~zero pitch variance -> should be flagged monotone
    assert any(e.type == "monotone_stretch" for e in events)


def test_varying_pitch_has_higher_variance_than_constant_tone():
    sample_rate = 16000
    constant = _sine(150.0, 2.0, sample_rate)

    # frequency sweeps from 100Hz to 250Hz across the clip
    t = np.linspace(0, 2.0, int(sample_rate * 2.0), endpoint=False)
    freq_sweep = 100 + (250 - 100) * (t / 2.0)
    varying = 0.6 * np.sin(2 * np.pi * np.cumsum(freq_sweep) / sample_rate)

    constant_summary, _ = compute_prosody_metrics(constant, sample_rate)
    varying_summary, _ = compute_prosody_metrics(varying, sample_rate)

    assert varying_summary.f0_variance > constant_summary.f0_variance
