"""Billing (§4.1 M12, §8.1). See api/billing.py for the entitlement
logic and the no-real-Stripe provider seam this router sits on top of.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.billing import (
    FREE_MONTHLY_ANALYSIS_LIMIT,
    VALID_CHECKOUT_TIERS,
    BillingProvider,
    count_analyses_this_month,
    effective_tier,
    event_sprint_period_end,
    has_unlimited_analyses,
)
from api.db import CheckoutSession, Subscription, User, get_db
from api.deps import get_billing
from api.schemas import CheckoutSessionOut, CreateCheckoutRequest, SubscriptionOut

router = APIRouter(tags=["billing"])


@router.post("/users/{user_id}/checkout", response_model=CheckoutSessionOut, status_code=201)
def create_checkout(
    user_id: str,
    body: CreateCheckoutRequest,
    db: OrmSession = Depends(get_db),
    provider: BillingProvider = Depends(get_billing),
) -> CheckoutSessionOut:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    if body.tier not in VALID_CHECKOUT_TIERS:
        raise HTTPException(
            status_code=400,
            detail=f"tier must be one of {sorted(VALID_CHECKOUT_TIERS)} — team is provisioned manually",
        )

    result = provider.create_checkout_session(user_id, body.tier)
    session = CheckoutSession(id=result.id, user_id=user_id, tier=body.tier, status="pending")
    db.add(session)
    db.commit()

    return CheckoutSessionOut(id=session.id, tier=session.tier, status=session.status, url=result.url)


@router.post("/billing/checkout/{checkout_session_id}/confirm", response_model=CheckoutSessionOut)
def confirm_checkout(checkout_session_id: str, db: OrmSession = Depends(get_db)) -> CheckoutSessionOut:
    """Dev-mode stand-in for a verified Stripe webhook firing after
    payment. A real integration authenticates the webhook signature
    before reaching this logic; there's nothing to verify against a
    mock checkout, so this just trusts the call."""
    session = db.get(CheckoutSession, checkout_session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="checkout session not found")
    if session.status == "completed":
        return CheckoutSessionOut(
            id=session.id, tier=session.tier, status=session.status, url=f"mock://checkout/{session.id}"
        )

    now = datetime.now(timezone.utc)
    period_end = event_sprint_period_end(now) if session.tier == "event_sprint" else None

    subscription = db.query(Subscription).filter_by(user_id=session.user_id).one_or_none()
    if subscription is None:
        subscription = Subscription(
            user_id=session.user_id, tier=session.tier, status="active", current_period_end=period_end
        )
        db.add(subscription)
    else:
        subscription.tier = session.tier
        subscription.status = "active"
        subscription.current_period_end = period_end

    session.status = "completed"
    db.commit()

    return CheckoutSessionOut(
        id=session.id, tier=session.tier, status=session.status, url=f"mock://checkout/{session.id}"
    )


@router.get("/users/{user_id}/subscription", response_model=SubscriptionOut)
def get_subscription(user_id: str, db: OrmSession = Depends(get_db)) -> SubscriptionOut:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    now = datetime.now(timezone.utc)
    subscription = db.query(Subscription).filter_by(user_id=user_id).one_or_none()
    tier = effective_tier(subscription, now)
    analyses_this_month = count_analyses_this_month(db, user_id, now)

    return SubscriptionOut(
        tier=tier,
        status=subscription.status if subscription else "active",
        current_period_end=subscription.current_period_end if subscription else None,
        analyses_this_month=analyses_this_month,
        analyses_limit=None if has_unlimited_analyses(tier) else FREE_MONTHLY_ANALYSIS_LIMIT,
    )
