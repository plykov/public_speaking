"""Calendar integration driving pre-meeting prompts (§4.2).

See `api/calendar.py` for what's real (the imminent-event-to-drill
matching) vs. mocked (the calendar connection itself — no real
Google/Microsoft OAuth app registration in this environment).
"""

from __future__ import annotations

import math
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.calendar import CalendarProvider, guess_drill_criterion, next_prompt_worthy_event
from api.db import CalendarConnection, User, get_db
from api.deps import get_calendar
from api.pipeline.drills import DEFAULT_DRILL, DRILL_CATALOG
from api.schemas import (
    CalendarConnectionOut,
    ConnectCalendarRequest,
    DrillOut,
    UpcomingPromptOut,
)

router = APIRouter(prefix="/users", tags=["calendar"])


def _get_user_or_404(user_id: str, db: OrmSession) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.post("/{user_id}/calendar/connect", response_model=CalendarConnectionOut)
def connect_calendar(
    user_id: str, body: ConnectCalendarRequest, db: OrmSession = Depends(get_db)
) -> CalendarConnectionOut:
    _get_user_or_404(user_id, db)
    connection = db.query(CalendarConnection).filter_by(user_id=user_id).one_or_none()
    if connection is None:
        connection = CalendarConnection(user_id=user_id, provider=body.provider)
        db.add(connection)
    else:
        connection.provider = body.provider
    db.commit()
    return CalendarConnectionOut(connected=True, provider=connection.provider)


@router.get("/{user_id}/calendar", response_model=CalendarConnectionOut)
def get_calendar_connection(user_id: str, db: OrmSession = Depends(get_db)) -> CalendarConnectionOut:
    _get_user_or_404(user_id, db)
    connection = db.query(CalendarConnection).filter_by(user_id=user_id).one_or_none()
    if connection is None:
        return CalendarConnectionOut(connected=False)
    return CalendarConnectionOut(connected=True, provider=connection.provider)


@router.delete("/{user_id}/calendar", status_code=204)
def disconnect_calendar(user_id: str, db: OrmSession = Depends(get_db)) -> None:
    _get_user_or_404(user_id, db)
    db.query(CalendarConnection).filter_by(user_id=user_id).delete()
    db.commit()


@router.get("/{user_id}/calendar/upcoming-prompt", response_model=UpcomingPromptOut)
def get_upcoming_prompt(
    user_id: str,
    db: OrmSession = Depends(get_db),
    calendar: CalendarProvider = Depends(get_calendar),
) -> UpcomingPromptOut:
    """§8 mechanism #1: 'Standup in 40 minutes — one interjection drill?'

    In production this is what a scheduler would poll and turn into a
    Web Push notification (§4.2's other Phase 2 item) — no scheduler
    exists in this environment (same documented gap as
    `api.lifecycle.purge_expired_media`), so it's exposed as an
    on-demand endpoint a client can poll instead.
    """
    _get_user_or_404(user_id, db)
    connection = db.query(CalendarConnection).filter_by(user_id=user_id).one_or_none()
    if connection is None:
        raise HTTPException(status_code=400, detail="no calendar connected for this user")

    now = datetime.now(timezone.utc)
    events = calendar.list_upcoming_events(now)
    event = next_prompt_worthy_event(events, now)
    if event is None:
        return UpcomingPromptOut(has_prompt=False)

    criterion = guess_drill_criterion(event.title)
    drill_data = DRILL_CATALOG.get(criterion, DEFAULT_DRILL) if criterion else DEFAULT_DRILL
    drill = DrillOut(
        id=drill_data["id"],
        title=drill_data["title"],
        prompt=drill_data["prompt"],
        duration_minutes=drill_data["duration_minutes"],
        targets_criterion=criterion,
    )
    minutes_until = math.ceil((event.start_time - now).total_seconds() / 60)
    return UpcomingPromptOut(
        has_prompt=True, event_title=event.title, minutes_until=minutes_until, drill=drill
    )
