from __future__ import annotations

from api import push as push_module


def test_vapid_public_key_endpoint(client) -> None:
    resp = client.get("/push/vapid-public-key")
    assert resp.status_code == 200
    assert resp.json()["public_key"] == push_module.get_vapid_public_key()


def test_subscribe_creates_subscription(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(
        f"/users/{user_id}/push-subscriptions",
        json={
            "endpoint": "https://push.example.com/abc",
            "keys": {"p256dh": "p256dh-value", "auth": "auth-value"},
        },
    )
    assert resp.status_code == 201
    assert resp.json()["status"] == "subscribed"


def test_subscribe_unknown_user_404(client) -> None:
    resp = client.post(
        "/users/does-not-exist/push-subscriptions",
        json={"endpoint": "https://push.example.com/x", "keys": {"p256dh": "a", "auth": "b"}},
    )
    assert resp.status_code == 404


def test_resubscribing_same_endpoint_updates_keys(client) -> None:
    user_id = client.post("/users").json()["id"]
    endpoint = "https://push.example.com/same-endpoint"
    client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "old", "auth": "old"}},
    )
    resp = client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "new", "auth": "new"}},
    )
    assert resp.status_code == 201

    from api.db import PushSubscription, SessionLocal

    db = SessionLocal()
    try:
        rows = db.query(PushSubscription).filter_by(endpoint=endpoint).all()
        assert len(rows) == 1
        assert rows[0].p256dh == "new"
    finally:
        db.close()


def test_unsubscribe_removes_subscription(client) -> None:
    user_id = client.post("/users").json()["id"]
    endpoint = "https://push.example.com/to-remove"
    client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "a", "auth": "b"}},
    )
    resp = client.post(f"/users/{user_id}/push-subscriptions/unsubscribe", json={"endpoint": endpoint})
    assert resp.status_code == 204

    from api.db import PushSubscription, SessionLocal

    db = SessionLocal()
    try:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 0
    finally:
        db.close()


def test_test_push_with_no_subscriptions_400(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/push-subscriptions/test")
    assert resp.status_code == 400


def test_test_push_unknown_user_404(client) -> None:
    resp = client.post("/users/does-not-exist/push-subscriptions/test")
    assert resp.status_code == 404


def test_test_push_success_counts_sent(client, monkeypatch) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": "https://push.example.com/one", "keys": {"p256dh": "a", "auth": "b"}},
    )

    from api.push import PushSendResult

    monkeypatch.setattr(
        "api.routers.push.send_web_push",
        lambda subscription_info, payload: PushSendResult(success=True, stale=False, status_code=201),
    )

    resp = client.post(f"/users/{user_id}/push-subscriptions/test")
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] == 1
    assert body["failed"] == 0
    assert body["removed_stale"] == 0


def test_test_push_stale_subscription_is_removed(client, monkeypatch) -> None:
    user_id = client.post("/users").json()["id"]
    endpoint = "https://push.example.com/stale"
    client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "a", "auth": "b"}},
    )

    from api.push import PushSendResult

    monkeypatch.setattr(
        "api.routers.push.send_web_push",
        lambda subscription_info, payload: PushSendResult(
            success=False, stale=True, status_code=410, error="gone"
        ),
    )

    resp = client.post(f"/users/{user_id}/push-subscriptions/test")
    body = resp.json()
    assert body["sent"] == 0
    assert body["failed"] == 1
    assert body["removed_stale"] == 1

    from api.db import PushSubscription, SessionLocal

    db = SessionLocal()
    try:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 0
    finally:
        db.close()


def test_account_delete_removes_push_subscriptions(client) -> None:
    user_id = client.post("/users").json()["id"]
    endpoint = "https://push.example.com/deleted-with-account"
    client.post(
        f"/users/{user_id}/push-subscriptions",
        json={"endpoint": endpoint, "keys": {"p256dh": "a", "auth": "b"}},
    )

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    from api.db import PushSubscription, SessionLocal

    db = SessionLocal()
    try:
        assert db.query(PushSubscription).filter_by(endpoint=endpoint).count() == 0
    finally:
        db.close()
