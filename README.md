# Cadence — deterministic metrics + pipeline API

Two components of the Cadence webapp (see `docs/scope.md`), built
standalone because they need no external services or infra beyond what
this environment provides:

1. **`metrics/`** — the deterministic delivery-metrics engine (§4.1
   M3-M4, §6.3 step 5).
2. **`api/`** — a FastAPI service implementing the analysis pipeline
   (§6.3 steps 1-9) around it, with STT and LLM vendors behind provider
   interfaces and mock implementations so the whole flow runs without
   API keys.

## `metrics/` — deterministic delivery metrics

Pure functions over a word-level transcript (and optionally raw audio)
that compute delivery metrics without any model/LLM call.

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

### Usage

```python
from metrics import Word, compute_metrics

words = [
    Word(text="maybe", start_ms=0, end_ms=200, confidence=0.9),
    Word(text="we", start_ms=210, end_ms=300, confidence=0.95),
    Word(text="should", start_ms=310, end_ms=500, confidence=0.95),
    Word(text="ship", start_ms=510, end_ms=650, confidence=0.95),
    Word(text="it.", start_ms=660, end_ms=800, confidence=0.95),
]

report = compute_metrics(words)
print(report.summary["hedging_rate_per_100_words"])
print(report.events_of_type("hedge"))
```

Pass `audio_samples` (mono float array in `[-1, 1]`) and
`audio_sample_rate` to also get pitch/energy metrics; omit them and
prosody is skipped rather than fabricated.

## `api/` — analysis pipeline + session API

Implements §6.3's pipeline end to end:

```
upload (chunked, resumable) → normalize → STT → deterministic metrics
   → LLM rubric evaluator → evidence validator → drill recommendation → persist
```

| Module | Scope section | Role |
|---|---|---|
| `api.storage.ObjectStore` / `LocalObjectStore` | §6.1, §4.1 M2 | Resumable chunked upload; a dropped connection never destroys a recording |
| `api.pipeline.normalize` | §6.3 step 3 | Audio normalization seam (dev stand-in: passthrough, no ffmpeg dependency) |
| `api.pipeline.stt` | §6.3 step 4, §6.2 | STT provider seam. **Never Whisper** — it strips disfluencies and lacks native word timestamps (§6.2 hard constraint). Mock provider accepts a pre-built transcript so the rest of the pipeline is testable without a live vendor |
| `api.pipeline.llm` | §4.1 M5, §6.3 step 6 | LLM rubric-evaluator seam, transcript + metrics only, **never raw audio**. Mock provider derives feedback from real deterministic-metric events (hedging, point-position, fillers), so it's deterministic and still exercises the evidence contract |
| `api.pipeline.evidence` | §6.3 step 7 | Rejects any feedback item whose quoted evidence span isn't verbatim in the transcript at the claimed timestamps — "never surface an unverifiable claim" |
| `api.pipeline.drills` | §4.1 M7 | Picks one repair drill targeting the top surviving feedback item |
| `api.pipeline.orchestrator` | §6.3 | `run_pipeline()` — the single function a worker (Celery/Arq in production) would call |
| `api.db` | §6.4 (simplified) | SQLAlchemy models: `PracticeSession`, `MediaAsset`, `AnalysisResult` (versioned by `rubric_version`/`model_version`, §6.4) |
| `api.routers.sessions` | — | HTTP surface: create session, chunked upload, analyze, fetch result, one-click delete (§4.1 M11) |

### Running

```bash
pip install -e ".[dev]"
uvicorn api.main:app --reload
# → http://127.0.0.1:8000/docs
```

```bash
curl -X POST localhost:8000/sessions -H 'content-type: application/json' -d '{"scenario":"standup"}'
curl -X POST "localhost:8000/sessions/<id>/media?offset=0" --data-binary @transcript.json
curl -X POST "localhost:8000/sessions/<id>/analyze"
curl "localhost:8000/sessions/<id>/result"
```

With `STT_PROVIDER=mock` (the default), the "audio" payload the mock
expects is a JSON array of `{"text","start_ms","end_ms","confidence"}`
objects — see `api/pipeline/stt.py`'s docstring. This lets the full
pipeline run without a real STT vendor; point `STT_PROVIDER` /
`LLM_PROVIDER` at a real implementation of `STTProvider` /
`LLMRubricProvider` to go live.

### Known simplifications, stated rather than hidden

- `AnalysisResult` stores transcript/metrics/feedback as JSON columns
  rather than the fully normalized `transcript_segment` / `metric_event`
  / `feedback_item` / `drill` tables in §6.4 — normalizing that schema is
  a separate scope item, not required for the pipeline to function or be
  tested.
- `/analyze` runs the pipeline synchronously in-request. Production
  moves steps 3-8 into a Celery/Arq worker (§6.1); `run_pipeline()` is
  already the exact function such a worker task would call, so this is
  a wiring change, not a rewrite.
- `PassthroughNormalizer` performs no real resampling — it exists so the
  pipeline is exercisable without an ffmpeg dependency. Never wire it to
  production audio.
- **Repetition/restart detection** is a lexical proxy, not a disfluency
  parser. It reliably catches immediate word repeats; "possible restart"
  is a weaker heuristic and is labelled as such in its event type.
- **Point-position scoring** is lexical-marker matching, not semantic
  understanding of the point's quality — that's the LLM rubric's job.
- **Prosody/F0 tracking** uses a plain autocorrelation pitch tracker (no
  external DSP dependency). Adequate for range/variance reporting but
  not yet validated against a hand-labelled set as §6.6 requires before
  the full product can ship — that needs the Phase 0 eval corpus.
- Sentence segmentation relies on ASR-supplied terminal punctuation. If
  the STT vendor doesn't emit it, the whole transcript is treated as one
  sentence rather than guessing — guessing would make point-position
  scoring non-deterministic.

## What's still out of scope

Auth, the Next.js Practice Studio UI, Stripe billing, real STT/LLM
vendor integrations, the fully normalized §6.4 schema, calendar
integration, and everything in Phase 2/3 of the roadmap.

## Testing

```bash
pytest --cov=metrics --cov=api --cov-report=term-missing
```

67 tests, 97% line coverage as of this commit.
