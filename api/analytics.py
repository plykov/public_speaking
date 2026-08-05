"""Manager aggregate analytics (§4.3 — "manager aggregate analytics with
recording access off by default").

Pure aggregation over already-computed `metrics_summary` dicts — no model
call, no new metric. "Off by default" is taken to its logical conclusion
here: this module has no parameter, flag, or code path that returns raw
audio, transcripts, or feedback text at all. A manager sees numbers only.
Anything richer (an opt-in per-member drill-down) would need the same
kind of explicit, granular consent `api/sharing.py`'s share links already
model — not built here, since nothing in §4.3 asked for it and building
it speculatively would be scope creep.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class AttemptMetrics:
    user_id: str
    wpm_overall: float | None
    filler_rate_per_100_words: float | None
    hedging_rate_per_100_words: float | None
    point_position_score: float | None


@dataclass(frozen=True)
class MemberAnalytics:
    user_id: str
    attempt_count: int
    avg_wpm: float | None
    avg_filler_rate: float | None
    avg_hedging_rate: float | None
    avg_point_position_score: float | None


@dataclass(frozen=True)
class TeamAnalytics:
    member_count: int
    total_attempts: int
    avg_wpm: float | None
    avg_filler_rate: float | None
    avg_hedging_rate: float | None
    avg_point_position_score: float | None
    per_member: tuple[MemberAnalytics, ...]


def _avg(values: list[float]) -> float | None:
    if not values:
        return None
    return round(sum(values) / len(values), 2)


def _member_analytics(user_id: str, attempts: list[AttemptMetrics]) -> MemberAnalytics:
    return MemberAnalytics(
        user_id=user_id,
        attempt_count=len(attempts),
        avg_wpm=_avg([a.wpm_overall for a in attempts if a.wpm_overall is not None]),
        avg_filler_rate=_avg(
            [a.filler_rate_per_100_words for a in attempts if a.filler_rate_per_100_words is not None]
        ),
        avg_hedging_rate=_avg(
            [a.hedging_rate_per_100_words for a in attempts if a.hedging_rate_per_100_words is not None]
        ),
        avg_point_position_score=_avg(
            [a.point_position_score for a in attempts if a.point_position_score is not None]
        ),
    )


def compute_team_analytics(member_user_ids: list[str], attempts: list[AttemptMetrics]) -> TeamAnalytics:
    """Aggregate metrics across a team's members. `member_user_ids` is the
    full roster (so a member with zero attempts still appears with
    `attempt_count=0`), `attempts` is every attempt from any current
    member, in any order."""
    by_member: dict[str, list[AttemptMetrics]] = {uid: [] for uid in member_user_ids}
    for attempt in attempts:
        by_member.setdefault(attempt.user_id, []).append(attempt)

    per_member = tuple(_member_analytics(uid, by_member[uid]) for uid in member_user_ids)

    return TeamAnalytics(
        member_count=len(member_user_ids),
        total_attempts=len(attempts),
        avg_wpm=_avg([a.wpm_overall for a in attempts if a.wpm_overall is not None]),
        avg_filler_rate=_avg(
            [a.filler_rate_per_100_words for a in attempts if a.filler_rate_per_100_words is not None]
        ),
        avg_hedging_rate=_avg(
            [a.hedging_rate_per_100_words for a in attempts if a.hedging_rate_per_100_words is not None]
        ),
        avg_point_position_score=_avg(
            [a.point_position_score for a in attempts if a.point_position_score is not None]
        ),
        per_member=per_member,
    )
