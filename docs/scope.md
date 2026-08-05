# Scope Document — Executive Communication Practice Webapp
**Working name:** Cadence
**Version:** 1.0 — adjudicated synthesis
**Date:** 5 August 2026
**Status:** Committed positions. Where a choice was contested, one option has been selected and the alternative recorded in Appendix A. This document is intended to be directly actionable by Claude Code.

---

## 0. Adjudication note

This scope replaces two prior deliverables.

**Deliverable A** (generic digital coaching PWA) is rejected in full: wrong category, four unbuildable or unlawful specifications (Web Bluetooth to Apple Health; HIPAA applicability; Whisper as the filler-detection transcription layer; emotion inference under EU AI Act Art. 5), and a twelve-month plan for a three-sided marketplace.

**Deliverable B** (public speaking) supplies the correct comp set and a sound feedback architecture, both retained. Its commercial thesis is rejected: it proposes "executive rehearsal" as differentiation while its own table quotes Yoodli occupying that exact position, and prices 2x above Yoodli with no unit economics.

The strategic correction is a segment change, detailed in §3 and §9.

---

## 1. Executive Summary

The category has consolidated around one loop — **speak → objective feedback → one targeted fix → retry → measurable delta**. That loop is no longer differentiating. Yoodli executes it well at $8/month in the browser, backed by roughly $60M raised and a $300M+ valuation as of December 2025, with Google, Snowflake and Databricks as enterprise logos. Any product whose pitch is "practise high-stakes executive speaking and get AI feedback" is competing with a funded incumbent on its stated positioning at a price it cannot beat.

Two structural facts define the opportunity:

1. **Retention, not capability, is the unsolved problem.** Use is episodic — people cram before a talk and leave. The peer-reviewed benchmark (JMIR scoping review, Jan 2025, 525,824 users) is a median 70% discontinuation within 100 days. Every product in the category is built around events, which guarantees churn.
2. **The recurring-need segment is under-served.** Non-native-English senior professionals in English-dominant workplaces do not have an event problem — they have a **daily meeting problem**. Interjecting, holding the floor, being taken as authoritative rather than tentative, being understood at speed. That need recurs weekly and does not resolve after the presentation.

**Cadence is a practice tool for non-native-English professionals who need to sound authoritative in English-language meetings.** Not a stage-fright product. Not a keynote rehearsal tool. A meeting-fluency gym.

MVP is deliberately narrow: browser capture, post-hoc analysis only, deterministic delivery metrics separated from LLM message-quality judgement, evidence-linked coaching tied to transcript timestamps, targeted drills, and interjection/hedging as first-class trained skills that no competitor teaches. No real-time coaching, no webcam analysis, no VR, no voice roleplay in v1 — each of these is a schedule, cost or legal risk with unproven retention value.

Commercial model does not fight Yoodli on consumer subscription. It runs a low-price habit tier for distribution and drives revenue into B2B/L&D from month six, which is where every survivor in this category found durable margin.

---

## 2. Market Analysis

### 2.1 Comp set and current state

| Product | Model | Price (Aug 2026) | Position | Verdict |
|---|---|---|---|---|
| **Yoodli** | Web, AI analysis + multi-persona roleplay, enterprise programs | Free (5 lifetime) / $8 Pro / $20 Advanced (annual) / Enterprise custom | Category leader. $40M Series B Dec 2025, ~$60M raised, $300M+ valuation. English-only. | **Primary threat.** Do not compete head-on. |
| **Orai** | Mobile-first, simple practice → one fix | ~$10–12/mo, enterprise custom | Cleanest loop in the category | Reviews cite lost recordings, save failures, payment friction. Reliability is a takeable advantage. |
| **Speeko** | iOS, deep curriculum + Roger Love content + optional human coaching | ~$8–30/mo, ~$50–90/yr | Best content library | Apple-centric. AI accuracy questioned in reviews. |
| **Poised** | Real-time desktop meeting coach | **Discontinued** | Acquired by Deepgram June 2024; tech repurposed into "Shortcut" | **The market trap.** Standalone consumer real-time coaching did not survive. |
| **VirtualSpeech** | Browser + VR, courses + AI avatars + certificates | ~$45/mo, ~$399/yr, enterprise | Blended learning + certification moat | Enterprise/education motion, not consumer. |
| **Ovation** | VR/desktop simulator, 3D audiences | ~$19.99 individual / ~$49.99 per seat org | Best simulated-audience realism | Setup friction for solo users. |
| **Quantified.ai** | Enterprise analytics, sight+sound+language scoring | Est. $60–110/seat/mo, 50+ seats | Premium enterprise pole | No public pricing. Regulated-industry sales roleplay focus. |
| **Ummo** | Filler-word tracker, one-time ~$1.99 | **Discontinued / removed** | Harvard/MIT origin | A cheap single-metric tool is not a business. |
| **LikeSo** | Habit-framed filler tracking, goals + reminders | Stagnant since ~2018 | Best early habit mechanics | Mechanics worth copying; product dead. |
| **Toastmasters Pathways** | Community + LMS, real audiences | Membership | Peer feedback + real audience | Software cannot replicate the community; dated digital layer. |

