"""Coach/manager share links (§4.2 — "Private share link for a coach or
manager, granular permissions").

Real, no vendor dependency: an opaque random token (`secrets.token_urlsafe`)
is the entire access control — no login for the viewer, consistent with
"private link" rather than "coach account." What's shared is controlled by
three independent boolean flags the owner sets when creating the link
(progress trend, transcripts, feedback text). Raw audio is never included
via a share link at any permission setting — §6.5's no-training/privacy
stance extends here by design, not merely by omission of a feature nobody
asked for.
"""

from __future__ import annotations

import secrets
from datetime import datetime


def generate_token() -> str:
    return secrets.token_urlsafe(24)


def _comparable(a: datetime, b: datetime) -> tuple[datetime, datetime]:
    """See api.billing._comparable — SQLite silently drops tzinfo on
    round-trip even for `DateTime(timezone=True)` columns."""
    if (a.tzinfo is None) != (b.tzinfo is None):
        a = a.replace(tzinfo=None)
        b = b.replace(tzinfo=None)
    return a, b


def is_link_active(revoked_at: datetime | None, expires_at: datetime | None, now: datetime) -> bool:
    if revoked_at is not None:
        return False
    if expires_at is not None:
        lhs, rhs = _comparable(now, expires_at)
        if lhs > rhs:
            return False
    return True
