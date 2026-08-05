from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _analyzed_session(client, user_id: str | None = None) -> str:
    body = {"scenario": "standup"}
    if user_id:
        body["user_id"] = user_id
    session_id = client.post("/sessions", json=body).json()["id"]
    audio = mock_transcript_bytes(
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.9},
            {"text": "we", "start_ms": 210, "end_ms": 300, "confidence": 0.95},
            {"text": "should", "start_ms": 310, "end_ms": 500, "confidence": 0.95},
            {"text": "ship", "start_ms": 510, "end_ms": 650, "confidence": 0.95},
            {"text": "it.", "start_ms": 660, "end_ms": 800, "confidence": 0.95},
        ]
    )
    client.post(f"/sessions/{session_id}/media?offset=0", content=audio)
    client.post(f"/sessions/{session_id}/analyze")
    return session_id


def test_get_transcript_returns_words_in_order(client) -> None:
    session_id = _analyzed_session(client)
    resp = client.get(f"/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    words = resp.json()
    assert [w["text"] for w in words] == ["maybe", "we", "should", "ship", "it."]
    assert words[0]["seq_index"] == 0
    assert words[0]["start_ms"] == 0


def test_get_transcript_empty_before_analysis(client) -> None:
    session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    resp = client.get(f"/sessions/{session_id}/transcript")
    assert resp.status_code == 200
    assert resp.json() == []


def test_get_transcript_unknown_session_404(client) -> None:
    resp = client.get("/sessions/does-not-exist/transcript")
    assert resp.status_code == 404


def test_update_transcript_rescoring_reflects_correction(client) -> None:
    session_id = _analyzed_session(client)

    # Correct "maybe" (a hedge) away entirely.
    resp = client.put(
        f"/sessions/{session_id}/transcript",
        json={"words": ["we", "we", "should", "ship", "it."]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript_text"] == "we we should ship it."
    hedge_items = [i for i in body["feedback_items"] if i["criterion"] == "point_first_clarity"]
    assert hedge_items == []  # hedging feedback should be gone now


def test_update_transcript_logs_corrections(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Russian", "self_declared_confidence": "comfortable"},
    )
    session_id = _analyzed_session(client, user_id=user_id)

    client.put(
        f"/sessions/{session_id}/transcript",
        json={"words": ["Maybe", "we", "should", "ship", "it."]},
    )

    from api.db import SessionLocal, TranscriptCorrection

    db = SessionLocal()
    try:
        corrections = db.query(TranscriptCorrection).filter_by(session_id=session_id).all()
        assert len(corrections) == 1
        assert corrections[0].original_text == "maybe"
        assert corrections[0].corrected_text == "Maybe"
        assert corrections[0].l1_first_language == "Russian"
    finally:
        db.close()


def test_update_transcript_preserves_timestamps(client) -> None:
    session_id = _analyzed_session(client)
    client.put(
        f"/sessions/{session_id}/transcript",
        json={"words": ["Perhaps", "we", "should", "ship", "it."]},
    )
    words = client.get(f"/sessions/{session_id}/transcript").json()
    assert words[0]["text"] == "Perhaps"
    assert words[0]["start_ms"] == 0
    assert words[0]["end_ms"] == 200


def test_update_transcript_wrong_word_count_400(client) -> None:
    session_id = _analyzed_session(client)
    resp = client.put(f"/sessions/{session_id}/transcript", json={"words": ["only", "two"]})
    assert resp.status_code == 400


def test_update_transcript_no_prior_analysis_400(client) -> None:
    session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    resp = client.put(f"/sessions/{session_id}/transcript", json={"words": ["hi"]})
    assert resp.status_code == 400


def test_update_transcript_unknown_session_404(client) -> None:
    resp = client.put("/sessions/does-not-exist/transcript", json={"words": ["hi"]})
    assert resp.status_code == 404


def test_reanalyze_clears_prior_corrections_via_session_delete(client) -> None:
    session_id = _analyzed_session(client)
    client.put(
        f"/sessions/{session_id}/transcript",
        json={"words": ["Maybe", "we", "should", "ship", "it."]},
    )
    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204

    from api.db import SessionLocal, TranscriptCorrection

    db = SessionLocal()
    try:
        assert db.query(TranscriptCorrection).filter_by(session_id=session_id).count() == 0
    finally:
        db.close()
