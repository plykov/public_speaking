from __future__ import annotations


def test_calendar_status_before_connecting(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/calendar")
    assert resp.status_code == 200
    assert resp.json() == {"connected": False, "provider": None}


def test_connect_calendar(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.post(f"/users/{user_id}/calendar/connect", json={})
    assert resp.status_code == 200
    assert resp.json() == {"connected": True, "provider": "mock"}

    resp = client.get(f"/users/{user_id}/calendar")
    assert resp.json() == {"connected": True, "provider": "mock"}


def test_connect_calendar_unknown_user_404(client) -> None:
    resp = client.post("/users/does-not-exist/calendar/connect", json={})
    assert resp.status_code == 404


def test_reconnect_updates_provider(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/calendar/connect", json={"provider": "mock"})
    resp = client.post(f"/users/{user_id}/calendar/connect", json={"provider": "mock"})
    assert resp.status_code == 200


def test_disconnect_calendar(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/calendar/connect", json={})
    resp = client.delete(f"/users/{user_id}/calendar")
    assert resp.status_code == 204

    resp = client.get(f"/users/{user_id}/calendar")
    assert resp.json()["connected"] is False


def test_upcoming_prompt_requires_connection(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/calendar/upcoming-prompt")
    assert resp.status_code == 400


def test_upcoming_prompt_after_connecting(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/calendar/connect", json={})

    resp = client.get(f"/users/{user_id}/calendar/upcoming-prompt")
    assert resp.status_code == 200
    body = resp.json()
    assert body["has_prompt"] is True
    assert body["event_title"] == "Team Standup"
    assert body["minutes_until"] is not None
    assert body["drill"]["targets_criterion"] == "point_first_clarity"


def test_upcoming_prompt_no_imminent_event(client, monkeypatch) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/calendar/connect", json={})

    monkeypatch.setattr("api.routers.calendar.next_prompt_worthy_event", lambda events, now: None)

    resp = client.get(f"/users/{user_id}/calendar/upcoming-prompt")
    assert resp.status_code == 200
    assert resp.json() == {
        "has_prompt": False,
        "event_title": None,
        "minutes_until": None,
        "drill": None,
    }


def test_upcoming_prompt_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/calendar/upcoming-prompt")
    assert resp.status_code == 404


def test_account_delete_removes_calendar_connection(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.post(f"/users/{user_id}/calendar/connect", json={})

    resp = client.delete(f"/users/{user_id}")
    assert resp.status_code == 204

    # user itself is gone, so this now 404s at the user check rather than
    # returning a stale connection
    resp = client.get(f"/users/{user_id}/calendar")
    assert resp.status_code == 404
