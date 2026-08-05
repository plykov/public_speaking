"""Onboarding (§4.1 M1): anonymous user + L1 profile.

No auth — a User row is created on demand and the client holds the id
(e.g. localStorage). L1Profile captures first language and self-declared
English confidence for onboarding copy and calibration only; nothing in
api/pipeline/llm.py or metrics/report.py reads this table.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.db import AnalysisResult, L1Profile, PracticeSession, Reminder, User, get_db
from api.deps import get_object_store
from api.lifecycle import delete_user_data, export_user_data
from api.schemas import (
    AttemptSummaryOut,
    CreateL1ProfileRequest,
    L1ProfileOut,
    ReminderOut,
    StreakOut,
    UpsertReminderRequest,
    UserOut,
)
from api.storage import ObjectStore
from api.streaks import compute_streak

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(db: OrmSession = Depends(get_db)) -> User:
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: OrmSession = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.put("/{user_id}/l1-profile", response_model=L1ProfileOut)
def upsert_l1_profile(
    user_id: str, body: CreateL1ProfileRequest, db: OrmSession = Depends(get_db)
) -> L1Profile:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    profile = db.query(L1Profile).filter_by(user_id=user_id).one_or_none()
    if profile is None:
        profile = L1Profile(user_id=user_id, **body.model_dump())
        db.add(profile)
    else:
        profile.first_language = body.first_language
        profile.self_declared_confidence = body.self_declared_confidence
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{user_id}/l1-profile", response_model=L1ProfileOut)
def get_l1_profile(user_id: str, db: OrmSession = Depends(get_db)) -> L1Profile:
    profile = db.query(L1Profile).filter_by(user_id=user_id).one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="no L1 profile for this user yet")
    return profile


@router.get("/{user_id}/export")
def export_user(user_id: str, db: OrmSession = Depends(get_db)) -> dict[str, Any]:
    """Full account export (§4.1 M11): profile + every session's transcript,
    metrics summary, and feedback."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return export_user_data(db, user)


@router.delete("/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> None:
    """Account delete (§4.1 M11, §6.5): every session's media/rows, the L1
    profile, and the user row."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    delete_user_data(db, store, user_id)
    db.commit()


@router.get("/{user_id}/attempts", response_model=list[AttemptSummaryOut])
def list_attempts(user_id: str, db: OrmSession = Depends(get_db)) -> list[AttemptSummaryOut]:
    """§4.1 M9: self-relative progress data, oldest first.

    Only completed, analyzed sessions for this user — no cross-user
    comparison, no percentile ranking, by design (§4.1 M9: "Self-relative
    trends only. No percentile ranking against an opaque population.").
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    rows = (
        db.query(PracticeSession, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == user_id)
        .order_by(AnalysisResult.created_at.asc())
        .all()
    )

    attempts: list[AttemptSummaryOut] = []
    for session, analysis in rows:
        summary = analysis.metrics_summary
        attempts.append(
            AttemptSummaryOut(
                session_id=session.id,
                parent_session_id=session.parent_session_id,
                scenario=session.scenario,
                created_at=analysis.created_at,
                wpm_overall=summary.get("wpm_overall", 0.0),
                filler_rate_per_100_words=summary.get("filler_rate_per_100_words", 0.0),
                hedging_rate_per_100_words=summary.get("hedging_rate_per_100_words", 0.0),
                point_position_score=(summary.get("point_position") or {}).get("score", 0.0),
            )
        )
    return attempts


@router.put("/{user_id}/reminder", response_model=ReminderOut)
def upsert_reminder(
    user_id: str, body: UpsertReminderRequest, db: OrmSession = Depends(get_db)
) -> Reminder:
    """§4.1 M10: store a reminder window preference.

    Calendar-free v1 — no calendar integration (Phase 2), and no
    scheduler/email delivery in this environment to actually send one
    (same gap as `api.lifecycle.purge_expired_media`). This endpoint
    stores the preference; acting on it is a follow-up.
    """
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    reminder = db.query(Reminder).filter_by(user_id=user_id).one_or_none()
    if reminder is None:
        reminder = Reminder(user_id=user_id, days=body.days, time_of_day=body.time_of_day)
        db.add(reminder)
    else:
        reminder.days = body.days
        reminder.time_of_day = body.time_of_day
    db.commit()
    db.refresh(reminder)
    return reminder


@router.get("/{user_id}/reminder", response_model=ReminderOut)
def get_reminder(user_id: str, db: OrmSession = Depends(get_db)) -> Reminder:
    reminder = db.query(Reminder).filter_by(user_id=user_id).one_or_none()
    if reminder is None:
        raise HTTPException(status_code=404, detail="no reminder set for this user yet")
    return reminder


@router.get("/{user_id}/streak", response_model=StreakOut)
def get_streak(user_id: str, db: OrmSession = Depends(get_db)) -> StreakOut:
    """§4.1 M10: non-punitive streak — one skipped day tolerated per run.
    Self-relative, like Progress (§4.1 M9): no comparison to other users."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    rows = (
        db.query(AnalysisResult.created_at)
        .join(PracticeSession, PracticeSession.id == AnalysisResult.session_id)
        .filter(PracticeSession.user_id == user_id)
        .all()
    )
    practice_dates = {r.created_at.date() for r in rows}
    result = compute_streak(practice_dates, today=datetime.now(timezone.utc).date())

    return StreakOut(
        current_streak=result.current_streak,
        longest_streak=result.longest_streak,
        freeze_used_in_current_streak=result.freeze_used_in_current_streak,
        last_practice_date=(
            result.last_practice_date.isoformat() if result.last_practice_date else None
        ),
    )
