# Cadence — deterministic metrics module

This is the deterministic delivery-metrics engine described in the
Cadence scope document (§4.1 M3-M4, §6.3 step 5): pure functions over a
word-level transcript (and optionally raw audio) that compute delivery
metrics without any model/LLM call. It is one component of the larger
webapp scoped in that document, built standalone first because it needs
no external services, no API keys, and is the part of the pipeline whose
correctness the rest of the coaching product depends on.

## What's in here

| Module | Scope section | Computes |
|---|---|---|
| `metrics.wpm` | §4.1 M3 | Words per minute, overall + rolling window |
| `metrics.fillers` | §4.1 M3 | Filler rate per 100 words, timestamped instances |
| `metrics.pauses` | §4.1 M3 | Pause count/mean/longest, mid-clause vs boundary |
| `metrics.repetitions` | §4.1 M3 | Immediate repetition + possible-restart rate |
| `metrics.hedging` | §4.1 M4 | Hedging index with timestamps + rewrite suggestions |
| `metrics.point_position` | §4.1 M4 | Where the recommendation lands (first sentence = target) |
| `metrics.intelligibility` | §4.1 M4 | Confidence × rate-of-speech proxy for hard-to-follow stretches |
| `metrics.prosody` | §4.1 M3 | Pitch (F0) range/variance, energy variance — reported as "vocal variety," never "confidence" |
| `metrics.speaking_time` | §4.1 M3 | Total speaking time, longest unbroken run |
| `metrics.report` | §6.3 step 5 | `compute_metrics()` — the single entry point wiring all of the above into one `MetricsReport` |

Every function is pure: same input in, same output out, every time.
That separation (§6.3) is deliberate — a user's improvement curve must
never be an artefact of a model having a different opinion on a re-run.
The `MetricEvent` list in the report is what the coaching layer (§4.1 M6,
out of scope here) deep-links to specific transcript timestamps.

## What's deliberately not here

The LLM rubric evaluator (§4.1 M5), evidence validator (§6.3 step 7),
STT integration, API/worker layer, and everything client-facing are out
of scope for this module — they depend on vendor API keys and infra this
environment doesn't have. `compute_metrics()` is the exact seam where the
STT pipeline output (word-level transcript + optional decoded PCM audio)
plugs in.

## Known limitations, stated rather than hidden (per §6.2, §9's honesty pillar)

- **Repetition/restart detection** is a lexical proxy, not a disfluency
  parser. It reliably catches immediate word repeats; "possible restart"
  is a weaker heuristic and is labelled as such in its event type.
- **Point-position scoring** is lexical-marker matching, not semantic
  understanding of the point's quality — that's the LLM rubric's job.
- **Prosody/F0 tracking** uses a plain autocorrelation pitch tracker
  (no external DSP dependency). It's adequate for range/variance
  reporting but is not validated against a hand-labelled set the way
  §6.6 requires before the full product can ship — that validation
  needs the Phase 0 eval corpus, not just this module.
- Sentence segmentation relies on ASR-supplied terminal punctuation. If
  the STT vendor doesn't emit it, the whole transcript is treated as one
  sentence rather than guessing — guessing would make point-position
  scoring non-deterministic.

## Running

```bash
pip install -e ".[dev]"
pytest --cov=metrics --cov-report=term-missing
```

39 tests, 96% line coverage as of this commit.

## Usage

```python
from metrics import Word, compute_metrics

words = [
    Word(text="So,", start_ms=0, end_ms=150, confidence=0.95),
    Word(text="I", start_ms=350, end_ms=450, confidence=0.97),
    Word(text="think", start_ms=450, end_ms=600, confidence=0.96),
    Word(text="we", start_ms=600, end_ms=700, confidence=0.98),
    Word(text="should", start_ms=700, end_ms=850, confidence=0.97),
    Word(text="ship.", start_ms=850, end_ms=1000, confidence=0.95),
]

report = compute_metrics(words)
print(report.summary["hedging_rate_per_100_words"])
print(report.events_of_type("hedge"))
```

Pass `audio_samples` (mono float array in `[-1, 1]`) and
`audio_sample_rate` to also get pitch/energy metrics; omit them and
prosody is skipped rather than fabricated.
