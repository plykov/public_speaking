"""Web Push registration and sending (§4.2). See api/push.py for the
real-but-scheduler-less Web Push implementation this router sits on.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.db import PushSubscription, User, get_db
from api.push import get_vapid_public_key, send_web_push
from api.schemas import (
    PushSubscribeRequest,
    PushTestResult,
    PushUnsubscribeRequest,
    VapidPublicKeyOut,
)

router = APIRouter(tags=["push"])


@router.get("/push/vapid-public-key", response_model=VapidPublicKeyOut)
def vapid_public_key() -> VapidPublicKeyOut:
    return VapidPublicKeyOut(public_key=get_vapid_public_key())


@router.post("/users/{user_id}/push-subscriptions", status_code=201)
def subscribe(
    user_id: str, body: PushSubscribeRequest, db: OrmSession = Depends(get_db)
) -> dict[str, str]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    existing = db.query(PushSubscription).filter_by(endpoint=body.endpoint).one_or_none()
    if existing is None:
        db.add(
            PushSubscription(
                user_id=user_id,
                endpoint=body.endpoint,
                p256dh=body.keys.p256dh,
                auth=body.keys.auth,
            )
        )
    else:
        existing.user_id = user_id
        existing.p256dh = body.keys.p256dh
        existing.auth = body.keys.auth
    db.commit()
    return {"status": "subscribed"}


@router.post("/users/{user_id}/push-subscriptions/unsubscribe", status_code=204)
def unsubscribe(
    user_id: str, body: PushUnsubscribeRequest, db: OrmSession = Depends(get_db)
) -> None:
    db.query(PushSubscription).filter_by(user_id=user_id, endpoint=body.endpoint).delete()
    db.commit()


@router.post("/users/{user_id}/push-subscriptions/test", response_model=PushTestResult)
def send_test_push(user_id: str, db: OrmSession = Depends(get_db)) -> PushTestResult:
    """Sends one real push notification to every subscription this user
    has registered. Stale subscriptions (the push service returns 404/410)
    are removed — that's the browser telling us this subscription is dead,
    not a transient failure."""
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    subscriptions = db.query(PushSubscription).filter_by(user_id=user_id).all()
    if not subscriptions:
        raise HTTPException(status_code=400, detail="no push subscriptions registered for this user")

    sent = 0
    failed = 0
    removed_stale = 0
    for sub in subscriptions:
        result = send_web_push(
            {"endpoint": sub.endpoint, "keys": {"p256dh": sub.p256dh, "auth": sub.auth}},
            {
                "title": "Cadence",
                "body": "This is a test notification — push delivery is working.",
            },
        )
        if result.success:
            sent += 1
        else:
            failed += 1
            if result.stale:
                db.delete(sub)
                removed_stale += 1
    db.commit()

    return PushTestResult(sent=sent, failed=failed, removed_stale=removed_stale)
