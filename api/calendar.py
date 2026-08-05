"""Calendar integration driving pre-meeting prompts (§4.2 — "the core
retention mechanism," §8 mechanism #1: "Standup in 40 minutes — one
interjection drill?").

OAuth with Google Calendar or Microsoft Graph needs a real app
registration (client id/secret, redirect URI, consent screen) this
environment doesn't have — the same category of gap as Stripe, not
something that can be worked around client-side the way Web Push or
SpeechSynthesis were. `CalendarProvider` is the seam a real integration
implements; `MockCalendarProvider` simulates a successful connection and
returns a small, deterministic (relative to `now`, not wall-clock-fixed)
set of synthetic upcoming events, so the genuinely real part — matching
an imminent event to a practice prompt — can be built and tested end to
end without waiting on OAuth.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta


@dataclass(frozen=True)
class CalendarEvent:
    id: str
    title: str
    start_time: datetime
    end_time: datetime


class CalendarProvider(ABC):
    @abstractmethod
    def list_upcoming_events(self, now: datetime) -> list[CalendarEvent]: ...


class MockCalendarProvider(CalendarProvider):
    def list_upcoming_events(self, now: datetime) -> list[CalendarEvent]:
        return [
            CalendarEvent(
                id="mock-standup",
                title="Team Standup",
                start_time=now + timedelta(minutes=30),
                end_time=now + timedelta(minutes=45),
            ),
            CalendarEvent(
                id="mock-1-1",
                title="1:1 with Manager",
                start_time=now + timedelta(hours=3),
                end_time=now + timedelta(hours=3, minutes=30),
            ),
        ]


def get_calendar_provider(name: str) -> CalendarProvider:
    if name == "mock":
        return MockCalendarProvider()
    raise NotImplementedError(
        f"Calendar provider {name!r} is not wired up yet — integrate Google Calendar or "
        "Microsoft Graph OAuth behind this same CalendarProvider interface."
    )


_MEETING_TYPE_DRILL_CRITERION: dict[str, str] = {
    "standup": "point_first_clarity",
    "1:1": "structure",
    "review": "concision",
}


def guess_drill_criterion(event_title: str) -> str | None:
    """A simple keyword match against the event title. Real "match a
    meeting to a skill" logic could be much richer (scenario history,
    past feedback for similar meetings); this demonstrates the mechanism
    without overclaiming sophistication the mock doesn't have."""
    lowered = event_title.lower()
    for keyword, criterion in _MEETING_TYPE_DRILL_CRITERION.items():
        if keyword in lowered:
            return criterion
    return None


def next_prompt_worthy_event(
    events: list[CalendarEvent], now: datetime, lookahead_minutes: int = 60
) -> CalendarEvent | None:
    """The earliest upcoming event starting within `lookahead_minutes`, or
    None if nothing qualifies. An event already in progress or past
    doesn't count — this prompt is "before," not "during" (§4.2 never
    proposes live-meeting capture, only a pre-meeting nudge)."""
    window_end = now + timedelta(minutes=lookahead_minutes)
    upcoming = [e for e in events if now <= e.start_time <= window_end]
    if not upcoming:
        return None
    return min(upcoming, key=lambda e: e.start_time)
