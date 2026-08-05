"""Billing (§4.1 M12, §8.1 commercial model).

No real payment processing — there's no live Stripe key in this
environment, and never should be committed to one anyway. This module
provides the same seam as `api.pipeline.stt` / `api.pipeline.llm`: a
provider abstraction plus a mock implementation, so entitlement gating
and the checkout flow are fully real and testable, with exactly one
piece — `StripeBillingProvider` — left to wire up.

Tiers (§8.1): `free` (no card, capped analyses/month), `pro` (unlimited,
recurring), `event_sprint` (unlimited, 30-day non-renewing), `team`
(month 6+ revenue engine — billed out of band, not through this
checkout flow; provisioned manually for now). A user with no
`Subscription` row, a canceled one, or an expired `event_sprint` window
is on `free` by construction — there's no "downgrade" event to handle.
"""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session as OrmSession

from api.db import AnalysisResult, PracticeSession, Subscription

FREE_MONTHLY_ANALYSIS_LIMIT = 3
EVENT_SPRINT_DURATION_DAYS = 30
UNLIMITED_TIERS = {"pro", "event_sprint", "team"}
VALID_CHECKOUT_TIERS = {"pro", "event_sprint"}  # team is sold out of band, not self-serve


def _comparable(a: datetime, b: datetime) -> tuple[datetime, datetime]:
    """SQLite silently drops tzinfo on round-trip even for `DateTime(timezone=True)`
    columns, so a value read back from the DB can be naive while `now` (passed in
    fresh) is aware. Normalize both to naive UTC before comparing rather than
    letting that raise `TypeError: can't compare offset-naive and offset-aware`."""
    if (a.tzinfo is None) != (b.tzinfo is None):
        a = a.replace(tzinfo=None)
        b = b.replace(tzinfo=None)
    return a, b


def effective_tier(subscription: Subscription | None, now: datetime) -> str:
    """The tier that actually applies right now — never trust `.tier` alone,
    since an event_sprint silently reverts to free once its window closes."""
    if subscription is None or subscription.status != "active":
        return "free"
    if subscription.tier == "event_sprint" and subscription.current_period_end is not None:
        lhs, rhs = _comparable(now, subscription.current_period_end)
        if lhs > rhs:
            return "free"
    return subscription.tier


def has_unlimited_analyses(tier: str) -> bool:
    return tier in UNLIMITED_TIERS


def quota_exceeded(tier: str, analyses_this_month: int) -> bool:
    """True if another analysis should be blocked (402) for this tier."""
    if has_unlimited_analyses(tier):
        return False
    return analyses_this_month >= FREE_MONTHLY_ANALYSIS_LIMIT


@dataclass(frozen=True)
class CheckoutSessionResult:
    id: str
    url: str
    tier: str


class BillingProvider(ABC):
    @abstractmethod
    def create_checkout_session(self, user_id: str, tier: str) -> CheckoutSessionResult: ...


class MockBillingProvider(BillingProvider):
    """Dev/test stand-in. Returns a fake, never-real URL — nothing here
    talks to a network. Confirming payment (`POST
    /billing/checkout/{id}/confirm`) is a stand-in for a verified Stripe
    webhook, which a real `StripeBillingProvider` would authenticate via
    signature verification before the router acts on it."""

    def create_checkout_session(self, user_id: str, tier: str) -> CheckoutSessionResult:
        session_id = str(uuid.uuid4())
        return CheckoutSessionResult(
            id=session_id, url=f"mock://checkout/{session_id}", tier=tier
        )


def get_billing_provider(name: str) -> BillingProvider:
    if name == "mock":
        return MockBillingProvider()
    raise NotImplementedError(
        f"Billing provider {name!r} is not wired up yet — integrate Stripe Checkout + "
        "webhooks behind this same BillingProvider interface. No API keys belong in this repo."
    )


def event_sprint_period_end(now: datetime) -> datetime:
    return now + timedelta(days=EVENT_SPRINT_DURATION_DAYS)


def month_start(now: datetime) -> datetime:
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=timezone.utc)


def count_analyses_this_month(db: OrmSession, user_id: str, now: datetime) -> int:
    return (
        db.query(AnalysisResult)
        .join(PracticeSession, PracticeSession.id == AnalysisResult.session_id)
        .filter(PracticeSession.user_id == user_id)
        .filter(AnalysisResult.created_at >= month_start(now))
        .count()
    )
