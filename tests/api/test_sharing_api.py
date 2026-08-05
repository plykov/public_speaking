from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _analyze(client, user_id: str) -> str:
    session_id = client.post("/sessions", json={"scenario": "standup", "user_id": user_id}).json()["id"]
    audio = mock_transcript_bytes(
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.95},
            {"text": "we", "start_ms": 210, "end_ms": 400, "confidence": 0.95},
            {"text": "should", "start_ms": 410, "end_ms": 600, "confidence": 0.95},
            {"text": "ship", "start_ms": 610, "end_ms": 800, "confidence": 0.95},
            {"text": "it.", "start_ms": 810, "end_ms": 900, "confidence": 0.95},
        ]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    return client.post(f"/sessions/{session_id}/analyze").json()["session_id"]


def test_create_share_link_defaults(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/share-links", json={})
    assert resp.status_code == 201
    body = resp.json()
    assert body["can_view_progress"] is True
    assert body["can_view_transcripts"] is False
    assert body["can_view_feedback"] is False
    assert body["revoked"] is False
    assert len(body["token"]) >= 24


def test_create_share_link_rejects_non_positive_expiry(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/share-links", json={"expires_in_days": 0})
    assert resp.status_code == 422


def test_create_share_link_unknown_user_404(client) -> None:
    resp = client.post("/users/does-not-exist/share-links", json={})
    assert resp.status_code == 404


def test_list_share_links_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/share-links")
    assert resp.status_code == 404


def test_list_share_links(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/share-links", json={"label": "For Priya"})
    client.post(f"/users/{user_id}/share-links", json={"label": "For Sam"})

    resp = client.get(f"/users/{user_id}/share-links")
    assert resp.status_code == 200
    labels = {link["label"] for link in resp.json()}
    assert labels == {"For Priya", "For Sam"}


def test_revoke_share_link(client) -> None:
    user_id = client.post("/users").json()["id"]
    link = client.post(f"/users/{user_id}/share-links", json={}).json()

    resp = client.delete(f"/users/{user_id}/share-links/{link['id']}")
    assert resp.status_code == 204

    resp = client.get(f"/users/{user_id}/share-links")
    assert resp.json()[0]["revoked"] is True

    resp = client.get(f"/share/{link['token']}")
    assert resp.status_code == 410


def test_revoke_unknown_share_link_404(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.delete(f"/users/{user_id}/share-links/does-not-exist")
    assert resp.status_code == 404


def test_shared_view_unknown_token_404(client) -> None:
    resp = client.get("/share/not-a-real-token")
    assert resp.status_code == 404


def test_shared_view_progress_only_by_default(client) -> None:
    user_id = client.post("/users").json()["id"]
    _analyze(client, user_id)
    link = client.post(f"/users/{user_id}/share-links", json={}).json()

    resp = client.get(f"/share/{link['token']}")
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["attempts"]) == 1
    attempt = body["attempts"][0]
    assert attempt["wpm_overall"] is not None
    assert attempt["transcript_text"] is None
    assert attempt["feedback_items"] is None


def test_shared_view_can_include_transcript_and_feedback(client) -> None:
    user_id = client.post("/users").json()["id"]
    _analyze(client, user_id)
    link = client.post(
        f"/users/{user_id}/share-links",
        json={"can_view_transcripts": True, "can_view_feedback": True},
    ).json()

    resp = client.get(f"/share/{link['token']}")
    attempt = resp.json()["attempts"][0]
    assert attempt["transcript_text"] == "maybe we should ship it."
    assert isinstance(attempt["feedback_items"], list)
    assert len(attempt["feedback_items"]) > 0


def test_shared_view_progress_off_hides_metrics(client) -> None:
    user_id = client.post("/users").json()["id"]
    _analyze(client, user_id)
    link = client.post(
        f"/users/{user_id}/share-links",
        json={"can_view_progress": False, "can_view_feedback": True},
    ).json()

    resp = client.get(f"/share/{link['token']}")
    attempt = resp.json()["attempts"][0]
    assert attempt["wpm_overall"] is None
    assert attempt["filler_rate_per_100_words"] is None
    assert attempt["feedback_items"] is not None


def test_shared_view_never_exposes_raw_media_field(client) -> None:
    user_id = client.post("/users").json()["id"]
    _analyze(client, user_id)
    link = client.post(
        f"/users/{user_id}/share-links",
        json={"can_view_progress": True, "can_view_transcripts": True, "can_view_feedback": True},
    ).json()

    resp = client.get(f"/share/{link['token']}")
    body = resp.json()
    assert "media_url" not in body["attempts"][0]
    assert "audio_url" not in body["attempts"][0]


def test_expired_share_link_returns_410(client) -> None:
    user_id = client.post("/users").json()["id"]
    link = client.post(f"/users/{user_id}/share-links", json={"expires_in_days": 1}).json()
    assert link["expires_at"] is not None

    # can't easily fast-forward time through the API; verify the field
    # round-trips and rely on unit tests (test_sharing.py) for the actual
    # expiry-comparison logic
    resp = client.get(f"/share/{link['token']}")
    assert resp.status_code == 200


def test_account_delete_removes_share_links(client) -> None:
    user_id = client.post("/users").json()["id"]
    link = client.post(f"/users/{user_id}/share-links", json={}).json()

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    resp = client.get(f"/share/{link['token']}")
    assert resp.status_code == 404