### 2.2 What the dead products teach

- **Poised** — real-time in-meeting coaching is technically impressive, commercially fragile, and its webcam eye-contact score broke on multi-monitor setups (a documented user complaint). Do not build real-time in v1.
- **Ummo** — a single metric is a feature, not a product.
- **LikeSo** — good habit mechanics without a curriculum or a recurring need still stalls.
- **PitchVantage** — survived only by pivoting from consumer to education/LMS. Consumer alone did not sustain it.

Every survivor moved upmarket. Plan the enterprise on-ramp from day one even while launching consumer.

### 2.3 Market gaps (ranked by defensibility)

1. **Recurring-need segments are ignored.** All products optimise for the event. Meeting fluency is weekly.
2. **Non-native English is treated as a localisation problem, not a curriculum problem.** Yoodli is English-only; nobody teaches interjection tactics, hedging reduction, or prosodic authority for L2 speakers. Roughly 70–75% of the world's English speakers are non-native.
3. **Scoring validity is unaddressed.** "Confidence" and webcam "eye contact" are proxies with contested validity and documented bias against non-native speakers. Honesty here is a marketing asset in a segment that is acutely sensitive to being judged.
4. **Reliability.** Orai and PitchVantage reviews both report lost recordings. A five-minute rehearsal destroyed by a failed upload is an unrecoverable trust event.
5. **Privacy.** Yoodli uses Starter/Pro session data to improve its platform and sells exclusion as a $20 tier feature. "We never train on your voice, at any price" is a clean differentiator for EU buyers.

### 2.4 Sizing

Soft-skills training is $37–39B globally (Mordor/IMARC 2025); the narrower communication-skills segment ~$5.8B (Dataintelo 2025). These vary wildly by scope definition and are directional only. The consumer app niche is small; the L&D budget is where the money is. The relevant substitute good is a human coach at roughly $200–600/hour — one session costs more than a year of any app in the table.

---

## 3. Target Audience Profile

### 3.1 Primary persona — commit here

**"Marta" — Senior manager, non-native English speaker, English-dominant European workplace**
- 32–48, technically or commercially senior, C1-level English, fully fluent in writing and 1:1.
- Works in an English-language company in NL/DE/FR/Nordics/CEE or a US multinational's European arm.
- **Job to be done:** be heard in meetings. Get into the conversation before the moment passes. Make a recommendation land without three qualifiers in front of it. Not be re-explained by a native-speaker colleague.
- **Failure modes she recognises in herself:** waiting for a gap that never comes; opening with context instead of the point; "maybe we could perhaps consider"; speaking fast under pressure and losing intelligibility; going flat and monotone in a second language because attention is on word retrieval.
- **Barriers:** does not want accent elimination and will reject a product that implies her accent is the problem. Will not practise in front of colleagues. Fears an AI grading her English.
- **Why she recurs:** the need is weekly, not event-driven. This is the retention thesis.

### 3.2 Secondary personas (serve, do not design for)

| Persona | Need | Priority |
|---|---|---|
| Rising native-speaker manager | Point-first structure, concision, Q&A composure | Serve with same product, second-tier marketing |
| Event-driven professional (interview, board, pitch) | Fast readiness, no subscription | Serve via non-renewing Event Sprint SKU |
| L&D / enablement buyer | Assign practice, see aggregate progress, never see raw recordings | Phase 3 revenue engine |
| Founder pitching investors | Q&A pressure-testing | Explicitly deprioritised — Yoodli owns this |
| Person with clinical glossophobia | Graded exposure, anxiety management | **Out of scope.** Do not make therapeutic claims. Signpost to VR exposure therapy / clinical support. |

