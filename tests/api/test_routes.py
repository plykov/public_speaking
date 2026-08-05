from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _create_session(client, scenario: str = "standup") -> str:
    resp = client.post("/sessions", json={"scenario": scenario})
    assert resp.status_code == 201
    return resp.json()["id"]


def test_full_session_lifecycle(client) -> None:
    session_id = _create_session(client)

    audio = mock_transcript_bytes(
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.9},
            {"text": "we", "start_ms": 210, "end_ms": 300, "confidence": 0.95},
            {"text": "should", "start_ms": 310, "end_ms": 500, "confidence": 0.95},
            {"text": "ship", "start_ms": 510, "end_ms": 650, "confidence": 0.95},
            {"text": "it.", "start_ms": 660, "end_ms": 800, "confidence": 0.95},
        ]
    )

    # Upload in two chunks to exercise the resumable path.
    half = len(audio) // 2
    resp = client.post(f"/sessions/{session_id}/media?offset=0", content=audio[:half])
    assert resp.status_code == 200
    assert resp.json()["bytes_received"] == half

    resp = client.post(f"/sessions/{session_id}/media?offset={half}", content=audio[half:])
    assert resp.status_code == 200
    assert resp.json()["bytes_received"] == len(audio)

    resp = client.get(f"/sessions/{session_id}/media/status")
    assert resp.json()["bytes_received"] == len(audio)

    resp = client.post(f"/sessions/{session_id}/analyze")
    assert resp.status_code == 200
    body = resp.json()
    assert body["transcript_text"] == "maybe we should ship it."
    assert body["rubric_version"]
    assert body["model_version"]
    assert len(body["feedback_items"]) >= 1
    assert body["drill"]["id"]

    resp = client.get(f"/sessions/{session_id}")
    assert resp.json()["status"] == "complete"

    resp = client.get(f"/sessions/{session_id}/result")
    assert resp.status_code == 200
    assert resp.json()["transcript_text"] == "maybe we should ship it."

    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204

    resp = client.get(f"/sessions/{session_id}")
    assert resp.status_code == 404


def test_analyze_without_upload_returns_400(client) -> None:
    session_id = _create_session(client)
    resp = client.post(f"/sessions/{session_id}/analyze")
    assert resp.status_code == 400


def test_result_before_analysis_returns_404(client) -> None:
    session_id = _create_session(client)
    resp = client.get(f"/sessions/{session_id}/result")
    assert resp.status_code == 404


def test_unknown_session_returns_404(client) -> None:
    resp = client.get("/sessions/does-not-exist")
    assert resp.status_code == 404


def test_chunk_offset_gap_returns_409(client) -> None:
    session_id = _create_session(client)
    resp = client.post(f"/sessions/{session_id}/media?offset=1000", content=b"data")
    assert resp.status_code == 409


def test_malformed_audio_analyze_returns_500_and_marks_session_failed(client) -> None:
    session_id = _create_session(client)
    resp = client.post(f"/sessions/{session_id}/media?offset=0", content=b"not-json-audio")
    assert resp.status_code == 200

    resp = client.post(f"/sessions/{session_id}/analyze")
    assert resp.status_code == 500

    resp = client.get(f"/sessions/{session_id}")
    assert resp.json()["status"] == "failed"
