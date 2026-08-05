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
| `api.db` | §6.4 | Normalized SQLAlchemy models — see the schema table below |
| `api.routers.sessions` | — | HTTP surface: create session, chunked upload, analyze, fetch result, get/edit transcript (§4.1 M8), one-click delete (§4.1 M11) |
| `api.routers.users` | §4.1 M1, M9, M10, M11 | Onboarding (create user, upsert L1 profile), progress attempts, reminder + streak, account export and delete |
| `api.routers.feedback` | §4.1 M6 | Thumbs up/down on a feedback item |
| `api.routers.admin` | §6.5 | Raw-media retention purge (no scheduler in this environment — see below) |
| `api.routers.billing` | §4.1 M12, §8.1 | Mock checkout, checkout confirmation, subscription status |
| `api.routers.push` | §4.2 | VAPID public key, push subscribe/unsubscribe, real test-send |
| `api.lifecycle` | §4.1 M11, §6.5 | Shared delete/export/retention logic — one code path for both session-delete and account-delete, so neither can drift and delete less than the other |
| `api.streaks` | §4.1 M10 | `compute_streak()` — pure function, no DB access, same "pure core" pattern as `metrics/` |
| `api.billing` | §4.1 M12, §8.1 | Entitlement logic (`effective_tier()`, `quota_exceeded()`) plus the no-real-Stripe provider seam — same pattern as `api.pipeline.stt` / `api.pipeline.llm` |
| `api.push` | §4.2 | Real Web Push send (VAPID keys + `pywebpush`) — genuinely delivers, unlike the STT/LLM/Stripe seams; the gap is scheduling *when* to send, not the send itself |
| `api.l1_calibration` | §4.2 | Catalog of nine L1 calibration profiles (RU/NL/DE/FR/ES/PT-BR/ZH/HI/JA) — real, authored content, no vendor dependency |
| `api.slides` | §4.2 | PDF page count + thumbnail rendering (PyMuPDF) — real, deterministic, no vendor dependency (AGPL license caveat noted in the Phase 2 section) |
| `api.sharing` | §4.2 | Token generation + expiry/revocation check for coach/manager share links — real, no vendor dependency |
| `api.pipeline.exemplar` | §4.2 | Exemplar-mode seam + mock (same pattern as STT/LLM/billing) — real rewrite quality needs a frontier model, not available in this environment |
| `api.pipeline.roleplay` | §4.2 | Persona catalog (3) + roleplay-reply seam/mock + multi-persona round-robin turn-picking. STT reused for real from `api.pipeline.stt`; TTS is genuinely real via the browser's `SpeechSynthesis` API, no mock needed |
| `api.calendar` | §4.2 | Calendar-connection seam/mock (real Google/Microsoft OAuth needs an app registration not available here) + genuinely real imminent-event-to-drill matching |
| `api.routers.teams` | §4.3 | Team workspaces, membership/roles (not enforced — no auth system exists), invites, custom scenarios (real) + custom rubrics (stored, not yet consumed by scoring) |
| `api.analytics` | §4.3 | Manager aggregate analytics — team/per-member metric averages; no field capable of carrying raw recordings/transcripts, by construction |
| `api.audit` | §4.3 | One-function audit-log helper — appends an immutable `AuditLogEntry`, no other logic |

### Data model (§6.4)