### 3.3 Retention design implication

Marta's trigger already exists in her calendar: she has meetings. The product must attach to that trigger rather than manufacture a synthetic one. Streaks alone will not beat a 70% / 100-day baseline; a reason to open the app before Tuesday's standup will.

---

## 4. Core Features & Functionality

### 4.1 MVP (must-have)

**M1 — Onboarding & baseline**
- Select context: recurring meetings / presentation / interview / difficult conversation.
- Select first language and self-declared English confidence (used for calibration and copy, never for scoring).
- 60–90 second prompted baseline recording. First useful feedback in under 5 minutes.

**M2 — Practice Studio**
- Mic check with live level meter (Web Audio API). Camera optional and **off by default in v1**.
- Prompt display, countdown, timer, record, restart, playback, resumable upload.
- Local chunked recording that survives a network drop.

**M3 — Deterministic delivery metrics**
Computed from audio + word-level timestamps, never from an LLM:
- Words per minute, overall and rolling window.
- Filler rate (per 100 words) with per-instance timestamps.
- Pause distribution: count, mean, longest, mid-clause vs boundary pauses.
- Repetition and restart rate.
- Pitch range and variance (F0), energy variance — reported as *vocal variety*, never as "confidence."
- Speaking time and longest unbroken run.

**M4 — L2-specific analysis (the differentiator)**
- **Hedging index.** Detect and count hedging constructions (*maybe, perhaps, I think, sort of, just, a bit, I'm not sure but*) with timestamps and rewrite suggestions.
- **Point-position score.** Where in the response does the recommendation appear? Target: first sentence.
- **Intelligibility proxy.** ASR confidence per word plus rate-of-speech interaction — flag stretches where speed degrades recognition. Framed as "this section is hard to follow at that pace," never as an accent judgement.
- **Interjection drills.** Scenario prompts where the user must enter a running conversation at a specific cue. Scored on latency and opener strength.

**M5 — Message quality (LLM layer, versioned)**
Scenario-aware rubric evaluation of: point-first clarity, structure, concision, relevance, evidence, call to action. Structured output with mandatory evidence spans.

**M6 — Evidence-linked coaching**
Fixed format per item: **Observation → why it lands badly → specific repair → retry.** Maximum three priorities surfaced. Every item deep-links to the transcript timestamp. Every item has a thumbs up/down.

**M7 — Repair loop**
Feedback automatically generates one 2–5 minute drill targeting the top issue, then re-prompts the original attempt and shows a side-by-side delta.

**M8 — Editable transcript**
User can correct ASR errors and trigger re-analysis. Corrections logged as an ASR quality signal per language background.

**M9 — Progress**
Self-relative trends only. No percentile ranking against an opaque population. First attempt vs best attempt vs latest.

**M10 — Habit layer**
Calendar-free v1: user-set reminder windows, weekly summary email, optional non-punitive streak with freeze.

**M11 — Privacy controls**
Visible recording indicator, per-session delete, account delete, transcript/report export, raw-media retention setting (default 30-day auto-delete).

**M12 — Billing**
No-card free tier. Conspicuous renewal terms. Stripe.

**Explicitly excluded from MVP:** real-time nudges, webcam/gaze/gesture analysis, voice roleplay, VR, leaderboards, community, live meeting capture, emotion or personality inference (the last is prohibited, not deferred — see §6.5).

### 4.2 Phase 2 (should-have)

- **Voice AI roleplay**, single persona, turn-based. Streaming STT → LLM → TTS.
- **Calendar integration** (Google/Microsoft) driving pre-meeting prompts — the core retention mechanism.
- Slide/PDF upload with timing and slide-linked transcript.
- Exemplar mode: after the user's attempt, show a stronger version and explain the delta.
- Private share link for a coach or manager, granular permissions.
- Multi-persona roleplay.
- Installable PWA with Web Push (note: iOS requires home-screen install).
- Additional L1 calibration profiles (RU, NL, DE, FR, ES, PT-BR, ZH, HI, JA).

### 4.3 Phase 3 (nice-to-have)

- Team workspaces, custom scenarios, custom rubrics, manager aggregate analytics with recording access off by default.
- SSO/SCIM, SOC 2 Type II, audit logs, configurable retention.
- Post-meeting analysis of consented Zoom/Teams/Meet recordings (never live interception).
- LMS/SCORM.
- Optional peer practice rooms.
- Human coach marketplace.

---

## 5. User Experience Flow

Navigation, five items maximum: **Home · Practice · Learn · Progress · Settings**

**First session (target: <5 min to value)**
Pick context → pick top difficulty → 90s baseline → scorecard with one strength and three ranked fixes → one drill → retry baseline → before/after delta → generated weekly plan.

**Weekly loop (the retention loop)**
Reminder → 3–5 min drill tied to a meeting skill → record → single top coaching point → retry → progress tick.

**Event sprint**
"Prepare for something specific" → audience + outcome + talking points → rehearse → feedback → targeted repair → repeat → readiness comparison. Final screen answers *"what should I practise once more before tomorrow?"* not *"your score is 82."*

**Interaction principles**
- Recording is at most two clicks from any screen.
- Three priorities before any metric wall.
- Every criticism opens the exact moment that caused it.
- User can mark feedback wrong; that signal is logged.
- A completed recording is never lost to a network failure.
- Desktop optimised for full rehearsal; mobile for quick audio drills and progress review.

---

## 6. Technical Architecture

### 6.1 Stack (pinned)

| Layer | Choice | Rationale |
|---|---|---|
| Client | Next.js + TypeScript, responsive, PWA-ready | Browser-first; avoids app store tax and Speeko's iOS-only trap |
| Capture | `getUserMedia` + `MediaRecorder`, chunked | Standard, no plugin |
| Audio UX | Web Audio API | Level meter, waveform |
| API | Python / FastAPI | Colocated with audio/ML tooling |
| Workers | Celery or Arq + Redis | Media and analysis are async, never in the request path |
| DB | PostgreSQL | Transactional; **no media in Postgres** |
| Object store | S3-compatible, private, signed URLs, lifecycle rules | EU region |
| STT | **AssemblyAI or Deepgram Nova-3, disfluency mode on** | Word-level timestamps + per-word confidence |
| LLM | Current frontier model behind a provider abstraction | Rubric evaluation only |
| TTS | Phase 2 only | Roleplay |
| Billing | Stripe | — |
| Hosting | EU region (Frankfurt or Amsterdam) | Data residency as a sales asset |

### 6.2 Transcription — hard constraint

**Do not use Whisper for this product.** Whisper was trained to produce intended transcription and removes disfluencies (`um`, `uh`), and does not natively emit word-level timestamps. A filler-word product built on Whisper measures nothing. Use AssemblyAI or Deepgram with disfluency detection enabled. If a Whisper family model is ever required, use a verbatim variant such as CrisperWhisper and validate against a hand-labelled set first.

Known limits to design around: `um`/`uh` detect reliably; false starts, repetitions and self-repairs are substantially harder (open models correct self-repairs only ~40% of the time). Report what is measured accurately; do not invent precision.

### 6.3 Pipeline

1. Browser records in chunks; buffers locally.
2. Resumable multipart upload to private object storage.
3. Worker normalises audio (16 kHz mono WAV).
4. STT with word timestamps + per-word confidence.
5. **Deterministic metrics module** — pure functions, unit-tested, no model calls. WPM, fillers, pauses, F0, energy, hedging, point-position.
6. **LLM rubric evaluator** — receives transcript + scenario rubric + deterministic metrics. Never receives raw audio. Returns structured JSON.
7. **Evidence validator** — every quoted span must exist verbatim in the transcript; fail the item if not, never surface an unverifiable claim.
8. Persist result with `rubric_version` and `model_version`.
9. Emit recommended drill.

Deterministic and generative layers are separated so WPM does not change because a model had a different opinion.

### 6.4 Data model (core entities)

`user`, `l1_profile`, `goal`, `scenario`, `rubric_version`, `session`, `media_asset`, `transcript_segment` (word-level: text, start_ms, end_ms, confidence), `metric_event` (type, start_ms, end_ms, value), `feedback_item` (observation, rationale, repair, evidence_start_ms, evidence_end_ms, user_rating), `drill`, `attempt_link` (original ↔ retry), `skill_trend`, `reminder`, `subscription`.

Version rubrics and models so historical progress remains interpretable after a model change. A user's improvement curve must not be an artefact of a prompt edit.

### 6.5 Privacy, legal, and prohibited features

Voice recordings are biometric-adjacent. Non-negotiable defaults:

- TLS 1.3 in transit, AES-256 at rest, private buckets, short-lived signed URLs only.
- **No training on user recordings, at any tier, ever.** Not a paid upsell. This is the anti-Yoodli position.
- DPAs with STT and LLM vendors including explicit no-training terms.
- Raw media auto-delete at 30 days unless user-pinned; derived metrics retained.
- One-click session delete, account delete, full export.
- **No voiceprints. No speaker identification. No voice-based authentication.** Voice embeddings have been found to trigger Illinois BIPA, which carries a private right of action and an active class-action wave.
- **No emotion, mental-state, personality or ethnicity inference from voice or video.** EU AI Act Art. 5 prohibits emotion recognition in workplace and education contexts, applicable since 2 February 2025. This is a prohibition, not a roadmap item.
- GDPR: purpose limitation, minimisation, storage limitation, privacy by design. EU hosting. Legal review before any US biometric-law state launch.

### 6.6 Bias and evaluation gates

Build an internal evaluation set before launch spanning: L1 backgrounds (minimum RU, NL, DE, FR, ES, ZH, HI), gender, age range, microphone quality, quiet and noisy environments, fast and slow speech.

Measure and report separately:
- **ASR word error rate by L1 cohort.** If WER dispersion across cohorts exceeds an agreed threshold, mitigate before launch — a coaching penalty caused by a recognition failure is the single worst outcome for the primary persona.
- **Coaching quality**, independent of transcription accuracy.
- **Test–retest reliability** of the LLM rubric: same recording, ten runs. If score variance exceeds the improvement the product claims to detect, the score is noise. Gate launch on this.

### 6.7 Reliability and unit economics

- >95% of completed recordings must return usable analysis without a re-record. Treated as a launch gate, not a nice-to-have.
- Analysis jobs idempotent and retryable; processing state surfaced honestly.
- Cost envelope: STT ~$0.0025–0.0077/min. A 5-minute session lands around **$0.03–0.06** all-in including LLM. At 20 sessions/month per active paid user, COGS is roughly $1/user/month — comfortable at any price point in §8.
- Meter cost per analysed minute from day one.

### 6.8 Browser constraints

Test Safari/iOS explicitly: codec and container quirks in `MediaRecorder`, permission handling, background capture limits. Web Push on iOS requires home-screen installation. Assume nothing works on Safari until proven.

---

## 7. Content Strategy

### 7.1 Curriculum tracks

| Track | Content |
|---|---|
| **Meeting entry** (differentiator) | Interjection openers, cue recognition, floor-holding, recovering an interrupted turn |
| **Point-first** | BLUF, recommendation before context, the 30/60/120-second answer |
| **De-hedging** | Removing qualifiers without becoming blunt; register calibration for L2 speakers |
| **Vocal authority** | Pace control, intentional pause, projection, pitch variation under cognitive load |
| **Pressure & Q&A** | Objections, interruptions, "I don't know," buying thinking time in a second language |
| **Intelligibility** | Rate management, stress placement, chunking — never accent elimination |

### 7.2 Inventory for launch

- 30 micro-lessons (2–4 min).
- 50 impromptu prompts.
- 20 targeted drills.
- 8 scenarios × 3 difficulty levels.
- 8–10 versioned rubrics.
- **12–20 exemplar clips — treat as a budgeted production line item, not a content bullet.** Cast exemplar speakers with visible accent diversity. If the model of an "executive voice" is a deep American male voice, the primary persona churns immediately.

### 7.3 Governance

A qualified communication coach owns rubrics and curriculum; AI generates prompt and scenario variants under coach review. Content in a lightweight CMS tagged by skill, difficulty, scenario, audience, duration, rubric. Lessons showing >25% drop-off in the first 60 seconds are auto-flagged for rewrite.

---

## 8. Engagement & Retention

**The loop:** real meeting coming → 4-minute targeted drill → evidence → one fix → retry → visible delta → next meeting goes better.

Mechanisms, in priority order:
1. **Calendar-triggered prompts** (Phase 2, but the highest-leverage feature in the entire document). "Standup in 40 minutes — one interjection drill?"
2. First useful result under 5 minutes.
3. One recommended drill per day, never a queue.
4. Optional, non-punitive streak with freezes (LikeSo's mechanics, executed properly).
5. Weekly summary: best attempt vs latest, one skill trending up, one to work on.
6. Periodic baseline re-assessment — makes improvement legible.
7. Private coach/manager sharing (Phase 2).

No leaderboards, no public community in v1. The primary persona's dominant emotion is exposure risk; privacy is a retention feature, not a compliance cost.

**Benchmark to beat:** category baseline is a median 70% discontinuation within 100 days, and roughly 3–4% Day-30 retention for consumer health/fitness apps. Target **Day-30 ≥ 20%** for activated users (activated = completed baseline + one retry). If Day-30 sits below 10% after the pilot, the recurring-need thesis is falsified — see Appendix B.

**Instrumentation:** onboarding → first recording conversion; recording completion rate; processing success rate; retry-after-feedback rate (the single best leading indicator); sessions per active week; D7/D30; first-vs-best delta; feedback useful/not-useful ratio; transcript correction rate by L1 cohort; free→paid conversion; refund and privacy-support ticket rate.

### 8.1 Commercial model

Do not price above Yoodli on a comparable subscription. Compete on segment, not on price.

- **Free** — no card. Baseline + 3 full analyses/month + daily drills. Generous, because COGS is ~$0.05/session.
- **Pro — €9/month annual, €14 monthly.** Unlimited analysis, full curriculum, progress history.
- **Event Sprint — €29 one-time, 30 days, explicitly non-renewing.** Captures the episodic user honestly and converts a churn event into revenue. This is a marketing asset in a category where billing complaints are endemic.
- **Teams — from month 6, per seat, custom.** Where the margin is.
- **No lifetime plan.** Per-minute inference cost is perpetual.

---

## 9. Differentiation Strategy

Position: **"Be heard in English meetings."** Not "speak like a CEO."

Five defensible pillars:

1. **A segment the leader structurally cannot serve well.** Yoodli is English-only with an implicitly American executive-presence rubric. Cadence trains L2 professionals on interjection, hedging and intelligibility — skills nobody in the comp set teaches.
2. **Recurring need beats event need.** The competition is built for the talk; Cadence is built for Tuesday's standup. This is a retention advantage, not a feature advantage, and retention is the category's unsolved problem.
3. **Honest measurement.** Report what is measurable (filler rate, pace, pause, pitch variance, hedging, point position). Refuse to score "confidence." Publish the test–retest reliability of the rubric. In a segment afraid of being judged by a machine, epistemic honesty is a conversion asset.
4. **Never train on your voice — at every tier.** Directly contrasts with the incumbent selling data exclusion as a $20 upgrade. EU-hosted, EU-operated.
5. **Reliability as a feature.** Orai and PitchVantage reviews both report lost recordings. Guaranteeing a completed rehearsal is never destroyed is a low-glamour, high-trust win.

Deliberately conceded: keynote rehearsal, VR audiences, investor-pitch coaching, real-time meeting interception. Yoodli, VirtualSpeech and Ovation own or have killed these.

---

## 10. Implementation Roadmap

Assumes 4–6 people: 2 full-stack, 1 ML/audio, 1 design, 1 content coach (fractional), 1 PM.

| Phase | Duration | Deliverables | Exit gate |
|---|---|---|---|
| **0 — Calibration** | 3 weeks | 20 interviews with L2 senior professionals; hand-labelled 60-clip eval set across L1 cohorts; STT vendor bake-off (AssemblyAI vs Deepgram on filler + hedging recall); coach-authored rubric v1; clickable prototype; data map | STT vendor selected on measured recall, not marketing. Cohort WER dispersion quantified. Rubric test–retest variance measured. |
| **1 — MVP** | 12–14 weeks | Auth, onboarding, Practice Studio, chunked resumable capture, STT pipeline, deterministic metrics module, hedging + point-position analysis, LLM rubric with evidence validation, 8 scenarios, repair drills, progress, editable transcript, reminders, Stripe, delete/export | >95% of completed recordings analyse without re-record. 100% of surfaced evidence spans verified against transcript. Time-to-first-feedback <5 min. |
| **2 — Pilot** | 4 weeks | 80–120 L2 professionals, majority non-UK/US; Safari/iOS matrix; accessibility; pricing test | ≥60% of pilot users rate the top coaching item specific and actionable. Retry-after-feedback rate ≥40%. No unmitigated cohort WER disparity. |
| **3 — Retention engine** | 8 weeks | Calendar integration + pre-meeting prompts, voice roleplay (single persona), exemplar mode, coach share links, PWA install + push, additional L1 profiles | **Day-30 retention ≥20% for activated users.** This is the phase's only real gate. |
| **4 — Teams** | 10 weeks | Team workspaces, custom scenarios and rubrics, manager aggregate analytics (recordings off by default), permissions, retention controls, SSO foundation | 3 paid team pilots. Security questionnaire survivable. |
| **5 — Platform** | Ongoing | Consented post-meeting analysis, LMS, marketplace, optional peer rooms | Build only against evidenced retention or revenue lift. |

**The gate before anything else ships:** can a user record an answer, understand exactly why it did not land, make one targeted correction, retry, and see an objective improvement — with the improvement being real rather than measurement noise? Phase 0's test–retest number decides whether the rest of the roadmap is worth building.

---

## Appendix A — Rejected positions and why

| Position | Source | Ruling |
|---|---|---|
| Whisper for word-level timestamps | Deliverable A | **Rejected.** Whisper strips disfluencies. Fatal for the core metric. |
| Web Bluetooth → Apple Health / Google Health Connect | Deliverable A | **Rejected.** No Web Bluetooth in Safari/iOS; Apple Health has no web API. Not implementable. |
| HIPAA compliance | Deliverable A | **Rejected.** Category error; not a covered entity or business associate. |
| Computer-vision emotion analytics | Deliverable A | **Rejected as unlawful.** EU AI Act Art. 5, workplace context, in force since Feb 2025. |
| Three-sided coach marketplace in year one | Deliverable A | **Rejected.** Not buildable at that scope; not the category. |
| "Executive rehearsal, not speech scoring" positioning | Deliverable B | **Rejected.** Verbatim Yoodli's stated positioning against a $300M+ funded incumbent. |
| €15–19/mo Pro tier | Deliverable B | **Rejected.** 2x Yoodli with no unit-economic or differentiation justification. |
| Poised as a live competitor at $19/mo | Deliverable B | **Corrected.** Acquired by Deepgram June 2024; consumer product wound down. Reclassify as market-trap evidence. |
| Voice roleplay in MVP | Deliverable B | **Deferred to Phase 3.** Streaming STT→LLM→TTS is the schedule killer and is unproven for retention. |
| Webcam gaze/posture analysis | Both | **Deferred indefinitely.** Proxy validity is weak (Poised's eye-contact score broke on multi-monitor setups), and it converts the product into a face-biometrics processor. |
| Evidence-linked feedback, deterministic/LLM separation, rubric versioning, no-training default | Deliverable B | **Adopted.** The strongest content in either document. |
| LikeSo-style goal + reminder + countdown mechanics | Research | **Adopted.** Best habit mechanics in the category; the product is dead but the pattern is not. |

## Appendix B — Falsification tests

Each is a kill or pivot condition, not a risk to monitor.

1. **Rubric reliability.** Ten runs on one recording. If score variance exceeds the improvement the product claims to detect, the LLM scoring layer ships as qualitative coaching only, with no numeric score. *Test in Phase 0.*
2. **Cohort fairness.** If WER dispersion across L1 cohorts cannot be reduced to an acceptable band, the intelligibility feature is cut — it would penalise exactly the users it is meant to serve. *Test in Phase 0.*
3. **Recurring-need thesis.** If Day-30 retention for activated users is below 10% after Phase 3's calendar integration, the L2 meeting-fluency need is not recurring in practice. Pivot to the Event Sprint SKU as the primary product and abandon the subscription.
4. **Segment willingness to pay.** If free→paid conversion is under 2% by end of Phase 2, redirect all acquisition spend to B2B/L&D pilots and treat consumer as a lead-generation surface only.
5. **Differentiation durability.** If Yoodli ships L2-specific meeting coaching before Phase 3 completes, the wedge is gone; fall back to the privacy and EU-residency position and accelerate the Teams motion.
