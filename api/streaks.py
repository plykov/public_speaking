"""Non-punitive streak calculation (§4.1 M10, §8 engagement mechanics).

Pure function over a set of calendar dates with at least one completed
attempt — no DB access, no side effects, same "pure core" pattern as
`metrics/`. "Non-punitive... with freeze" (§4.1 M10) is implemented as:
a single missed day inside an otherwise-consecutive run doesn't reset
the streak, but only one such gap is tolerated per run before it breaks.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta


@dataclass(frozen=True)
class StreakResult:
    current_streak: int
    longest_streak: int
    freeze_used_in_current_streak: bool
    last_practice_date: date | None


def compute_streak(practice_dates: set[date], today: date) -> StreakResult:
    """`practice_dates`: every distinct calendar date with >=1 completed
    attempt. `today` is passed in (not read from the clock) so this stays
    pure and deterministic for tests."""
    if not practice_dates:
        return StreakResult(0, 0, False, None)

    last_practice_date = max(practice_dates)

    # More than one full day since the last practice: the streak is dead,
    # even with a freeze — a freeze covers one skipped day, not an
    # open-ended absence.
    current_streak = 0
    freeze_used = False
    if (today - last_practice_date).days <= 1:
        cursor = today if today in practice_dates else last_practice_date
        freeze_available = True
        while True:
            if cursor in practice_dates:
                current_streak += 1
                cursor -= timedelta(days=1)
                continue
            if freeze_available and (cursor - timedelta(days=1)) in practice_dates:
                freeze_available = False
                freeze_used = True
                cursor -= timedelta(days=1)
                continue
            break

    longest_streak = _longest_run(practice_dates)
    longest_streak = max(longest_streak, current_streak)

    return StreakResult(current_streak, longest_streak, freeze_used, last_practice_date)


def _longest_run(practice_dates: set[date]) -> int:
    """Longest historical run, counted in practiced days (matching
    `current_streak`'s units) — each run gets one internal one-day freeze."""
    ordered = sorted(practice_dates)
    best = 0
    run_length = 0
    freeze_available = True
    prev: date | None = None
    for d in ordered:
        if prev is None:
            run_length = 1
        else:
            gap = (d - prev).days
            if gap == 1:
                run_length += 1
            elif gap == 2 and freeze_available:
                freeze_available = False
                run_length += 1
            else:
                run_length = 1
                freeze_available = True
        best = max(best, run_length)
        prev = d
    return best
