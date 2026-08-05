from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _analyzed_session(client):
    session_id = client.post("/sessions", json={"scenario": "standup"}).json()["id"]
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
    result = client.post(f"/sessions/{session_id}/analyze").json()
    return result


def test_feedback_items_start_unrated(client) -> None:
    result = _analyzed_session(client)
    assert len(result["feedback_items"]) >= 1
    for item in result["feedback_items"]:
        assert item["user_rating"] is None
        assert item["id"]


def test_rate_feedback_item_useful(client) -> None:
    result = _analyzed_session(client)
    item_id = result["feedback_items"][0]["id"]

    resp = client.put(f"/feedback-items/{item_id}/rating", json={"useful": True})
    assert resp.status_code == 200
    assert resp.json()["user_rating"] is True

    # Rating persists when re-fetching the session result.
    session_id = result["session_id"]
    refetched = client.get(f"/sessions/{session_id}/result").json()
    assert refetched["feedback_items"][0]["user_rating"] is True


def test_rate_feedback_item_not_useful(client) -> None:
    result = _analyzed_session(client)
    item_id = result["feedback_items"][0]["id"]

    resp = client.put(f"/feedback-items/{item_id}/rating", json={"useful": False})
    assert resp.json()["user_rating"] is False


def test_rate_unknown_feedback_item_404(client) -> None:
    resp = client.put("/feedback-items/does-not-exist/rating", json={"useful": True})
    assert resp.status_code == 404


def test_reanalyze_replaces_prior_feedback_items(client) -> None:
    result = _analyzed_session(client)
    session_id = result["session_id"]
    old_item_ids = {item["id"] for item in result["feedback_items"]}

    second = client.post(f"/sessions/{session_id}/analyze").json()
    new_item_ids = {item["id"] for item in second["feedback_items"]}

    assert old_item_ids.isdisjoint(new_item_ids)
