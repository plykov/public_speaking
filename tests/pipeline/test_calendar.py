from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from api.calendar import (
    CalendarEvent,
    MockCalendarProvider,
    get_calendar_provider,
    guess_drill_criterion,
    next_prompt_worthy_event,
)


def test_mock_provider_returns_events_relative_to_now() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = MockCalendarProvider().list_upcoming_events(now)
    assert len(events) >= 1
    for e in events:
        assert e.start_time > now


def test_get_calendar_provider_mock() -> None:
    assert isinstance(get_calendar_provider("mock"), MockCalendarProvider)


def test_get_calendar_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_calendar_provider("google")


def test_guess_drill_criterion_standup() -> None:
    assert guess_drill_criterion("Team Standup") == "point_first_clarity"


def test_guess_drill_criterion_one_on_one() -> None:
    assert guess_drill_criterion("1:1 with Manager") == "structure"


def test_guess_drill_criterion_review() -> None:
    assert guess_drill_criterion("Quarterly Review") == "concision"


def test_guess_drill_criterion_unknown_returns_none() -> None:
    assert guess_drill_criterion("Random Meeting") is None


def _event(minutes_from_now: int, title: str = "Meeting") -> CalendarEvent:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    start = now + timedelta(minutes=minutes_from_now)
    return CalendarEvent(id="e", title=title, start_time=start, end_time=start + timedelta(minutes=30))


def test_next_prompt_worthy_event_finds_imminent_meeting() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(30), _event(200)]
    result = next_prompt_worthy_event(events, now, lookahead_minutes=60)
    assert result is not None
    assert result.title == "Meeting"
    assert result.start_time == now + timedelta(minutes=30)


def test_next_prompt_worthy_event_none_when_nothing_imminent() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(200)]
    assert next_prompt_worthy_event(events, now, lookahead_minutes=60) is None


def test_next_prompt_worthy_event_excludes_past_events() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(-10)]
    assert next_prompt_worthy_event(events, now, lookahead_minutes=60) is None


def test_next_prompt_worthy_event_picks_earliest() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    events = [_event(45, "Later"), _event(15, "Sooner")]
    result = next_prompt_worthy_event(events, now, lookahead_minutes=60)
    assert result.title == "Sooner"


def test_next_prompt_worthy_event_empty_list() -> None:
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    assert next_prompt_worthy_event([], now) is None
