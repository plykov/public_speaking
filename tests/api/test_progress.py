from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _analyze(client, user_id: str | None = None, parent_session_id: str | None = None):
    body = {"scenario": "standup"}
    if user_id:
        body["user_id"] = user_id
    if parent_session_id:
        body["parent_session_id"] = parent_session_id
    session_id = client.post("/sessions", json=body).json()["id"]
    audio = mock_transcript_bytes(
        [
            {"text": "we", "start_ms": 0, "end_ms": 200, "confidence": 0.95},
            {"text": "should", "start_ms": 210, "end_ms": 400, "confidence": 0.95},
            {"text": "ship", "start_ms": 410, "end_ms": 600, "confidence": 0.95},
            {"text": "it.", "start_ms": 610, "end_ms": 800, "confidence": 0.95},
        ]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    return client.post(f"/sessions/{session_id}/analyze").json()["session_id"]


def test_attempts_empty_for_new_user(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/attempts")
    assert resp.status_code == 200
    assert resp.json() == []


def test_attempts_returns_completed_sessions_oldest_first(client) -> None:
    user_id = client.post("/users").json()["id"]
    first = _analyze(client, user_id=user_id)
    second = _analyze(client, user_id=user_id)

    resp = client.get(f"/users/{user_id}/attempts")
    assert resp.status_code == 200
    body = resp.json()
    assert [a["session_id"] for a in body] == [first, second]
    assert body[0]["wpm_overall"] > 0


def test_attempts_excludes_other_users_sessions(client) -> None:
    user_a = client.post("/users").json()["id"]
    user_b = client.post("/users").json()["id"]
    _analyze(client, user_id=user_a)

    resp = client.get(f"/users/{user_b}/attempts")
    assert resp.json() == []


def test_attempts_excludes_anonymous_sessions(client) -> None:
    user_id = client.post("/users").json()["id"]
    _analyze(client, user_id=None)  # no user attached

    resp = client.get(f"/users/{user_id}/attempts")
    assert resp.json() == []


def test_attempts_includes_parent_session_link(client) -> None:
    user_id = client.post("/users").json()["id"]
    baseline = _analyze(client, user_id=user_id)
    retry = _analyze(client, user_id=user_id, parent_session_id=baseline)

    resp = client.get(f"/users/{user_id}/attempts")
    body = resp.json()
    retry_attempt = next(a for a in body if a["session_id"] == retry)
    assert retry_attempt["parent_session_id"] == baseline


def test_attempts_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/attempts")
    assert resp.status_code == 404
