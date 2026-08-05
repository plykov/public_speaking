from __future__ import annotations

from api.analytics import AttemptMetrics, compute_team_analytics


def test_empty_team_no_attempts() -> None:
    result = compute_team_analytics(["u1", "u2"], [])
    assert result.member_count == 2
    assert result.total_attempts == 0
    assert result.avg_wpm is None
    assert len(result.per_member) == 2
    assert all(m.attempt_count == 0 for m in result.per_member)


def test_aggregates_across_members() -> None:
    attempts = [
        AttemptMetrics("u1", 120.0, 2.0, 1.0, 0.8),
        AttemptMetrics("u1", 140.0, 4.0, 3.0, 0.6),
        AttemptMetrics("u2", 100.0, 0.0, 0.0, 1.0),
    ]
    result = compute_team_analytics(["u1", "u2"], attempts)
    assert result.total_attempts == 3
    assert result.avg_wpm == round((120 + 140 + 100) / 3, 2)
    assert result.avg_filler_rate == round((2 + 4 + 0) / 3, 2)


def test_per_member_breakdown() -> None:
    attempts = [
        AttemptMetrics("u1", 120.0, 2.0, 1.0, 0.8),
        AttemptMetrics("u1", 140.0, 4.0, 3.0, 0.6),
        AttemptMetrics("u2", 100.0, 0.0, 0.0, 1.0),
    ]
    result = compute_team_analytics(["u1", "u2"], attempts)
    u1 = next(m for m in result.per_member if m.user_id == "u1")
    u2 = next(m for m in result.per_member if m.user_id == "u2")
    assert u1.attempt_count == 2
    assert u1.avg_wpm == 130.0
    assert u2.attempt_count == 1
    assert u2.avg_wpm == 100.0


def test_member_with_zero_attempts_still_listed() -> None:
    attempts = [AttemptMetrics("u1", 120.0, 2.0, 1.0, 0.8)]
    result = compute_team_analytics(["u1", "u2"], attempts)
    u2 = next(m for m in result.per_member if m.user_id == "u2")
    assert u2.attempt_count == 0
    assert u2.avg_wpm is None


def test_attempt_from_non_roster_user_still_counted_in_team_total() -> None:
    """A member who left the team after practicing shouldn't silently
    vanish from the team total, even though they're not in per_member."""
    attempts = [AttemptMetrics("ex-member", 100.0, 1.0, 1.0, 1.0)]
    result = compute_team_analytics(["u1"], attempts)
    assert result.total_attempts == 1
    assert result.avg_wpm == 100.0


def test_no_raw_media_or_transcript_fields_exist() -> None:
    """Structural guarantee, not just a docstring claim: neither dataclass
    has a field capable of carrying audio, transcript, or feedback text."""
    attempt_fields = set(AttemptMetrics.__dataclass_fields__)
    assert attempt_fields == {
        "user_id",
        "wpm_overall",
        "filler_rate_per_100_words",
        "hedging_rate_per_100_words",
        "point_position_score",
    }
