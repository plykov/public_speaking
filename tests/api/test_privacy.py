from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.api.conftest import mock_transcript_bytes


def _analyze(client, user_id: str) -> str:
    session_id = client.post("/sessions", json={"scenario": "standup", "user_id": user_id}).json()["id"]
    audio = mock_transcript_bytes(
        [
            {"text": "we", "start_ms": 0, "end_ms": 200, "confidence": 0.95},
            {"text": "should", "start_ms": 210, "end_ms": 400, "confidence": 0.95},
            {"text": "ship", "start_ms": 410, "end_ms": 600, "confidence": 0.95},
            {"text": "it.", "start_ms": 610, "end_ms": 800, "confidence": 0.95},
        ]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    client.post(f"/sessions/{session_id}/analyze")
    return session_id


def test_export_includes_profile_and_sessions(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Dutch", "self_declared_confidence": "comfortable"},
    )
    session_id = _analyze(client, user_id)

    resp = client.get(f"/users/{user_id}/export")
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["l1_profile"]["first_language"] == "Dutch"
    assert len(body["sessions"]) == 1
    assert body["sessions"][0]["session_id"] == session_id
    assert body["sessions"][0]["transcript"][0]["text"] == "we"
    assert body["sessions"][0]["metrics_summary"] is not None


def test_export_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/export")
    assert resp.status_code == 404


def test_export_empty_for_new_user(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/export")
    body = resp.json()
    assert body["sessions"] == []
    assert body["l1_profile"] is None


def test_delete_account_removes_everything(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "French", "self_declared_confidence": "fluent"},
    )
    session_id = _analyze(client, user_id)

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    assert client.get(f"/users/{user_id}").status_code == 404
    assert client.get(f"/users/{user_id}/l1-profile").status_code == 404
    assert client.get(f"/sessions/{session_id}").status_code == 404


def test_delete_unknown_account_404(client) -> None:
    resp = client.delete("/users/does-not-exist")
    assert resp.status_code == 404


def test_purge_expired_media_removes_old_assets_keeps_recent(client) -> None:
    old_session = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    recent_session = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    audio = mock_transcript_bytes([{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}])
    client.post(f"/sessions/{old_session}/media?offset=0", content=audio)
    client.post(f"/sessions/{recent_session}/media?offset=0", content=audio)

    from api.db import SessionLocal, MediaAsset

    db = SessionLocal()
    try:
        old_asset = db.query(MediaAsset).filter_by(session_id=old_session).one()
        old_asset.created_at = datetime.now(timezone.utc) - timedelta(days=31)
        db.commit()
    finally:
        db.close()

    resp = client.post("/admin/purge-expired-media")
    assert resp.status_code == 200
    assert resp.json()["deleted_media_assets"] == 1

    assert client.get(f"/sessions/{old_session}/media/status").json()["bytes_received"] == 0
    assert client.get(f"/sessions/{recent_session}/media/status").json()["bytes_received"] > 0


def test_purge_expired_media_custom_retention(client) -> None:
    session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    audio = mock_transcript_bytes([{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}])
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)

    from api.db import SessionLocal, MediaAsset

    db = SessionLocal()
    try:
        asset = db.query(MediaAsset).filter_by(session_id=session_id).one()
        asset.created_at = datetime.now(timezone.utc) - timedelta(days=2)
        db.commit()
    finally:
        db.close()

    resp = client.post("/admin/purge-expired-media?retention_days=1")
    assert resp.json()["deleted_media_assets"] == 1
