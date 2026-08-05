from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _session_with_transcript(client, words: list[dict]) -> str:
    session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
    client.post(f"/sessions/{session_id}/media?offset=0", content=mock_transcript_bytes(words))
    return session_id


def test_exemplar_before_analysis_still_works_from_uploaded_transcript(client) -> None:
    # /exemplar reads TranscriptWord rows directly, populated at /analyze time —
    # so it needs an analyzed session, not just an uploaded one.
    session_id = _session_with_transcript(
        client,
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.95},
            {"text": "we", "start_ms": 210, "end_ms": 400, "confidence": 0.95},
            {"text": "should", "start_ms": 410, "end_ms": 600, "confidence": 0.95},
            {"text": "ship", "start_ms": 610, "end_ms": 800, "confidence": 0.95},
            {"text": "it.", "start_ms": 810, "end_ms": 900, "confidence": 0.95},
        ],
    )
    resp = client.get(f"/sessions/{session_id}/exemplar")
    assert resp.status_code == 400


def test_exemplar_returns_rewrite_and_explanation(client) -> None:
    session_id = _session_with_transcript(
        client,
        [
            {"text": "maybe", "start_ms": 0, "end_ms": 200, "confidence": 0.95},
            {"text": "we", "start_ms": 210, "end_ms": 400, "confidence": 0.95},
            {"text": "should", "start_ms": 410, "end_ms": 600, "confidence": 0.95},
            {"text": "ship", "start_ms": 610, "end_ms": 800, "confidence": 0.95},
            {"text": "it.", "start_ms": 810, "end_ms": 900, "confidence": 0.95},
        ],
    )
    client.post(f"/sessions/{session_id}/analyze")

    resp = client.get(f"/sessions/{session_id}/exemplar")
    assert resp.status_code == 200
    body = resp.json()
    assert "maybe" not in body["rewritten_text"].lower()
    assert body["original_text"] != body["rewritten_text"]
    assert len(body["explanation"]) > 0
    assert body["model_version"] == "mock-exemplar-v1"


def test_exemplar_unknown_session_404(client) -> None:
    resp = client.get("/sessions/does-not-exist/exemplar")
    assert resp.status_code == 404
