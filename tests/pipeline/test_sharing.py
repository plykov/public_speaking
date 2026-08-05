from __future__ import annotations

from datetime import datetime, timedelta, timezone

from api.sharing import generate_token, is_link_active


def test_generate_token_is_url_safe_and_long_enough() -> None:
    token = generate_token()
    assert len(token) >= 24
    assert all(c.isalnum() or c in "-_" for c in token)


def test_generate_token_is_not_deterministic() -> None:
    assert generate_token() != generate_token()


def test_is_link_active_with_no_expiry_or_revocation() -> None:
    assert is_link_active(None, None, datetime.now(timezone.utc)) is True


def test_is_link_active_false_when_revoked() -> None:
    now = datetime.now(timezone.utc)
    assert is_link_active(now, None, now) is False


def test_is_link_active_false_when_expired() -> None:
    now = datetime.now(timezone.utc)
    expired = now - timedelta(days=1)
    assert is_link_active(None, expired, now) is False


def test_is_link_active_true_when_not_yet_expired() -> None:
    now = datetime.now(timezone.utc)
    future = now + timedelta(days=1)
    assert is_link_active(None, future, now) is True


def test_is_link_active_handles_naive_datetime_from_sqlite_roundtrip() -> None:
    """SQLite drops tzinfo on round-trip — a real symptom hit earlier in
    api.billing._comparable; this is the same fix applied here."""
    now = datetime.now(timezone.utc)
    naive_future_expiry = (now + timedelta(days=1)).replace(tzinfo=None)
    assert is_link_active(None, naive_future_expiry, now) is True

    naive_past_expiry = (now - timedelta(days=1)).replace(tzinfo=None)
    assert is_link_active(None, naive_past_expiry, now) is False
