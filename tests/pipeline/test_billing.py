from __future__ import annotations

from datetime import datetime, timedelta, timezone

from api.billing import (
    FREE_MONTHLY_ANALYSIS_LIMIT,
    MockBillingProvider,
    effective_tier,
    get_billing_provider,
    has_unlimited_analyses,
    quota_exceeded,
)
from api.db import Subscription

NOW = datetime(2026, 6, 15, tzinfo=timezone.utc)


def _sub(**overrides) -> Subscription:
    base = dict(tier="pro", status="active", current_period_end=None)
    base.update(overrides)
    return Subscription(**base)


def test_no_subscription_is_free() -> None:
    assert effective_tier(None, NOW) == "free"


def test_canceled_subscription_is_free() -> None:
    assert effective_tier(_sub(status="canceled"), NOW) == "free"


def test_active_pro_is_pro() -> None:
    assert effective_tier(_sub(tier="pro"), NOW) == "pro"


def test_active_team_is_team() -> None:
    assert effective_tier(_sub(tier="team"), NOW) == "team"


def test_event_sprint_within_window_is_event_sprint() -> None:
    sub = _sub(tier="event_sprint", current_period_end=NOW + timedelta(days=5))
    assert effective_tier(sub, NOW) == "event_sprint"


def test_event_sprint_expired_reverts_to_free() -> None:
    sub = _sub(tier="event_sprint", current_period_end=NOW - timedelta(days=1))
    assert effective_tier(sub, NOW) == "free"


def test_event_sprint_handles_naive_datetime_from_sqlite_roundtrip() -> None:
    # SQLite drops tzinfo on round-trip even for DateTime(timezone=True)
    # columns, so current_period_end can come back naive while `now` is
    # aware. Must not raise TypeError, and must still compare correctly.
    naive_expired = datetime(2026, 6, 14)  # no tzinfo, one day before NOW
    sub = _sub(tier="event_sprint", current_period_end=naive_expired)
    assert effective_tier(sub, NOW) == "free"

    naive_future = datetime(2026, 7, 1)  # no tzinfo, after NOW
    sub2 = _sub(tier="event_sprint", current_period_end=naive_future)
    assert effective_tier(sub2, NOW) == "event_sprint"


def test_has_unlimited_analyses() -> None:
    assert has_unlimited_analyses("pro") is True
    assert has_unlimited_analyses("event_sprint") is True
    assert has_unlimited_analyses("team") is True
    assert has_unlimited_analyses("free") is False


def test_quota_exceeded_free_tier() -> None:
    assert quota_exceeded("free", FREE_MONTHLY_ANALYSIS_LIMIT - 1) is False
    assert quota_exceeded("free", FREE_MONTHLY_ANALYSIS_LIMIT) is True
    assert quota_exceeded("free", FREE_MONTHLY_ANALYSIS_LIMIT + 1) is True


def test_quota_never_exceeded_for_unlimited_tiers() -> None:
    assert quota_exceeded("pro", 10_000) is False
    assert quota_exceeded("event_sprint", 10_000) is False
    assert quota_exceeded("team", 10_000) is False


def test_mock_provider_creates_fake_checkout_session() -> None:
    result = MockBillingProvider().create_checkout_session("user-1", "pro")
    assert result.tier == "pro"
    assert result.url.startswith("mock://checkout/")
    assert result.id in result.url


def test_get_billing_provider_mock() -> None:
    assert isinstance(get_billing_provider("mock"), MockBillingProvider)


def test_get_billing_provider_unknown_raises() -> None:
    import pytest

    with pytest.raises(NotImplementedError):
        get_billing_provider("stripe")
