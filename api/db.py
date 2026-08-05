"""Persistence layer (§6.4 core entities).

Uses SQLAlchemy against `DATABASE_URL` — SQLite by default for dev,
Postgres in production per §6.1 ("no media in Postgres" — only
`MediaAsset.storage_key` is stored here, the bytes live in the object
store).

Normalizes the entities that matter for onboarding, coaching, and
progress: `user`, `l1_profile`, `session`, `media_asset`,
`transcript_segment` (as `TranscriptWord`, word-level), `metric_event`,
`feedback_item` (with `user_rating` for the thumbs up/down in §4.1 M6),
and `attempt_link` (as `PracticeSession.parent_session_id`, a
self-referencing FK — simpler than a join table for a 1:1 original↔retry
relationship, semantically the same as §6.4's `attempt_link`).

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
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    user: Mapped[User] = relationship(back_populates="l1_profile")


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
