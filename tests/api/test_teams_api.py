from __future__ import annotations


def _user(client) -> str:
    return client.post("/users").json()["id"]


def test_create_team_adds_admin_membership(client) -> None:
    admin_id = _user(client)
    resp = client.post("/teams", json={"name": "Acme Sales", "admin_user_id": admin_id})
    assert resp.status_code == 201
    body = resp.json()
    assert body["name"] == "Acme Sales"
    assert len(body["members"]) == 1
    assert body["members"][0] == {"user_id": admin_id, "role": "admin", "joined_at": body["members"][0]["joined_at"]}


def test_create_team_unknown_admin_404(client) -> None:
    resp = client.post("/teams", json={"name": "Acme", "admin_user_id": "does-not-exist"})
    assert resp.status_code == 404


def test_get_team(client) -> None:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    resp = client.get(f"/teams/{team['id']}")
    assert resp.status_code == 200
    assert resp.json()["id"] == team["id"]


def test_get_team_unknown_404(client) -> None:
    resp = client.get("/teams/does-not-exist")
    assert resp.status_code == 404


def test_list_teams_for_user(client) -> None:
    admin_id = _user(client)
    client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id})
    client.post("/teams", json={"name": "Beta Corp", "admin_user_id": admin_id})

    resp = client.get(f"/users/{admin_id}/teams")
    assert resp.status_code == 200
    names = {t["name"] for t in resp.json()}
    assert names == {"Acme", "Beta Corp"}


def test_list_teams_for_user_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist/teams")
    assert resp.status_code == 404


def test_list_teams_empty_for_user_with_no_teams(client) -> None:
    user_id = _user(client)
    resp = client.get(f"/users/{user_id}/teams")
    assert resp.json() == []


def test_invite_and_accept_flow(client) -> None:
    admin_id = _user(client)
    member_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()

    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()
    assert invite["accepted"] is False

    resp = client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": member_id})
    assert resp.status_code == 200
    assert resp.json() == {"user_id": member_id, "role": "member", "joined_at": resp.json()["joined_at"]}

    team_after = client.get(f"/teams/{team['id']}").json()
    assert len(team_after["members"]) == 2


def test_invite_rejects_invalid_role(client) -> None:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    resp = client.post(f"/teams/{team['id']}/invites", json={"role": "owner"})
    assert resp.status_code == 422


def test_accept_invite_twice_is_410(client) -> None:
    admin_id = _user(client)
    member_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()

    client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": member_id})
    resp = client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": member_id})
    assert resp.status_code == 410


def test_accept_invite_already_a_member_409(client) -> None:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()

    resp = client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": admin_id})
    assert resp.status_code == 409


def test_accept_unknown_invite_404(client) -> None:
    user_id = _user(client)
    resp = client.post("/team-invites/not-a-real-token/accept", json={"user_id": user_id})
    assert resp.status_code == 404


def test_accept_invite_unknown_user_404(client) -> None:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()
    resp = client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": "does-not-exist"})
    assert resp.status_code == 404


def test_update_member_role(client) -> None:
    admin_id = _user(client)
    member_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()
    client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": member_id})

    resp = client.put(f"/teams/{team['id']}/members/{member_id}/role", json={"role": "admin"})
    assert resp.status_code == 200
    assert resp.json()["role"] == "admin"


def test_update_role_rejects_invalid_role(client) -> None:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    resp = client.put(f"/teams/{team['id']}/members/{admin_id}/role", json={"role": "superadmin"})
    assert resp.status_code == 422


def test_update_role_non_member_404(client) -> None:
    admin_id = _user(client)
    other_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    resp = client.put(f"/teams/{team['id']}/members/{other_id}/role", json={"role": "admin"})
    assert resp.status_code == 404


def test_remove_team_member(client) -> None:
    admin_id = _user(client)
    member_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    invite = client.post(f"/teams/{team['id']}/invites", json={"role": "member"}).json()
    client.post(f"/team-invites/{invite['token']}/accept", json={"user_id": member_id})

    resp = client.delete(f"/teams/{team['id']}/members/{member_id}")
    assert resp.status_code == 204

    team_after = client.get(f"/teams/{team['id']}").json()
    assert len(team_after["members"]) == 1


def test_remove_non_member_404(client) -> None:
    admin_id = _user(client)
    other_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    resp = client.delete(f"/teams/{team['id']}/members/{other_id}")
    assert resp.status_code == 404


def _team(client) -> tuple[str, str]:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    return team["id"], admin_id


def test_create_and_list_team_scenario(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(
        f"/teams/{team_id}/scenarios",
        json={"title": "Exec review", "prompt": "Give a 2-minute update to the VP."},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["title"] == "Exec review"
    assert body["team_id"] == team_id

    resp = client.get(f"/teams/{team_id}/scenarios")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


def test_create_scenario_unknown_team_404(client) -> None:
    resp = client.post(
        "/teams/does-not-exist/scenarios", json={"title": "x", "prompt": "y"}
    )
    assert resp.status_code == 404


def test_delete_team_scenario(client) -> None:
    team_id, _ = _team(client)
    scenario = client.post(
        f"/teams/{team_id}/scenarios", json={"title": "x", "prompt": "y"}
    ).json()

    resp = client.delete(f"/teams/{team_id}/scenarios/{scenario['id']}")
    assert resp.status_code == 204
    assert client.get(f"/teams/{team_id}/scenarios").json() == []


def test_delete_unknown_scenario_404(client) -> None:
    team_id, _ = _team(client)
    resp = client.delete(f"/teams/{team_id}/scenarios/does-not-exist")
    assert resp.status_code == 404


def test_create_and_list_team_rubric(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(
        f"/teams/{team_id}/rubrics",
        json={"name": "Exec rubric", "criteria": ["point_first_clarity", "executive_presence"]},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["criteria"] == ["point_first_clarity", "executive_presence"]

    resp = client.get(f"/teams/{team_id}/rubrics")
    assert len(resp.json()) == 1


def test_create_rubric_rejects_empty_criteria(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(f"/teams/{team_id}/rubrics", json={"name": "x", "criteria": []})
    assert resp.status_code == 422


def test_create_rubric_unknown_team_404(client) -> None:
    resp = client.post(
        "/teams/does-not-exist/rubrics", json={"name": "x", "criteria": ["a"]}
    )
    assert resp.status_code == 404


def test_delete_team_rubric(client) -> None:
    team_id, _ = _team(client)
    rubric = client.post(
        f"/teams/{team_id}/rubrics", json={"name": "x", "criteria": ["a"]}
    ).json()

    resp = client.delete(f"/teams/{team_id}/rubrics/{rubric['id']}")
    assert resp.status_code == 204
    assert client.get(f"/teams/{team_id}/rubrics").json() == []


def test_delete_unknown_rubric_404(client) -> None:
    team_id, _ = _team(client)
    resp = client.delete(f"/teams/{team_id}/rubrics/does-not-exist")
    assert resp.status_code == 404
