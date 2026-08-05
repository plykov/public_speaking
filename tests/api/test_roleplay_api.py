from __future__ import annotations

from tests.api.conftest import mock_transcript_bytes


def _create_session(client, persona_id: str = "skeptical_stakeholder", user_id: str | None = None) -> dict:
    body = {"persona_id": persona_id}
    if user_id:
        body["user_id"] = user_id
    return client.post("/roleplay-sessions", json=body).json()


def test_list_personas(client) -> None:
    resp = client.get("/roleplay-personas")
    assert resp.status_code == 200
    body = resp.json()
    assert any(p["id"] == "skeptical_stakeholder" for p in body)


def test_create_roleplay_session_returns_opening_line(client) -> None:
    session = _create_session(client)
    assert session["status"] == "active"
    assert len(session["turns"]) == 1
    assert session["turns"][0]["speaker"] == "persona"
    assert session["turns"][0]["text"]


def test_create_roleplay_session_unknown_persona_404(client) -> None:
    resp = client.post("/roleplay-sessions", json={"persona_id": "does-not-exist"})
    assert resp.status_code == 404


def test_create_roleplay_session_unknown_user_404(client) -> None:
    resp = client.post(
        "/roleplay-sessions", json={"persona_id": "skeptical_stakeholder", "user_id": "no-such-user"}
    )
    assert resp.status_code == 404


def test_get_roleplay_session(client) -> None:
    session = _create_session(client)
    resp = client.get(f"/roleplay-sessions/{session['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == session["id"]


def test_get_roleplay_session_unknown_404(client) -> None:
    resp = client.get("/roleplay-sessions/does-not-exist")
    assert resp.status_code == 404


def test_submit_turn_transcribes_and_appends_reply(client) -> None:
    session = _create_session(client)
    audio = mock_transcript_bytes(
        [
            {"text": "we", "start_ms": 0, "end_ms": 100, "confidence": 0.95},
            {"text": "should", "start_ms": 110, "end_ms": 200, "confidence": 0.95},
            {"text": "ship", "start_ms": 210, "end_ms": 300, "confidence": 0.95},
            {"text": "it.", "start_ms": 310, "end_ms": 400, "confidence": 0.95},
        ]
    )
    resp = client.post(f"/roleplay-sessions/{session['id']}/turns", content=audio)
    assert resp.status_code == 200
    body = resp.json()
    assert body["session_status"] == "active"
    assert len(body["new_turns"]) == 2
    assert body["new_turns"][0]["speaker"] == "user"
    assert body["new_turns"][0]["text"] == "we should ship it."
    assert body["new_turns"][1]["speaker"] == "persona"


def test_submit_turn_reacts_to_hedging(client) -> None:
    session = _create_session(client)
    audio = mock_transcript_bytes(
        [{"text": "maybe", "start_ms": 0, "end_ms": 100, "confidence": 0.95}]
    )
    resp = client.post(f"/roleplay-sessions/{session['id']}/turns", content=audio)
    reply_text = resp.json()["new_turns"][1]["text"].lower()
    assert "maybe" in reply_text


def test_conversation_closes_after_max_turns(client) -> None:
    session = _create_session(client)
    audio = mock_transcript_bytes(
        [{"text": "yes", "start_ms": 0, "end_ms": 100, "confidence": 0.95}]
    )
    session_id = session["id"]
    for _ in range(3):
        resp = client.post(f"/roleplay-sessions/{session_id}/turns", content=audio)
    assert resp.json()["session_status"] == "completed"


def test_submit_turn_after_completion_rejected(client) -> None:
    session = _create_session(client)
    audio = mock_transcript_bytes(
        [{"text": "yes", "start_ms": 0, "end_ms": 100, "confidence": 0.95}]
    )
    session_id = session["id"]
    for _ in range(3):
        client.post(f"/roleplay-sessions/{session_id}/turns", content=audio)
    resp = client.post(f"/roleplay-sessions/{session_id}/turns", content=audio)
    assert resp.status_code == 400


def test_submit_turn_malformed_audio_422(client) -> None:
    session = _create_session(client)
    resp = client.post(f"/roleplay-sessions/{session['id']}/turns", content=b"not json")
    assert resp.status_code == 422


def test_submit_turn_unknown_session_404(client) -> None:
    resp = client.post(
        "/roleplay-sessions/does-not-exist/turns",
        content=mock_transcript_bytes([{"text": "hi", "start_ms": 0, "end_ms": 100, "confidence": 0.9}]),
    )
    assert resp.status_code == 404


def test_create_multi_persona_session(client) -> None:
    resp = client.post(
        "/roleplay-sessions",
        json={"persona_ids": ["skeptical_stakeholder", "data_driven_skeptic"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["persona_ids"] == ["skeptical_stakeholder", "data_driven_skeptic"]
    assert body["turns"][0]["persona_id"] == "skeptical_stakeholder"


def test_create_session_requires_persona_id_or_ids(client) -> None:
    resp = client.post("/roleplay-sessions", json={})
    assert resp.status_code == 422


def test_create_multi_persona_session_unknown_persona_404(client) -> None:
    resp = client.post(
        "/roleplay-sessions", json={"persona_ids": ["skeptical_stakeholder", "does-not-exist"]}
    )
    assert resp.status_code == 404


def test_multi_persona_round_robin_and_speaker_attribution(client) -> None:
    session = client.post(
        "/roleplay-sessions",
        json={"persona_ids": ["skeptical_stakeholder", "data_driven_skeptic", "time_pressured_exec"]},
    ).json()
    session_id = session["id"]
    audio = mock_transcript_bytes(
        [{"text": "we", "start_ms": 0, "end_ms": 100, "confidence": 0.95},
         {"text": "should", "start_ms": 110, "end_ms": 200, "confidence": 0.95},
         {"text": "ship", "start_ms": 210, "end_ms": 300, "confidence": 0.95}]
    )

    speakers = []
    for _ in range(3):
        resp = client.post(f"/roleplay-sessions/{session_id}/turns", content=audio)
        speakers.append(resp.json()["new_turns"][1]["persona_id"])

    # round-robin: 1st user turn -> persona[0], 2nd -> persona[1], 3rd -> persona[2]
    assert speakers == ["skeptical_stakeholder", "data_driven_skeptic", "time_pressured_exec"]


def test_multi_persona_closes_on_group_turn_budget_not_per_persona(client) -> None:
    session = client.post(
        "/roleplay-sessions",
        json={"persona_ids": ["skeptical_stakeholder", "data_driven_skeptic"]},
    ).json()
    session_id = session["id"]
    audio = mock_transcript_bytes(
        [{"text": "yes", "start_ms": 0, "end_ms": 100, "confidence": 0.95}]
    )
    statuses = []
    for _ in range(4):
        resp = client.post(f"/roleplay-sessions/{session_id}/turns", content=audio)
        statuses.append(resp.json()["session_status"])

    # GROUP_MAX_USER_TURNS=4, shared across personas — not 3 turns per persona (would be 6)
    assert statuses == ["active", "active", "active", "completed"]


def test_account_delete_removes_roleplay_sessions(client) -> None:
    user_id = client.post("/users").json()["id"]
    session = _create_session(client, user_id=user_id)

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    resp = client.get(f"/roleplay-sessions/{session['id']}")
    assert resp.status_code == 404
