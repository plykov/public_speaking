"""Web Push (§4.2: "Installable PWA with Web Push").

This is real Web Push — no vendor account or API key needed, since the
browser's own push service (e.g. Chrome's, via FCM) is used
transparently once a client subscribes with our VAPID public key. The
gap this module doesn't close is *scheduling*: nothing in this
environment decides "it's time to remind this user" (that's
`api.lifecycle.purge_expired_media`'s and `Reminder`'s documented gap
too) — this module only sends a push when asked to, e.g. by the
`/push-subscriptions/test` endpoint.

VAPID keys: if `VAPID_PUBLIC_KEY`/`VAPID_PRIVATE_KEY` aren't set, a
fresh keypair is generated at process start. That's fine for exercising
the flow locally, but every subscription made against an ephemeral
keypair is invalidated the next time the process restarts (the
browser's push service ties a subscription to the public key that
created it) — set the env vars to persist subscriptions.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from cryptography.hazmat.primitives import serialization
from py_vapid import Vapid02
from pywebpush import WebPushException, webpush

from api.config import settings

logger = logging.getLogger(__name__)


def generate_vapid_keypair() -> tuple[str, str]:
    """Returns (public_key_b64url, private_key_b64url)."""
    import base64

    vapid = Vapid02()
    vapid.generate_keys()

    public_raw = vapid.public_key.public_bytes(
        encoding=serialization.Encoding.X962,
        format=serialization.PublicFormat.UncompressedPoint,
    )
    private_raw = vapid.private_key.private_numbers().private_value.to_bytes(32, "big")

    public_b64 = base64.urlsafe_b64encode(public_raw).rstrip(b"=").decode()
    private_b64 = base64.urlsafe_b64encode(private_raw).rstrip(b"=").decode()
    return public_b64, private_b64


def _resolve_vapid_keys() -> tuple[str, str]:
    if settings.vapid_public_key and settings.vapid_private_key:
        return settings.vapid_public_key, settings.vapid_private_key
    logger.warning(
        "VAPID_PUBLIC_KEY/VAPID_PRIVATE_KEY not set — generating an ephemeral VAPID "
        "keypair for this process. Push subscriptions will NOT survive a restart. "
        "Set both env vars to persist them."
    )
    return generate_vapid_keypair()


VAPID_PUBLIC_KEY, VAPID_PRIVATE_KEY = _resolve_vapid_keys()


def get_vapid_public_key() -> str:
    return VAPID_PUBLIC_KEY


@dataclass(frozen=True)
class PushSendResult:
    success: bool
    stale: bool  # True if the push service says this subscription is gone (404/410)
    status_code: int | None
    error: str | None = None


def send_web_push(
    subscription_info: dict, payload: dict, ttl: int = 60
) -> PushSendResult:
    """Send one real push message. `subscription_info` is the
    `{"endpoint", "keys": {"p256dh", "auth"}}` shape the browser's
    `PushSubscription.toJSON()` produces."""
    import json

    try:
        response = webpush(
            subscription_info=subscription_info,
            data=json.dumps(payload),
            vapid_private_key=VAPID_PRIVATE_KEY,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=ttl,
        )
        status_code = response.status_code if hasattr(response, "status_code") else 201
        return PushSendResult(success=True, stale=False, status_code=status_code)
    except WebPushException as exc:
        status_code = exc.response.status_code if exc.response is not None else None
        stale = status_code in (404, 410)
        return PushSendResult(
            success=False, stale=stale, status_code=status_code, error=str(exc)
        )
    except Exception as exc:
        # A malformed endpoint/keys (e.g. corrupted browser-side data)
        # raises before any request is even made — pywebpush doesn't wrap
        # that in WebPushException. Treat it as a failed send, not a
        # 500: this is bad subscription data, not a server bug. Not
        # marked stale — the push service never weighed in, so we don't
        # know it's actually gone.
        return PushSendResult(success=False, stale=False, status_code=None, error=str(exc))
