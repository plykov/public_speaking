"""Persistence layer (§6.4 core entities, simplified).

Uses SQLAlchemy against `DATABASE_URL` — SQLite by default for dev,
Postgres in production per §6.1 ("no media in Postgres" — only
`MediaAsset.storage_key` is stored here, the bytes live in the object
store).

This intentionally collapses `transcript_segment`, `metric_event`,
`feedback_item`, and `drill` into JSON columns on `AnalysisResult`
rather than fully normalizing them — that normalization is a follow-up
("Data model + Postgres schema" scope item), not something the pipeline
module needs to function or be tested.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, ForeignKey, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session as OrmSession, mapped_column, sessionmaker

from api.config import settings


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class PracticeSession(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    scenario: Mapped[str] = mapped_column(String, default="general")
    status: Mapped[str] = mapped_column(String, default="created")  # created|uploading|analyzing|complete|failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class MediaAsset(Base):
    __tablename__ = "media_assets"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    storage_key: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class AnalysisResult(Base):
    __tablename__ = "analysis_results"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"))
    rubric_version: Mapped[str] = mapped_column(String)
    model_version: Mapped[str] = mapped_column(String)
    transcript_text: Mapped[str] = mapped_column(String)
    metrics_summary: Mapped[dict] = mapped_column(JSON)
    metric_events: Mapped[list] = mapped_column(JSON)
    feedback_items: Mapped[list] = mapped_column(JSON)
    drill: Mapped[dict] = mapped_column(JSON)
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
