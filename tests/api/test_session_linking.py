from __future__ import annotations


def test_session_with_user_id(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post("/sessions", json={"scenario": "standup", "user_id": user_id})
    assert resp.status_code == 201
    assert resp.json()["user_id"] == user_id


def test_session_with_unknown_user_id_404(client) -> None:
    resp = client.post("/sessions", json={"scenario": "standup", "user_id": "nope"})
    assert resp.status_code == 404


def test_session_without_user_id_is_anonymous(client) -> None:
    resp = client.post("/sessions", json={"scenario": "standup"})
    assert resp.status_code == 201
    assert resp.json()["user_id"] is None


def test_retry_session_links_to_parent(client) -> None:
    baseline = client.post("/sessions", json={"scenario": "standup"}).json()
    retry = client.post(
        "/sessions", json={"scenario": "standup", "parent_session_id": baseline["id"]}
    )
    assert retry.status_code == 201
    assert retry.json()["parent_session_id"] == baseline["id"]


def test_retry_session_unknown_parent_404(client) -> None:
    resp = client.post("/sessions", json={"scenario": "standup", "parent_session_id": "nope"})
    assert resp.status_code == 404
