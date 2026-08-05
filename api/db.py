"""Persistence layer (§6.4 core entities).

Uses SQLAlchemy against `DATABASE_URL` — SQLite by default for dev,
Postgres in production per §6.1 ("no media in Postgres" — only
`MediaAsset.storage_key` is stored here, the bytes live in the object
store).

Normalizes the entities that matter for onboarding, coaching, and
progress: `user`, `l1_profile`, `session`, `media_asset`,
`transcript_segment` (as `TranscriptWord`, word-level), `metric_event`,
`feedback_item` (with `user_rating` for the thumbs up/down in §4.1 M6),
`attempt_link` (as `PracticeSession.parent_session_id`, a
self-referencing FK — simpler than a join table for a 1:1 original↔retry
relationship, semantically the same as §6.4's `attempt_link`), and
`TranscriptCorrection` for the M8 editable-transcript quality signal.

Deliberately **not** modeled yet: `goal`, `scenario` (kept as a plain
string — no admin CRUD for scenarios was asked for), `rubric_version`
(kept as a string field — the rubric itself is code-defined in
`api/pipeline/llm.py`, not database-editable), `skill_trend`,
`reminder`, `subscription`. Those belong to M9 (Progress), M10 (Habit
layer), and M12 (Billing) respectively — out of scope for the
onboarding + schema work this migration covers.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    Session as OrmSession,
    mapped_column,
    relationship,
    sessionmaker,
)

from api.config import settings


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    """Anonymous, device-scoped account (§4.1 M12 "no-card free tier").

    No email/password — auth is explicitly out of scope. This row exists
    so onboarding, L1 calibration, and attempt history have somewhere to
    attach; the client holds the id (e.g. localStorage) and sends it back.
    """

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    l1_profile: Mapped["L1Profile | None"] = relationship(back_populates="user", uselist=False)


class L1Profile(Base):
    """First-language + self-declared confidence (§4.1 M1).

    Used for onboarding copy and dev-mode sample-transcript calibration
    ONLY. Never passed into scoring — see api/pipeline/llm.py and
    metrics/report.py, neither of which accepts or reads this table.
    """

    __tablename__ = "l1_profiles"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    first_language: Mapped[str] = mapped_column(String)
    self_declared_confidence: Mapped[str] = mapped_column(String)  # e.g. "building"|"comfortable"|"fluent"
    # §4.2: a catalog code (see api/l1_calibration.py) when the user picked a
    # known L1 background; None for free-text-only or "prefer not to say".
    first_language_code: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="l1_profile")


class Reminder(Base):
    """§4.1 M10: user-set reminder window. Calendar-free v1 — no calendar
    integration (Phase 2) and no email delivery here; storing the
    preference is the whole scope of this table. Actually sending a
    reminder needs the scheduler this environment doesn't have (§6.1),
    same gap as `api.lifecycle.purge_expired_media`.
    """

    __tablename__ = "reminders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    days: Mapped[list] = mapped_column(JSON)  # e.g. ["mon","wed","fri"]
    time_of_day: Mapped[str] = mapped_column(String)  # "HH:MM", 24h, no timezone handling yet
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PushSubscription(Base):
    """§4.2: Web Push registration — a browser `PushSubscription.toJSON()`.

    `endpoint` is unique because it *is* the subscription's identity —
    the same browser/device re-subscribing (e.g. after clearing storage)
    gets a new endpoint, and the old one is naturally orphaned rather
    than colliding with anything.
    """

    __tablename__ = "push_subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    endpoint: Mapped[str] = mapped_column(String, unique=True)
    p256dh: Mapped[str] = mapped_column(String)
    auth: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Subscription(Base):
    """§4.1 M12, §8.1 commercial model.

    A user with no row here (or an expired `event_sprint`) is on the
    free tier by construction — see `api.billing.effective_tier()`. No
    real Stripe integration exists; `checkout_session_id` /
    `provider_customer_id` are seams for one, populated by
    `api.billing.MockBillingProvider` today.
    """

    __tablename__ = "subscriptions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), unique=True)
    tier: Mapped[str] = mapped_column(String, default="free")  # free|pro|event_sprint|team
    status: Mapped[str] = mapped_column(String, default="active")  # active|canceled
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    provider_customer_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class CheckoutSession(Base):
    """A pending mock checkout — created by `POST /users/{id}/checkout`,
    resolved by `POST /billing/checkout/{id}/confirm` standing in for a
    Stripe webhook (§6.1: no payment provider is wired up here)."""

    __tablename__ = "checkout_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    tier: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String, default="pending")  # pending|completed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class PracticeSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    parent_session_id: Mapped[str | None] = mapped_column(
        ForeignKey("sessions.id"), nullable=True
    )  # §6.4 attempt_link: set on a retry, pointing at the original attempt
    scenario: Mapped[str] = mapped_column(String, default="general")
    status: Mapped[str] = mapped_column(String, default="created")  # created|uploading|analyzing|complete|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class TranscriptWord(Base):
    """§6.4 `transcript_segment`, word-level."""

    __tablename__ = "transcript_words"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    seq_index: Mapped[int] = mapped_column(Integer)
    text: Mapped[str] = mapped_column(String)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    confidence: Mapped[float] = mapped_column(Float)


class TranscriptCorrection(Base):
    """§4.1 M8: a user-submitted ASR correction, logged as a quality signal.

    `l1_first_language` is a snapshot taken at correction time (not a
    live FK to `L1Profile`) so a later profile edit or account deletion
    doesn't rewrite or orphan the historical signal this table exists to
    preserve — the whole point is measuring ASR quality by L1 cohort
    over time (§6.6).
    """

    __tablename__ = "transcript_corrections"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    seq_index: Mapped[int] = mapped_column(Integer)
    original_text: Mapped[str] = mapped_column(String)
    corrected_text: Mapped[str] = mapped_column(String)
    l1_first_language: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MetricEventRow(Base):
    """§6.4 `metric_event` (type, start_ms, end_ms, value)."""

    __tablename__ = "metric_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    type: Mapped[str] = mapped_column(String)
    start_ms: Mapped[int] = mapped_column(Integer)
    end_ms: Mapped[int] = mapped_column(Integer)
    value: Mapped[dict | str | None] = mapped_column(JSON, nullable=True)


class FeedbackItemRow(Base):
    """§6.4 `feedback_item`, including `user_rating` for the M6 thumbs up/down."""

    __tablename__ = "feedback_items"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    rank: Mapped[int] = mapped_column(Integer)  # 0 = top priority; max 3 per §4.1 M6
    criterion: Mapped[str] = mapped_column(String)
    observation: Mapped[str] = mapped_column(String)
    rationale: Mapped[str] = mapped_column(String)
    repair: Mapped[str] = mapped_column(String)
    evidence_text: Mapped[str] = mapped_column(String)
    evidence_start_ms: Mapped[int] = mapped_column(Integer)
    evidence_end_ms: Mapped[int] = mapped_column(Integer)
    user_rating: Mapped[bool | None] = mapped_column(Boolean, nullable=True)  # None=unrated, True=useful, False=not useful


class AnalysisResult(Base):
    """Per-attempt rubric/model version stamp + computed summary + drill snapshot.

    The summary is a derived aggregate (not one of §6.4's core entities),
    so it stays JSON rather than ~15 individual columns. The drill fields
    are a snapshot of whatever `DRILL_CATALOG` entry was recommended at
    analysis time, so a later catalog edit doesn't rewrite history.
    """

    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    rubric_version: Mapped[str] = mapped_column(String)
    model_version: Mapped[str] = mapped_column(String)
    metrics_summary: Mapped[dict] = mapped_column(JSON)
    drill_id: Mapped[str] = mapped_column(String)
    drill_title: Mapped[str] = mapped_column(String)
    drill_prompt: Mapped[str] = mapped_column(String)
    drill_duration_minutes: Mapped[str] = mapped_column(String)
    drill_targets_criterion: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SlideDeck(Base):
    """§4.2 — one PDF slide deck per session. `storage_key` is the PDF
    itself; per-page thumbnails are stored separately (rendered once at
    upload time, keyed by page index) since a talk with 40 slides
    shouldn't re-rasterize the whole deck on every transcript view."""

    __tablename__ = "slide_decks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    filename: Mapped[str] = mapped_column(String)
    page_count: Mapped[int] = mapped_column(Integer)
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class SlideTransition(Base):
    """§4.2 — one "the presenter advanced to slide N" mark, timestamped
    against the recording's elapsed milliseconds (same clock as
    `TranscriptWord.start_ms`), so a transcript word's slide is whichever
    transition's timestamp is the latest one at or before it."""

    __tablename__ = "slide_transitions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    slide_index: Mapped[int] = mapped_column(Integer)  # 0-based
    timestamp_ms: Mapped[int] = mapped_column(Integer)


class ShareLink(Base):
    """§4.2 — a private, tokenized read-only view for a coach/manager.

    No login for the viewer: the token itself is the credential (like a
    Google Docs "anyone with the link" share, not an account). Three
    independent permission flags, all opt-in and false by default —
    raw audio is never exposed through this at any permission setting,
    that's not a flag, it's a property of what the endpoint returns.
    """

    __tablename__ = "share_links"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"))
    token: Mapped[str] = mapped_column(String, unique=True)
    label: Mapped[str | None] = mapped_column(String, nullable=True)
    can_view_progress: Mapped[bool] = mapped_column(Boolean, default=True)
    can_view_transcripts: Mapped[bool] = mapped_column(Boolean, default=False)
    can_view_feedback: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


_engine = create_engine(
    settings.database_url,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(bind=_engine, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(_engine)


def get_db() -> OrmSession:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
