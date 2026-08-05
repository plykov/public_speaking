from __future__ import annotations

from datetime import datetime, timezone

from api.deps import get_meeting_recordings
from api.main import app
from api.meeting_import import MeetingRecording, MeetingRecordingProvider


def _user(client) -> str:
    return client.post("/users").json()["id"]


class _BrokenBytesProvider(MeetingRecordingProvider):
    """Returns a valid catalog but non-JSON 'recording' bytes, to exercise
    the transcription-failure path (any real vendor call can fail too)."""

    def list_available_recordings(self, external_user_id):
        return [
            MeetingRecording(
                id="broken", title="Broken", platform="zoom", occurred_at=datetime.now(timezone.utc)
            )
        ]

    def get_recording_metadata(self, recording_id):
        return self.list_available_recordings("")[0]

    def fetch_recording_bytes(self, recording_id):
        return b"not json"


def test_list_meeting_recordings(client) -> None:
    user_id = _user(client)
    resp = client.get(f"/meeting-recordings?user_id={user_id}")
    assert resp.status_code == 200
    recordings = resp.json()
    assert len(recordings) == 2
    ids = {r["id"] for r in recordings}
    assert ids == {"mock-standup-recording", "mock-review-recording"}
    for r in recordings:
        assert r["platform"] in {"zoom", "teams"}
        assert "occurred_at" in r


def test_list_meeting_recordings_unknown_user_404(client) -> None:
    resp = client.get("/meeting-recordings?user_id=does-not-exist")
    assert resp.status_code == 404


def test_import_meeting_recording_requires_consent(client) -> None:
    user_id = _user(client)
    resp = client.post(
        "/meeting-recordings/mock-standup-recording/import",
        json={"user_id": user_id, "consent": False},
    )
    assert resp.status_code == 422


def test_import_meeting_recording_unknown_recording_404(client) -> None:
    user_id = _user(client)
    resp = client.post(
        "/meeting-recordings/does-not-exist/import",
        json={"user_id": user_id, "consent": True},
    )
    assert resp.status_code == 404


def test_import_meeting_recording_unknown_user_404(client) -> None:
    resp = client.post(
        "/meeting-recordings/mock-standup-recording/import",
        json={"user_id": "does-not-exist", "consent": True},
    )
    assert resp.status_code == 404


def test_import_meeting_recording_runs_full_pipeline(client) -> None:
    user_id = _user(client)
    resp = client.post(
        "/meeting-recordings/mock-standup-recording/import",
        json={"user_id": user_id, "consent": True},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["metrics_summary"]
    assert body["feedback_items"]
    assert body["drill"]["id"]
    assert body["transcript_text"].startswith("So")

    session_id = body["session_id"]
    attempts = client.get(f"/users/{user_id}/attempts").json()
    assert any(a["session_id"] == session_id for a in attempts)


def test_list_meeting_imports(client) -> None:
    user_id = _user(client)
    client.post(
        "/meeting-recordings/mock-standup-recording/import",
        json={"user_id": user_id, "consent": True},
    )
    client.post(
        "/meeting-recordings/mock-review-recording/import",
        json={"user_id": user_id, "consent": True},
    )
    resp = client.get(f"/users/{user_id}/meeting-imports")
    assert resp.status_code == 200
    imports = resp.json()
    assert len(imports) == 2
    platforms = {i["platform"] for i in imports}
    assert platforms == {"zoom", "teams"}
    for i in imports:
        assert i["session_id"]
        assert i["external_recording_id"]


def test_list_meeting_imports_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/meeting-imports")
    assert resp.status_code == 404


def test_list_meeting_imports_empty_for_new_user(client) -> None:
    user_id = _user(client)
    resp = client.get(f"/users/{user_id}/meeting-imports")
    assert resp.status_code == 200
    assert resp.json() == []


def test_import_meeting_recording_pipeline_failure_returns_500(client) -> None:
    user_id = _user(client)
    app.dependency_overrides[get_meeting_recordings] = lambda: _BrokenBytesProvider()
    try:
        resp = client.post(
            "/meeting-recordings/broken/import",
            json={"user_id": user_id, "consent": True},
        )
        assert resp.status_code == 500
    finally:
        del app.dependency_overrides[get_meeting_recordings]
