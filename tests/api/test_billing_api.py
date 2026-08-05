from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.api.conftest import mock_transcript_bytes


def _analyze(client, user_id: str) -> dict:
    session_id = client.post("/sessions", json={"scenario": "standup", "user_id": user_id}).json()["id"]
    audio = mock_transcript_bytes(
        [{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    return client.post(f"/sessions/{session_id}/analyze")


def test_new_user_has_free_tier_and_zero_analyses(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/subscription")
    assert resp.status_code == 200
    body = resp.json()
    assert body["tier"] == "free"
    assert body["analyses_this_month"] == 0
    assert body["analyses_limit"] == 3


def test_subscription_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/subscription")
    assert resp.status_code == 404


def test_free_tier_blocked_after_three_analyses(client) -> None:
    user_id = client.post("/users").json()["id"]
    for _ in range(3):
        resp = _analyze(client, user_id)
        assert resp.status_code == 200

    resp = _analyze(client, user_id)
    assert resp.status_code == 402

    sub = client.get(f"/users/{user_id}/subscription").json()
    assert sub["analyses_this_month"] == 3


def test_reanalyzing_same_session_does_not_consume_quota(client) -> None:
    user_id = client.post("/users").json()["id"]
    session_id = client.post("/sessions", json={"scenario": "standup", "user_id": user_id}).json()["id"]
    audio = mock_transcript_bytes([{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}])
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)

    for _ in range(3):
        resp = client.post(f"/sessions/{session_id}/analyze")
        assert resp.status_code == 200

    sub = client.get(f"/users/{user_id}/subscription").json()
    assert sub["analyses_this_month"] == 1


def test_anonymous_sessions_are_never_gated(client) -> None:
    for _ in range(5):
        session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
        audio = mock_transcript_bytes([{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}])
        client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
        resp = client.post(f"/sessions/{session_id}/analyze")
        assert resp.status_code == 200


def test_checkout_and_confirm_upgrades_to_pro(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/checkout", json={"tier": "pro"})
    assert resp.status_code == 201
    checkout = resp.json()
    assert checkout["status"] == "pending"
    assert checkout["url"].startswith("mock://checkout/")

    resp = client.post(f"/billing/checkout/{checkout['id']}/confirm")
    assert resp.status_code == 200
    assert resp.json()["status"] == "completed"

    sub = client.get(f"/users/{user_id}/subscription").json()
    assert sub["tier"] == "pro"
    assert sub["analyses_limit"] is None


def test_pro_tier_has_no_quota(client) -> None:
    user_id = client.post("/users").json()["id"]
    checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "pro"}).json()
    client.post(f"/billing/checkout/{checkout['id']}/confirm")

    for _ in range(5):
        resp = _analyze(client, user_id)
        assert resp.status_code == 200


def test_event_sprint_expires_back_to_free(client) -> None:
    user_id = client.post("/users").json()["id"]
    checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "event_sprint"}).json()
    client.post(f"/billing/checkout/{checkout['id']}/confirm")

    from api.db import SessionLocal, Subscription

    db = SessionLocal()
    try:
        sub = db.query(Subscription).filter_by(user_id=user_id).one()
        sub.current_period_end = datetime.now(timezone.utc) - timedelta(days=1)
        db.commit()
    finally:
        db.close()

    resp = client.get(f"/users/{user_id}/subscription")
    assert resp.json()["tier"] == "free"


def test_second_checkout_upgrades_existing_subscription(client) -> None:
    user_id = client.post("/users").json()["id"]
    first_checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "event_sprint"}).json()
    client.post(f"/billing/checkout/{first_checkout['id']}/confirm")
    assert client.get(f"/users/{user_id}/subscription").json()["tier"] == "event_sprint"

    second_checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "pro"}).json()
    client.post(f"/billing/checkout/{second_checkout['id']}/confirm")

    sub = client.get(f"/users/{user_id}/subscription").json()
    assert sub["tier"] == "pro"
    assert sub["current_period_end"] is None  # pro has no expiry, unlike event_sprint


def test_checkout_invalid_tier_rejected(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/checkout", json={"tier": "team"})
    assert resp.status_code == 400


def test_checkout_unknown_user_404(client) -> None:
    resp = client.post("/users/does-not-exist/checkout", json={"tier": "pro"})
    assert resp.status_code == 404


def test_confirm_unknown_checkout_404(client) -> None:
    resp = client.post("/billing/checkout/does-not-exist/confirm")
    assert resp.status_code == 404


def test_confirm_is_idempotent(client) -> None:
    user_id = client.post("/users").json()["id"]
    checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "pro"}).json()
    first = client.post(f"/billing/checkout/{checkout['id']}/confirm")
    second = client.post(f"/billing/checkout/{checkout['id']}/confirm")
    assert first.status_code == second.status_code == 200
    assert first.json() == second.json()


def test_account_delete_removes_subscription_and_checkout(client) -> None:
    user_id = client.post("/users").json()["id"]
    checkout = client.post(f"/users/{user_id}/checkout", json={"tier": "pro"}).json()
    client.post(f"/billing/checkout/{checkout['id']}/confirm")

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    assert client.get(f"/users/{user_id}").status_code == 404
