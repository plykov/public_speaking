from __future__ import annotations

import base64

import pytest
from pywebpush import WebPushException

from api import push


def test_generate_vapid_keypair_produces_valid_base64url() -> None:
    public_b64, private_b64 = push.generate_vapid_keypair()

    # Must decode cleanly as URL-safe base64 (with padding restored).
    public_raw = base64.urlsafe_b64decode(public_b64 + "=" * (-len(public_b64) % 4))
    private_raw = base64.urlsafe_b64decode(private_b64 + "=" * (-len(private_b64) % 4))

    assert len(public_raw) == 65  # uncompressed EC point: 0x04 + 32 + 32 bytes
    assert public_raw[0] == 0x04
    assert len(private_raw) == 32


def test_generate_vapid_keypair_is_not_deterministic() -> None:
    first = push.generate_vapid_keypair()
    second = push.generate_vapid_keypair()
    assert first != second


def test_get_vapid_public_key_returns_module_key() -> None:
    assert push.get_vapid_public_key() == push.VAPID_PUBLIC_KEY
    assert isinstance(push.get_vapid_public_key(), str)
    assert len(push.get_vapid_public_key()) > 0


def test_send_web_push_success(monkeypatch) -> None:
    class FakeResponse:
        status_code = 201

    def fake_webpush(**kwargs):
        assert kwargs["subscription_info"]["endpoint"] == "https://example.com/push/abc"
        return FakeResponse()

    monkeypatch.setattr(push, "webpush", fake_webpush)

    result = push.send_web_push(
        {"endpoint": "https://example.com/push/abc", "keys": {"p256dh": "x", "auth": "y"}},
        {"title": "hi"},
    )
    assert result.success is True
    assert result.stale is False
    assert result.status_code == 201


def test_send_web_push_stale_subscription_marks_stale(monkeypatch) -> None:
    class FakeResponse:
        status_code = 410

    def fake_webpush(**kwargs):
        raise WebPushException("gone", response=FakeResponse())

    monkeypatch.setattr(push, "webpush", fake_webpush)

    result = push.send_web_push(
        {"endpoint": "https://example.com/push/abc", "keys": {"p256dh": "x", "auth": "y"}},
        {"title": "hi"},
    )
    assert result.success is False
    assert result.stale is True
    assert result.status_code == 410


def test_send_web_push_non_stale_failure_not_marked_stale(monkeypatch) -> None:
    class FakeResponse:
        status_code = 500

    def fake_webpush(**kwargs):
        raise WebPushException("server error", response=FakeResponse())

    monkeypatch.setattr(push, "webpush", fake_webpush)

    result = push.send_web_push(
        {"endpoint": "https://example.com/push/abc", "keys": {"p256dh": "x", "auth": "y"}},
        {"title": "hi"},
    )
    assert result.success is False
    assert result.stale is False
    assert result.status_code == 500


def test_send_web_push_malformed_key_does_not_raise() -> None:
    # Regression: a p256dh value that's *almost* valid base64 (wrong
    # padding, e.g. corrupted browser-side data) used to raise
    # binascii.Error deep inside pywebpush's WebPusher.__init__, before
    # any request was attempted and before our WebPushException handler
    # could catch it — a real subscription's bad data should never 500
    # the endpoint that sends to it.
    result = push.send_web_push(
        {
            "endpoint": "https://fcm.googleapis.com/fcm/send/fake",
            "keys": {
                "p256dh": "BNbT_kLMk4KJ6qWmZ8x2xVzJZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzZzA",
                "auth": "fakeauthkey12",
            },
        },
        {"title": "hi"},
    )
    assert result.success is False
    assert result.stale is False
    assert result.status_code is None
    assert result.error is not None


def test_send_web_push_exception_with_no_response(monkeypatch) -> None:
    def fake_webpush(**kwargs):
        raise WebPushException("network error", response=None)

    monkeypatch.setattr(push, "webpush", fake_webpush)

    result = push.send_web_push(
        {"endpoint": "https://example.com/push/abc", "keys": {"p256dh": "x", "auth": "y"}},
        {"title": "hi"},
    )
    assert result.success is False
    assert result.stale is False
    assert result.status_code is None