| Table | §6.4 entity | Notes |
|---|---|---|
| `User` | `user` | Anonymous, device-scoped — no email/password. Auth is explicitly out of scope; the client holds the id (localStorage) |
| `L1Profile` | `l1_profile` | First language + self-declared confidence, plus an optional §4.2 `first_language_code` for the L1 calibration catalog. Read only by onboarding copy and the dev-mode sample-transcript picker — **never** by `api/pipeline/llm.py` or `metrics/report.py` |
| `PracticeSession` | `session` | Adds `user_id` and a self-referencing `parent_session_id` — a retry session points at the baseline it followed, which is §6.4's `attempt_link` relationship without a separate join table |
| `MediaAsset` | `media_asset` | Unchanged — storage key only, never the audio bytes |
| `TranscriptWord` | `transcript_segment` | Word-level: text, start/end ms, confidence, sequence index |
| `MetricEventRow` | `metric_event` | Every timestamped instance from the deterministic metrics module |
| `FeedbackItemRow` | `feedback_item` | Includes `user_rating` (nullable bool) for the M6 thumbs up/down |
| `TranscriptCorrection` | — | Not a §6.4 entity — logs each M8 word-level correction (original/corrected text) with a snapshot of the speaker's L1 background, an ASR-quality-by-cohort signal per §6.6. Deleted along with its session (privacy over long-term analytics — see below) |
| `Reminder` | `reminder` | Days + time-of-day preference for the M10 habit layer. Storing the preference is the whole scope — see below |
| `PushSubscription` | — | Not a §6.4 entity — a browser's `PushSubscription.toJSON()` (endpoint + keys), for §4.2 Web Push. Unique on `endpoint`, since that *is* the subscription's identity |
| `SlideDeck` | `slide_decks` | Not a §6.4 entity — one PDF per session (§4.2), storage key + page count |
| `SlideTransition` | `slide_transitions` | Not a §6.4 entity — "advanced to slide N at elapsed-ms T" marks (§4.2), used client-side to link transcript evidence to a slide |
| `ShareLink` | `share_links` | Not a §6.4 entity — a coach/manager share link (§4.2): token, three permission flags, optional expiry, soft-delete via `revoked_at` |
| `RoleplaySession` / `RoleplayTurn` | `roleplay_sessions` / `roleplay_turns` | Not §6.4 entities — a turn-based voice roleplay conversation (§4.2, single- or multi-persona via `persona_ids`) and its dialogue lines (`persona_id` attributes each persona turn). No raw audio ever stored for a turn |
| `CalendarConnection` | `calendar_connections` | Not a §6.4 entity — whether/which calendar provider (§4.2) a user has connected. One row per user |
| `Team` / `TeamMembership` / `TeamInvite` | `teams` / `team_memberships` / `team_invites` | Not §6.4 entities — team workspace (§4.3), membership + advisory role, one-time invite tokens |
| `TeamScenario` / `TeamRubric` | `team_scenarios` / `team_rubrics` | Not §6.4 entities — team-authored custom scenario prompts (real) and rubric criteria (stored, not yet consumed by scoring) |
| `AuditLogEntry` | `audit_log_entries` | Not a §6.4 entity — an immutable audit-log row (§4.3): actor, action, target, detail. Never updated/deleted by any other code path |
| `Subscription` | `subscription` | Tier/status/period-end for M12 billing — see below. A user with no row (or an expired `event_sprint`) is free-tier by construction, computed in `api.billing.effective_tier()`, never trusted from `.tier` alone |
| `CheckoutSession` | — | Not a §6.4 entity — a pending mock checkout, resolved by the confirm endpoint standing in for a Stripe webhook |
| `AnalysisResult` | — | Not a §6.4 entity — a per-attempt stamp of `rubric_version`/`model_version`, the computed metrics summary (kept as JSON: it's a derived aggregate, not a core entity), and a snapshot of the recommended drill |

Re-analyzing a session (`POST /sessions/{id}/analyze` called again) replaces
that session's `TranscriptWord` / `MetricEventRow` / `FeedbackItemRow` /
`AnalysisResult` rows rather than appending — a session has one current
attempt's worth of derived data, not a growing pile of them.

**Deliberately not modeled**: `goal`, `scenario` as a table (kept as a
plain string — no admin CRUD for scenarios was in scope),
`rubric_version` as a table (the rubric is code-defined in
`api/pipeline/llm.py`, not database-editable), `skill_trend` (§4.1 M9 —
`GET /users/{id}/attempts` computes trends from `AnalysisResult` on
read rather than maintaining a separate rolled-up table) — not part of
the work this covers.

### Habit layer (§4.1 M10)

| Endpoint | Behavior |
|---|---|
| `PUT`/`GET /users/{id}/reminder` | Store/fetch a reminder-window preference (days + time-of-day) |
| `GET /users/{id}/streak` | Non-punitive streak — a single missed day is tolerated once per streak run before it breaks, via `api.streaks.compute_streak()` |

Calendar-free v1, same as the scope doc specifies: no Google/Microsoft
calendar integration (that's Phase 2 — §4.2), and no actual reminder
delivery, since there's no notification channel (push/email) or
scheduler in this environment — same documented gap as
`purge-expired-media` above. `PUT /users/{id}/reminder` stores the
preference; a real send is a follow-up. The streak is self-relative,
like Progress (§4.1 M9) — no comparison to other users, and "freeze"
means exactly one skipped day per contiguous run doesn't reset the
count, not an unlimited grace period.

### Billing (§4.1 M12, §8.1)

| Endpoint | Behavior |
|---|---|
| `POST /users/{id}/checkout` | `{"tier": "pro" \| "event_sprint"}` — creates a pending mock checkout, returns a fake `mock://checkout/{id}` URL. `team` is rejected: sold out of band, not self-serve |
| `POST /billing/checkout/{id}/confirm` | Dev-mode stand-in for a verified Stripe webhook firing after payment. Idempotent — confirming twice is a no-op the second time |
| `GET /users/{id}/subscription` | The *effective* tier (never trust a raw `.tier` — an expired `event_sprint` silently reverts), plus this month's analysis count and limit |

No real payment processing exists, and no Stripe key belongs in this
repo — same seam pattern as `api.pipeline.stt` / `api.pipeline.llm`:
`BillingProvider` is the interface, `MockBillingProvider` the dev
implementation, `get_billing_provider()` the factory a real
`StripeBillingProvider` would plug into via `BILLING_PROVIDER=stripe`.

Entitlement gating lives in `POST /sessions/{id}/analyze`: **free tier
is capped at 3 analyses/month** (§8.1), enforced only on a session's
*first* analysis — re-analyzing after a transcript correction never
consumes a second slot, and anonymous sessions (no `user_id`) are never
gated, matching the no-card free tier already being the default.
Exceeding the cap returns `402 Payment Required` with a message
pointing at Pro/Event Sprint. `pro` and `team` are unlimited and
non-expiring; `event_sprint` is unlimited for a rolling 30 days from
confirmation, then reverts to free automatically — there's no
"downgrade" event to handle, just `effective_tier()` recomputing on
every read.

## Phase 2

### Web Push (§4.2 — "Installable PWA with Web Push")

Unlike the STT/LLM/Stripe seams, **this one is real end to end on the
send side** — no vendor account or API key needed, since the browser's
own push service (e.g. Chrome's, via FCM) is used transparently once a
client subscribes with our self-generated VAPID key. `api/push.py`
generates a VAPID keypair (env vars persist it across restarts; unset,
a fresh ephemeral one is generated per process — fine for dev, but every
subscription made against it dies on the next restart) and sends via
`pywebpush`.

| Endpoint | Behavior |
|---|---|
| `GET /push/vapid-public-key` | The public key the frontend passes to `pushManager.subscribe()` |
| `POST /users/{id}/push-subscriptions` | Register (or update, keyed by `endpoint`) a browser subscription |
| `POST /users/{id}/push-subscriptions/unsubscribe` | Remove one |
| `POST /users/{id}/push-subscriptions/test` | Send one real push to every subscription this user has; auto-removes any the push service reports as gone (404/410) |

**The gap**: nothing decides *when* to send — there's no scheduler here
to notice "it's time for this user's reminder window" (§4.1 M10's
documented gap, same root cause as `purge-expired-media`). `test` is
the only trigger that exists; wiring `Reminder` to actually fire one is
a follow-up.

**A real bug this caught**: a subscription with a slightly malformed
`p256dh` key (valid-looking but wrong base64 padding — the kind of
thing corrupted browser-side storage could produce) crashed
`send_web_push` with an unhandled `binascii.Error` from deep inside
`pywebpush`, before any network call was even attempted, returning a
raw 500 instead of a handled failure. Fixed by broadening the catch and
covered by a regression test (`test_send_web_push_malformed_key_does_not_raise`)
— found via manual testing with a deliberately-malformed subscription,
not by the unit tests, which is exactly why the manual pass matters.

**Frontend**: `src/public/manifest.webmanifest` + `sw.js` (push,
notificationclick, and a passthrough fetch handler some browsers still
check for install-eligibility) + `src/lib/push.ts` + `PushSettings.tsx`
on `/settings`. `layout.tsx` wires the manifest, theme color, and Apple
home-screen-install meta (§4.2's explicit iOS note).

**Verified live, and what couldn't be**: service worker registration
and the Notification permission grant both work in this environment,
confirmed via direct `page.evaluate` diagnostics with per-step
timeouts. `pushManager.subscribe()` itself hangs indefinitely — it
needs to reach the browser vendor's internal push-registration
service, which this sandboxed container's browser can't do (backend-only
HTTP through the environment's proxy doesn't cover Chromium's own
network stack). That's an environment constraint on *testing* this
specific browser call, not a defect in the implementation: the code
path is identical to what any real deployed browser would run, and the
send side was verified for real — registering a subscription with a
genuine FCM-shaped endpoint and calling `/test` against it produces a
real HTTP round-trip to `fcm.googleapis.com`, observable in the API
logs and failing predictably (not silently) on fabricated key data.
Given the hang was real (not just slow), `subscribeToPush()` now races
against a 15s timeout with a clear error — a legitimate defensive fix
independent of this sandbox, since `pushManager.subscribe()` has no
built-in timeout and a stuck call previously left the UI's "Enabling…"
button spinning forever with no way out.

**Install note**: `pywebpush`'s `http-ece` dependency can fail to build
on an old/distro-patched `pip`+`setuptools` combo (a `distutils`
`install_layout` `AttributeError`) — if `pip install -e ".[dev]"` fails
on it, upgrade `pip`/`setuptools`/`wheel` first (ideally in a venv) and
retry.

### L1 calibration profiles (§4.2 — "Additional L1 calibration profiles")

Phase 1's onboarding stored "first language" as free text, shown back
verbatim but taught the product nothing. `api/l1_calibration.py` adds a
curated catalog for the nine languages named in scope (RU, NL, DE, FR, ES,
PT-BR, ZH, HI, JA): each has a short, hedged calibration note about a
documented L1→English transfer pattern relevant to meeting speech (e.g.
topic-comment ordering, discourse register, hedging carried over from a more
deferential first-language register) — never a claim about accent,
intelligence, or "correctness." Same non-negotiable as before: **this is
onboarding copy only** — `api/pipeline/llm.py` and `metrics/report.py` never
read `L1Profile`, and adding a code here doesn't change that.

| Endpoint | Behavior |
|---|---|
| `GET /l1-calibration-profiles` | The catalog: code, label, calibration note |
| `PUT /users/{id}/l1-profile` | Now also accepts `first_language_code`; response includes a derived `calibration_note` (not stored — computed from the code on every read, so editing the catalog text doesn't require a data migration) |

**Frontend**: onboarding's first-language field (`web/src/app/onboarding/page.tsx`)
is now a chip picker fetched from the catalog, showing the relevant
calibration note the moment a language is picked, plus an "Other / prefer
not to say" option that falls back to the original free-text input — nobody
outside the nine-language catalog loses the ability to onboard. Verified
live: picking Russian shows its note, switching to Other reveals the text
field, and submission reaches the recorder either way.

### Slide/PDF upload with slide-linked transcript (§4.2)

Real, no vendor gap: `api/slides.py` renders an uploaded PDF's page count
and per-page PNG thumbnails using PyMuPDF (`fitz`) — deterministic, no
LLM/network call, same "pure function over bytes" shape as `metrics/`.

**License note, stated rather than hidden**: PyMuPDF's open-source
distribution is AGPL-3.0. Fine for demonstrating this scope item; a real
deployment shipping closed-source code alongside it would need Artifex's
commercial license or a swap to a permissively-licensed renderer (e.g.
shelling out to Poppler's `pdftoppm`) — a vendor-swap decision, not an
architecture change, since everything downstream only depends on
`count_pages`/`render_thumbnails`'s signatures.

| Endpoint | Behavior |
|---|---|
| `POST /sessions/{id}/slides` | Upload/replace a session's PDF deck; renders + stores per-page thumbnails, returns page count + thumbnail URLs. Rejects non-PDF bytes with 422 |
| `GET /sessions/{id}/slides` | Deck metadata + thumbnail URLs |
| `GET /sessions/{id}/slides/{page}/thumbnail` | One page's PNG |
| `PUT /sessions/{id}/slide-transitions` | Replace the full list of "advanced to slide N at elapsed-ms T" marks (same replace-not-append pattern as §4.1 M8's transcript correction) |
| `GET /sessions/{id}/slide-transitions` | The current list, sorted by timestamp |

**Slide-linking is computed client-side, not server-side.** `web/src/lib/slideLinking.ts`'s
`buildSlideLookup()` takes the transitions list and returns a pure
`(ms) => slideIndex` function — kept out of the transcript/evidence tables
entirely so this feature never touches the deterministic pipeline's schema.
`Scorecard.tsx` calls it per feedback item's `evidence_start_ms` to show a
thumbnail + "Slide N" badge next to the evidence quote.

**Frontend flow**: the baseline session is now created up front (moved out
of `runAnalysis`, which previously created it lazily) so `SlideDeckPanel`
has a session to attach the PDF to before recording starts.
`RecorderPanel` grows optional `slidePageCount`/`onSlideAdvance` props: when
a deck is present, a "Next slide →" button appears during recording and
reports `(slideIndex, elapsedMs)` on click, using the same recording clock
as `TranscriptWord.start_ms`. Transitions are submitted right before
`/analyze` is called. Scoped to the baseline attempt only for now — the
retry/drill recording doesn't yet get its own deck, a stated gap rather
than a silent one.

Verified live end to end via Playwright: uploaded a real 3-page PDF built
with PyMuPDF, saw its thumbnails render in the upload panel, advanced
slides during a real recording, and confirmed the resulting scorecard's
feedback items each show the correct slide thumbnail + badge for their
evidence timestamp.

### Coach/manager share links (§4.2)

Real, no vendor dependency. `api/sharing.py` generates an opaque
`secrets.token_urlsafe` token — the token itself is the credential (an
"anyone with the link" model, not a coach account/login). Three
independent, opt-in-by-default-off permission flags control what a share
link exposes: progress trend (on by default — the whole point of sharing),
transcripts, and coaching feedback text. **Raw audio is never exposed
through a share link, at any permission combination** — that's not a
fourth flag that happens to default off, it's a property of what
`GET /share/{token}` returns; the response schema (`SharedAttemptOut`) has
no field capable of carrying it.

| Endpoint | Behavior |
|---|---|
| `POST /users/{id}/share-links` | Create a link: optional label, three permission booleans, optional `expires_in_days` |
| `GET /users/{id}/share-links` | List the owner's links (management view), each with a derived `revoked` flag |
| `DELETE /users/{id}/share-links/{share_id}` | Revoke (soft-delete via `revoked_at`, not a hard delete — matches the audit-friendly pattern used elsewhere) |
| `GET /share/{token}` | Public, no-login view. 404 for an unknown token, 410 Gone for revoked/expired — distinct statuses so a viewer isn't left guessing which |

**Frontend**: `ShareLinkSettings.tsx` on `/settings` creates/lists/revokes
links and copies the share URL to the clipboard. `web/src/app/share/[token]/page.tsx`
is the public viewer — plain metric tiles, transcript, and feedback cards
gated on whatever the link's permissions allow, with the "raw recordings
are never included" statement shown up front rather than left implicit.

Verified live end to end: created a user + analyzed session via the API,
created a share link with feedback included from `/settings`, opened the
generated `/share/{token}` URL and confirmed the metrics + feedback
rendered, revoked the link from `/settings`, and confirmed the same URL
now shows a clear "revoked or expired" message instead of a raw 410.

### Exemplar mode (§4.2 — "show a stronger version and explain the delta")

Same seam-plus-mock pattern as STT/LLM/billing: `api/pipeline/exemplar.py`
defines an `ExemplarProvider` interface a real frontier-model integration
would implement (compose a genuinely stronger, more naturally-phrased
rewrite). `MockExemplarProvider` is deliberately *not* a language model —
it only **reorders and removes what the speaker already said**: it moves
the sentence containing a recognized recommendation marker
(`metrics.point_position`'s detector) to the front, and strips detected
hedge phrases (`metrics.hedging`'s detector), reusing the exact same
deterministic detectors already in the pipeline rather than duplicating
logic. This is stated as a mechanical demonstration of the "show the
delta" UX, not a claim about rewrite quality — the frontend panel says so
directly rather than passing the mock off as a real rewrite.

| Endpoint | Behavior |
|---|---|
| `GET /sessions/{id}/exemplar` | Computed on demand from the stored transcript (not persisted — cheap to recompute, never stale after a §4.1 M8 transcript correction). 400 if the session has no transcript yet |

**Frontend**: `ExemplarPanel.tsx` — a "Show a stronger version" button on
both the baseline and retry scorecards reveals the original text, the
rewritten text, and a bulleted "what changed" list. Verified live: recorded
a baseline attempt with a hedge and a trailing recommendation, clicked
through, and confirmed the panel correctly moved the recommendation
sentence first and stripped the hedge, with an accurate explanation of
both changes.

### Voice AI roleplay — single- and multi-persona (§4.2 — "streaming STT → LLM → TTS")

Three legs, three different levels of "real" in this environment:

- **STT**: fully reused, not reimplemented — `api.deps.get_stt()`, the
  same seam Practice Studio uses (mock here for the same reason: no live
  vendor key). A roleplay turn's audio is transcribed in-memory from the
  request body and **never stored** — tighter than the 30-day media
  retention default elsewhere (§6.5), since there's no product reason to
  keep it at all for a roleplay turn.
- **LLM** (persona reply generation): same seam-plus-mock pattern as
  `api.pipeline.llm`/`api.pipeline.exemplar`. `api/pipeline/roleplay.py`'s
  `RoleplayLLMProvider` is what a real frontier-model integration
  implements; `MockRoleplayLLMProvider` is rule-based — it reuses the
  same `metrics.hedging` detector already in the pipeline to react when
  the user hedges, and otherwise cycles through the persona's scripted
  pressure questions. Not a language model, stated as such.
- **TTS**: **genuinely real**, no mock needed — the persona's lines are
  spoken aloud by the browser's native `SpeechSynthesis` API
  (`web/src/lib/tts.ts`), the same "the browser already has this
  capability, use it directly" move as Web Push's own push service.

One session model covers both single- and multi-persona conversations —
`RoleplaySession.persona_ids` is a JSON list, length 1 for single-persona,
2+ for multi (§4.2's second roleplay item), rather than two separate
session shapes for what's the same conversation with more speakers on one
side. Three personas ship: Priya (skeptical stakeholder), Marcus
(data-driven skeptic), Elena (time-pressured executive) — each with its
own opening line, follow-up bank, and closing line.

**Multi-persona turn-taking**: `pick_next_persona()` round-robins whose
turn it is to respond (1st user turn → `persona_ids[0]`, 2nd →
`persona_ids[1]`, ...), and a shared `GROUP_MAX_USER_TURNS` (4) closes the
conversation regardless of how many personas are in it — a 3-persona panel
doesn't take 3x as many rounds just because there are more speakers.
`RoleplayTurn.persona_id` records which persona said which line so the
frontend can attribute (and could pick different TTS voices per persona,
not implemented here).

| Endpoint | Behavior |
|---|---|
| `GET /roleplay-personas` | The catalog: id, name, role, description |
| `POST /roleplay-sessions` | Create a session — `persona_id` (single) or `persona_ids` (multi, 2+); returns it with the first persona's opening line as turn 0 |
| `GET /roleplay-sessions/{id}` | Full turn history + status (`active`/`completed`) |
| `POST /roleplay-sessions/{id}/turns` | Submit one recorded turn (raw audio body): transcribes, appends the user turn, picks the next responding persona, generates + appends their reply, closes the conversation once the turn budget is spent |

**Frontend**: `/roleplay` — select one persona, or multiple for a panel
(toggled as chips), hear/see the opening line, respond via the same
dev-mode sample-transcript picker Practice Studio uses (no live STT vendor
in this environment, same documented gap), watch personas react and take
turns, and see the conversation close out. Verified live for both modes:
single-persona correctly detected a hedge ("maybe") and reacted to it
mid-conversation; a 2-persona panel round-robinned correctly (Priya →
Marcus → Priya → Marcus) and closed on the shared turn budget rather than
per-persona, with each line correctly attributed to the persona who said it.

### Calendar integration driving pre-meeting prompts (§4.2 — "the core retention mechanism")

§8 calls calendar-triggered prompts "the highest-leverage feature in the
entire document": *"Standup in 40 minutes — one interjection drill?"*
The vendor gap here is the least workaroundable of any in this project —
real Google Calendar/Microsoft Graph integration needs an actual OAuth app
registration (client id/secret, redirect URI, consent screen), which isn't
something a client-side trick (à la Web Push or SpeechSynthesis) can
substitute for. So `api/calendar.py` follows the seam-plus-mock pattern
one more time: `CalendarProvider` is what a real OAuth integration
implements; `MockCalendarProvider` simulates a successful connection and
returns two synthetic upcoming events (relative to "now," not
wall-clock-fixed, so a demo run next week still works).

**What's genuinely real**: matching an imminent event to a practice
prompt. `next_prompt_worthy_event()` finds the earliest upcoming event
within a lookahead window (60 min); `guess_drill_criterion()` maps an
event's title to a relevant drill via simple keyword matching (standup →
point-first clarity, 1:1 → structure, review → concision), reusing the
existing `DRILL_CATALOG` (§4.1 M7) rather than inventing a parallel one.

| Endpoint | Behavior |
|---|---|
| `POST /users/{id}/calendar/connect` | Simulates a successful connection (mock provider) |
| `GET /users/{id}/calendar` | Connection status |
| `DELETE /users/{id}/calendar` | Disconnect |
| `GET /users/{id}/calendar/upcoming-prompt` | The genuinely real part: is there an imminent event, and if so which drill to suggest. No scheduler exists in this environment (same documented gap as `purge_expired_media`) to turn this into a proactive Web Push notification on its own — it's polled on demand instead (the frontend checks it on page load) |

**Frontend**: `CalendarSettings.tsx` on `/settings` connects/disconnects;
`UpcomingPromptBanner.tsx` on the home page polls the endpoint and — only
when a real prompt exists — shows exactly the copy §8 describes, with a
one-click link into the relevant drill. Verified live: connected the mock
calendar, then confirmed the home page showed "Team Standup in 30 minutes
— one-breath recommendation?" with a working link to the drill.

### Privacy controls (§4.1 M11, §6.5)

| Endpoint | Behavior |
|---|---|
| `DELETE /sessions/{id}` | One-click session delete — media + every derived row for that session |
| `DELETE /users/{id}` | Account delete — every session's data (via the same code path above), the L1 profile, and the user row |
| `GET /users/{id}/export` | Full export — profile + every session's transcript, metrics summary, and feedback, as JSON |
| `POST /admin/purge-expired-media?retention_days=30` | Deletes raw media older than the retention window; **derived metrics and feedback are untouched** — only the audio bytes and the `MediaAsset` row go |

`purge-expired-media` stands in for the scheduled job production would
run (§6.1 Celery/Arq beat, or a cron trigger) — this environment has no
scheduler, so it's an endpoint an operator or a real cron job calls.
It has no auth, which is fine for local dev but is a tracked gap before
any real deployment (needs an internal network boundary or admin
credential — out of scope here since auth itself is out of scope).
User-pinning a recording past the retention window (mentioned in §6.5)
isn't implemented — the purge is unconditional today.

### Editable transcript (§4.1 M8)

| Endpoint | Behavior |
|---|---|
| `GET /sessions/{id}/transcript` | The word list (empty until analyzed) |
| `PUT /sessions/{id}/transcript` | Submit corrected words (same count/order — timestamps aren't user-editable) and re-score |

Correcting a transcript re-runs `api.pipeline.orchestrator.score_words()`
— steps 5-9, metrics through drill recommendation — directly on the
corrected words, skipping STT entirely. A correction is scored exactly
like a first-pass transcript; there's no special-cased "corrected mode."
Every changed word is logged to `TranscriptCorrection` before re-scoring,
capturing the speaker's L1 background at that moment as an ASR-quality
signal (§6.6) — not a live join to `L1Profile`, so a later profile edit
or account deletion can't quietly rewrite historical signal.

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

## Phase 3

### Team workspaces + custom scenarios + custom rubrics (§4.3)

Real, no vendor gap — but with one honestly-stated limitation baked into
the model itself: **this app has no auth/session system at all.**
`User` (api/db.py) has been anonymous and device-scoped since Phase 1;
nothing in Phase 3 changes that. `Team`/`TeamMembership`/`TeamInvite`
track membership and an `admin`/`member` role, and the frontend's `/team`
page shows role-gated-looking buttons ("Make admin," "Remove"), but
**nothing enforces it server-side** — any caller who knows a `team_id`
and a `user_id` can currently call any team endpoint. `api/routers/teams.py`
says this plainly in its module docstring rather than presenting a data
model as if it were a security boundary. A real deployment needs a login
system before team roles mean anything as access control.

| Endpoint | Behavior |
|---|---|
| `POST /teams` | Create a team; creator becomes its first `admin` member |
| `GET /teams/{id}` | Team + member list |
| `GET /users/{id}/teams` | Teams a user belongs to |
| `PUT /teams/{id}/members/{user_id}/role` | Change a member's role |
| `DELETE /teams/{id}/members/{user_id}` | Remove a member |
| `POST /teams/{id}/invites` | Create a one-time invite token (no email delivery — same no-SMTP gap as weekly summaries/reminders elsewhere; a real deployment's email provider would send the link) |
| `POST /team-invites/{token}/accept` | Join a team via an invite link; 410 if already used, 409 if already a member |
| `POST /teams/{id}/scenarios` / `GET` / `DELETE` | Custom scenarios — **genuinely real**: a team-authored title/prompt, usable as a real practice prompt |
| `POST /teams/{id}/rubrics` / `GET` / `DELETE` | Custom rubrics — stored and manageable for real, but **not yet consumed by scoring**: `MockLLMRubricProvider` (api/pipeline/llm.py) is rule-based over deterministic metrics and never reads `ScenarioRubric.criteria` at all, mock or custom. Wiring a team's criteria into what gets judged is only meaningful once a real LLM provider exists behind that seam — not a fake cosmetic toggle |

**Frontend**: `/team` — create/select a team, manage members and roles,
generate an invite link, author custom scenarios and rubrics.
`/team/join/[token]` accepts an invite. Verified live end to end across
two separate browser contexts (simulating two different users/devices):
created a team in context 1, generated an invite link, opened it in
context 2 (a different anonymous user), accepted it, and confirmed both
members now appear in the roster from either context.

### Audit logs + configurable retention (§4.3)

Both real, no vendor gap.

- **Audit logs**: `api/audit.py`'s `log_audit_event()` is deliberately
  dumb — one function, appends one immutable `AuditLogEntry` row, no
  redaction logic, no retention policy of its own (audit entries are
  never purged by `api.lifecycle`, and nothing else in the app updates or
  deletes them, including account/team deletion). Wired into every
  sensitive team action: create, invite create/accept, member
  role-change/removal, scenario/rubric create/delete, retention changes.
  Where an action's endpoint has no session to identify its caller (no
  auth system — see the team-workspaces section above), it accepts an
  optional `acting_user_id` that's recorded as **self-reported**, not
  verified — stated in the endpoint's docstring rather than implied to be
  trustworthy.
- **Configurable retention**: `Team.retention_days` overrides the global
  30-day default (`api.lifecycle.DEFAULT_RETENTION_DAYS`) for a team.
  `effective_retention_days()` resolves a user's *actual* retention window
  by taking the **most restrictive** setting across every team they
  belong to (retention is a privacy floor, not something a lenient team
  membership can override) — teams with no override don't count as
  "unlimited" and can't win that comparison. `purge_expired_media` now
  computes this per-asset via the asset's owning session's user, instead
  of a single global cutoff.

| Endpoint | Behavior |
|---|---|
| `GET` / `PUT /teams/{id}/retention` | Read/set the override; `null` clears it back to the default |
| `GET /teams/{id}/audit-log` | Full history for a team, newest first |

**Frontend**: `/team` gained "Retention" and "Audit log" cards. Verified
live: set a team's retention to 7 days, confirmed "Currently effective: 7
days" reflected it immediately, and saw both the `team.create` and
`team.retention.update` entries appear in the audit log with correct
actor/target/detail data.

### Manager aggregate analytics (§4.3 — "recording access off by default")

`api/analytics.py` computes team-level and per-member aggregates (average
words/min, filler rate, hedging rate, point-position score) from
already-computed `metrics_summary` data — no new metric, no model call.
"Off by default" is implemented as an absolute rather than a defaulted-off
toggle: `AttemptMetrics`/`MemberAnalytics`/`TeamAnalytics` have no field
capable of carrying a recording, transcript, or feedback item at all —
verified by a test that asserts the dataclass's field set directly, and
an API test that greps the full JSON response for "transcript",
"feedback_items", "audio", and "media" and asserts none appear.

| Endpoint | Behavior |
|---|---|
| `GET /teams/{id}/analytics` | Team + per-member aggregates. A member with zero attempts still appears with `attempt_count: 0` rather than being silently omitted |

**Frontend**: the `/team` page's "Manager analytics" card shows the
aggregate tiles + a per-member attempt-count/avg-WPM row. Verified live:
created a team, practiced one session, and confirmed the dashboard
reflected the real computed metrics (300 wpm, 1 attempt) rather than
placeholder data.

## `web/` — Practice Studio (§4.1 M1/M2, §5 first-session flow)

A real Next.js frontend, not fake data — it drives the actual FastAPI
backend above.

- **Mic capture is entirely real**: `getUserMedia` + `MediaRecorder`,
  a live Web Audio level meter, countdown, timer, restart, and local
  playback (`src/lib/useAudioRecorder.ts`, `src/components/RecorderPanel.tsx`).
- **Upload is entirely real**: recordings go through the same
  offset-tracked, resumable chunked upload
  (`src/lib/chunkedUpload.ts`) that hits `POST /sessions/{id}/media`
  on the backend.
- **Analysis uses a dev-mode stand-in**: no live STT vendor is wired
  up yet (§6.2 — nothing here uses Whisper, but nothing here uses a
  real vendor either). Since the backend's mock STT expects a JSON
  word-list rather than decoded audio, the UI's dev-mode transcript
  picker (`src/components/DevTranscriptPicker.tsx`,
  `src/lib/sampleTranscripts.ts`) sends one of three scripted sample
  transcripts through that same upload path so the scorecard, evidence
  links, and drill recommendation are all exercising the real backend
  end to end. The real recording still plays back locally regardless —
  it's just not what gets analyzed yet. This is labelled in the UI,
  not hidden, and is the one seam to remove once a real STT provider
  is wired into `api/pipeline/stt.py`.
- **Onboarding** (`src/app/onboarding/page.tsx`, §4.1 M1): pick a
  context, optionally give a first language + self-declared English
  confidence ("this only shapes onboarding copy — it's never used to
  score your recordings," stated in the UI, not just this README). This
  `POST /users` + `PUT /users/{id}/l1-profile`, stores the returned user
  id in `localStorage` (`src/lib/localUser.ts`), and hands off into the
  same baseline-recording flow with the context preselected via a query
  param — no duplicate context picker. The first-language field is now a
  chip picker sourced from `GET /l1-calibration-profiles` (§4.2), showing
  a calibration note the moment a language is picked; an "Other / prefer
  not to say" chip falls back to free text for anyone outside the catalog.
- Flow implemented: onboarding → baseline recording → scorecard (one
  strength, up to three evidence-linked priorities each with a
  useful/not-useful rating, one drill) → retry the drill → before/after
  delta (`src/app/practice/page.tsx`). A retry session is created with
  `parent_session_id` pointing at the baseline session, so the
  `attempt_link` relationship in the schema above is populated by real
  usage, not just backfilled.
- **Progress** (`src/app/progress/page.tsx`, §4.1 M9): first attempt vs.
  best attempt vs. latest attempt, per metric, plus a full attempt
  history — pulled from `GET /users/{id}/attempts`. Self-relative only,
  by design: no percentile ranking against other users, matching the
  scope doc's stated reasoning that such scores are "proxies with
  contested validity" (§2.3).
- **Settings** (`src/app/settings/page.tsx`, §4.1 M11): export your data
  (downloads the `GET /users/{id}/export` JSON as a file) and delete
  your account (two-click confirm — the button re-labels itself "click
  again to confirm" rather than the scope's literal "one-click," since
  an irreversible action deserves a beat of friction; still no modal
  dialog).
- **Visible recording indicator** (§6.5): `RecorderPanel` shows a
  pulsing red dot + "Recording" label — `role="status"
  aria-live="assertive"` — for the entire duration a session is
  actually recording, not just implied by the timer running.
- **Editable transcript** (`src/components/EditableTranscript.tsx`, §4.1
  M8): click any word in the scorecard's transcript to correct it inline;
  "Save corrections & re-analyze" submits the full corrected word list
  and replaces the scorecard with freshly re-scored feedback — verified
  live that correcting a hedge word away from a recording drops the
  hedging-rate metric and removes the corresponding feedback item.
- **Reminder + streak** (§4.1 M10): `src/components/ReminderSettings.tsx`
  on `/settings` picks days + time and saves via `PUT /users/{id}/reminder`
  — verified live that the choice persists across a page reload.
  `src/components/StreakBadge.tsx` on `/progress` shows the current/
  longest non-punitive streak from `GET /users/{id}/streak`.
- **Billing** (`src/components/BillingSettings.tsx`, §4.1 M12): shows
  the current plan and, on free tier, this month's analysis count
  against the limit. "Upgrade" buttons are explicitly labelled mock —
  there's no hosted Stripe checkout page to redirect to, so upgrading
  creates and immediately confirms a mock checkout. `PracticeStudio`
  catches a `402` from `/analyze` and shows an upgrade prompt instead of
  a generic error — verified live end to end (free tier shows "1/3
  analyses used," upgrading to Pro removes the counter entirely).
- A four-link nav bar (Home/Practice/Progress/Settings) ties the pages
  together (`src/components/NavBar.tsx`).
- **Installable PWA + Web Push** (§4.2): `manifest.webmanifest` + `sw.js`
  make the app installable (including the iOS home-screen path §4.2
  explicitly calls out); `PushSettings.tsx` on `/settings` wires real
  subscribe/unsubscribe/test-send. See the Phase 2 section above for
  what was verified live vs. what this sandbox's browser genuinely
  can't reach.

### Running

```bash
# terminal 1 — backend
pip install -e ".[dev]"
CORS_ALLOW_ORIGINS=http://localhost:3000 uvicorn api.main:app --reload

# terminal 2 — frontend
cd web
cp env.example .env.local   # NEXT_PUBLIC_API_URL, defaults to localhost:8000
npm install
npm run dev
# → http://localhost:3000/onboarding
```

`/practice` also works directly without onboarding first — session
creation's `user_id` is optional, matching the no-card free tier (§8.1);
onboarding is there to attach an L1 profile, not gate access.

## What's still out of scope

**Auth — the single biggest standing gap.** The `User` table has been
anonymous/device-scoped since Phase 1; there is still no login system
anywhere in this app. Phase 3's team roles (`admin`/`member`) are tracked
but **not enforced** as a result — stated plainly in `api/routers/teams.py`
rather than presented as real access control. Every other gap in this
project is a vendor-credential problem; this one is architectural, and
would need solving before team/manager features are safe to expose beyond
a demo.

Every §4.1 MVP checklist item (M1-M12) and all eight §4.2 (Phase 2) items
are complete. §4.3 (Phase 3) is in progress: team workspaces and custom
scenarios are genuinely real (modulo the auth gap above); custom rubrics
are stored but not yet consumed by scoring (same reason as the mock LLM
rubric provider generally — see `api/pipeline/llm.py`). Going further on
the vendor-credential gaps (Stripe, AssemblyAI/Deepgram, a frontier LLM,
Google/Microsoft OAuth for calendar) means real credentials this
environment doesn't have; every one of those follows the same
provider-seam-plus-mock pattern, documented at each seam.

## Testing

```bash
# metrics + API
pytest --cov=metrics --cov=api --cov-report=term-missing

# frontend
cd web && npx tsc --noEmit && npm run lint && npm run build
```

340 backend tests, 99% line coverage as of this commit.
