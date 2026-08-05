"""Shared data-lifecycle operations (§4.1 M11, §6.5): delete, export, retention.

Kept separate from the routers so `DELETE /sessions/{id}` and account
deletion (`DELETE /users/{id}`) share exactly one code path for wiping a
session's rows and media — no risk of one endpoint deleting fewer things
than the other.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session as OrmSession

from api.db import (
    AnalysisResult,
    CalendarConnection,
    CheckoutSession,
    FeedbackItemRow,
    L1Profile,
    MediaAsset,
    MetricEventRow,
    PracticeSession,
    PushSubscription,
    Reminder,
    RoleplaySession,
    RoleplayTurn,
    ShareLink,
    SlideDeck,
    SlideTransition,
    Subscription,
    TranscriptCorrection,
    TranscriptWord,
    User,
)
from api.slides import slide_thumbnail_key
from api.storage import ObjectStore

DEFAULT_RETENTION_DAYS = 30


def _media_key(session_id: str) -> str:
    return f"{session_id}/audio.raw"


def delete_session_data(db: OrmSession, store: ObjectStore, session_id: str) -> None:
    """Delete one session's media and every derived row. Does not commit.

    Includes `TranscriptCorrection` rows even though §6.6 wants those
    retained as an aggregate ASR-quality-by-cohort signal — privacy wins
    the tradeoff here, matching "account delete: every session's data."
    Losing correction history on delete is the accepted cost.
    """
    store.delete(_media_key(session_id))
    deck = db.query(SlideDeck).filter_by(session_id=session_id).one_or_none()
    if deck is not None:
        store.delete(deck.storage_key)
        for page in range(deck.page_count):
            store.delete(slide_thumbnail_key(session_id, page))
    db.query(SlideTransition).filter_by(session_id=session_id).delete()
    db.query(SlideDeck).filter_by(session_id=session_id).delete()
    db.query(TranscriptCorrection).filter_by(session_id=session_id).delete()
    db.query(TranscriptWord).filter_by(session_id=session_id).delete()
    db.query(MetricEventRow).filter_by(session_id=session_id).delete()
    db.query(FeedbackItemRow).filter_by(session_id=session_id).delete()
    db.query(AnalysisResult).filter_by(session_id=session_id).delete()
    db.query(MediaAsset).filter_by(session_id=session_id).delete()
    db.query(PracticeSession).filter_by(id=session_id).delete()


def delete_user_data(db: OrmSession, store: ObjectStore, user_id: str) -> None:
    """Account delete: every session's data, the L1 profile, reminder
    preference, push subscriptions, subscription/billing records, and the
    user row."""
    session_ids = [s.id for s in db.query(PracticeSession.id).filter_by(user_id=user_id).all()]
    for session_id in session_ids:
        delete_session_data(db, store, session_id)
    db.query(L1Profile).filter_by(user_id=user_id).delete()
    db.query(Reminder).filter_by(user_id=user_id).delete()
    db.query(ShareLink).filter_by(user_id=user_id).delete()
    roleplay_session_ids = [
        r.id for r in db.query(RoleplaySession.id).filter_by(user_id=user_id).all()
    ]
    for rid in roleplay_session_ids:
        db.query(RoleplayTurn).filter_by(roleplay_session_id=rid).delete()
    db.query(RoleplaySession).filter_by(user_id=user_id).delete()
    db.query(CalendarConnection).filter_by(user_id=user_id).delete()
    db.query(PushSubscription).filter_by(user_id=user_id).delete()
    db.query(CheckoutSession).filter_by(user_id=user_id).delete()
    db.query(Subscription).filter_by(user_id=user_id).delete()
    db.query(User).filter_by(id=user_id).delete()


def export_user_data(db: OrmSession, user: User) -> dict[str, Any]:
    """Full export (§4.1 M11): profile + every session's transcript, metrics, feedback."""
    l1_profile = db.query(L1Profile).filter_by(user_id=user.id).one_or_none()
    sessions = (
        db.query(PracticeSession)
        .filter_by(user_id=user.id)
        .order_by(PracticeSession.created_at.asc())
        .all()
    )

    session_exports = []
    for session in sessions:
        analysis = db.query(AnalysisResult).filter_by(session_id=session.id).one_or_none()
        words = (
            db.query(TranscriptWord)
            .filter_by(session_id=session.id)
            .order_by(TranscriptWord.seq_index)
            .all()
        )
        feedback_rows = (
            db.query(FeedbackItemRow)
            .filter_by(session_id=session.id)
            .order_by(FeedbackItemRow.rank)
            .all()
        )
        session_exports.append(
            {
                "session_id": session.id,
                "parent_session_id": session.parent_session_id,
                "scenario": session.scenario,
                "status": session.status,
                "created_at": session.created_at.isoformat(),
                "transcript": [
                    {
                        "text": w.text,
                        "start_ms": w.start_ms,
                        "end_ms": w.end_ms,
                        "confidence": w.confidence,
                    }
                    for w in words
                ],
                "metrics_summary": analysis.metrics_summary if analysis else None,
                "feedback_items": [
                    {
                        "criterion": f.criterion,
                        "observation": f.observation,
                        "rationale": f.rationale,
                        "repair": f.repair,
                        "evidence_text": f.evidence_text,
                        "user_rating": f.user_rating,
                    }
                    for f in feedback_rows
                ],
            }
        )

    return {
        "user_id": user.id,
        "created_at": user.created_at.isoformat(),
        "l1_profile": (
            {
                "first_language": l1_profile.first_language,
                "self_declared_confidence": l1_profile.self_declared_confidence,
            }
            if l1_profile
            else None
        ),
        "sessions": session_exports,
    }


def purge_expired_media(
    db: OrmSession,
    store: ObjectStore,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: datetime | None = None,
) -> int:
    """Delete raw media older than `retention_days`; derived metrics/feedback stay.

    §6.5: "Raw media auto-delete at 30 days unless user-pinned; derived
    metrics retained." No pinning UI exists yet, so this always purges —
    pinning is a follow-up, not implemented here. Intended to run on a
    schedule in production (§6.1); exposed as a callable + an admin
    endpoint since this environment has no cron/worker infra.
    """
    cutoff = (now or datetime.now(timezone.utc)) - timedelta(days=retention_days)
    expired = db.query(MediaAsset).filter(MediaAsset.created_at < cutoff).all()
    for asset in expired:
        store.delete(asset.storage_key)
        db.delete(asset)
    return len(expired)
