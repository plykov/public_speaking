from __future__ import annotations

from datetime import datetime, timedelta, timezone

from tests.api.conftest import mock_transcript_bytes


def _analyze_at(client, user_id: str, when: datetime) -> str:
    session_id = client.post("/sessions", json={"scenario": "standup", "user_id": user_id}).json()["id"]
    audio = mock_transcript_bytes(
        [{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    client.post(f"/sessions/{session_id}/analyze")

    from api.db import AnalysisResult, SessionLocal

    db = SessionLocal()
    try:
        analysis = db.query(AnalysisResult).filter_by(session_id=session_id).one()
        analysis.created_at = when
        db.commit()
    finally:
        db.close()
    return session_id


def test_upsert_and_get_reminder(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(
        f"/users/{user_id}/reminder", json={"days": ["mon", "wed", "fri"], "time_of_day": "09:00"}
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["days"] == ["mon", "wed", "fri"]
    assert body["time_of_day"] == "09:00"

    resp = client.get(f"/users/{user_id}/reminder")
    assert resp.json()["time_of_day"] == "09:00"


def test_reminder_upsert_overwrites(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.put(f"/users/{user_id}/reminder", json={"days": ["mon"], "time_of_day": "08:00"})
    resp = client.put(f"/users/{user_id}/reminder", json={"days": ["tue", "thu"], "time_of_day": "18:30"})
    assert resp.json()["days"] == ["tue", "thu"]

    resp = client.get(f"/users/{user_id}/reminder")
    assert resp.json()["time_of_day"] == "18:30"


def test_reminder_invalid_day_rejected(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(f"/users/{user_id}/reminder", json={"days": ["funday"], "time_of_day": "09:00"})
    assert resp.status_code == 422


def test_reminder_invalid_time_rejected(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(f"/users/{user_id}/reminder", json={"days": ["mon"], "time_of_day": "9:00am"})
    assert resp.status_code == 422


def test_reminder_empty_days_rejected(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(f"/users/{user_id}/reminder", json={"days": [], "time_of_day": "09:00"})
    assert resp.status_code == 422


def test_reminder_unknown_user_404(client) -> None:
    resp = client.put("/users/does-not-exist/reminder", json={"days": ["mon"], "time_of_day": "09:00"})
    assert resp.status_code == 404


def test_get_reminder_before_set_404(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/reminder")
    assert resp.status_code == 404


def test_streak_zero_for_new_user(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/streak")
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_streak"] == 0
    assert body["last_practice_date"] is None


def test_streak_reflects_consecutive_practice_days(client) -> None:
    user_id = client.post("/users").json()["id"]
    today = datetime.now(timezone.utc)
    _analyze_at(client, user_id, today - timedelta(days=1))
    _analyze_at(client, user_id, today)

    resp = client.get(f"/users/{user_id}/streak")
    body = resp.json()
    assert body["current_streak"] == 2
    assert body["freeze_used_in_current_streak"] is False


def test_streak_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/streak")
    assert resp.status_code == 404
