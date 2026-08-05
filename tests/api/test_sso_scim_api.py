from __future__ import annotations


def _user(client) -> str:
    return client.post("/users").json()["id"]


def _team(client) -> tuple[str, str]:
    admin_id = _user(client)
    team = client.post("/teams", json={"name": "Acme", "admin_user_id": admin_id}).json()
    return team["id"], admin_id


# --- SSO ---


def test_get_sso_login_url(client) -> None:
    team_id, _ = _team(client)
    resp = client.get(f"/teams/{team_id}/sso/login-url?redirect_uri=https://x.example/cb")
    assert resp.status_code == 200
    url = resp.json()["authorization_url"]
    assert team_id in url
    assert "x.example" in url


def test_sso_login_url_unknown_team_404(client) -> None:
    resp = client.get("/teams/does-not-exist/sso/login-url")
    assert resp.status_code == 404


def test_sso_callback_creates_user_and_membership(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(f"/teams/{team_id}/sso/callback", json={"code": "abc123"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["created_user"] is True
    assert body["created_membership"] is True
    assert body["role"] == "member"

    team = client.get(f"/teams/{team_id}").json()
    assert any(m["user_id"] == body["user_id"] for m in team["members"])


def test_sso_callback_same_code_reuses_identity(client) -> None:
    team_id, _ = _team(client)
    first = client.post(f"/teams/{team_id}/sso/callback", json={"code": "stable-code"}).json()
    second = client.post(f"/teams/{team_id}/sso/callback", json={"code": "stable-code"}).json()
    assert first["user_id"] == second["user_id"]
    assert second["created_user"] is False
    assert second["created_membership"] is False


def test_sso_callback_unknown_team_404(client) -> None:
    resp = client.post("/teams/does-not-exist/sso/callback", json={"code": "x"})
    assert resp.status_code == 404


def test_sso_callback_empty_code_422(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(f"/teams/{team_id}/sso/callback", json={"code": ""})
    assert resp.status_code == 422


# --- SCIM ---


def test_scim_list_users(client) -> None:
    team_id, admin_id = _team(client)
    resp = client.get(f"/scim/v2/Teams/{team_id}/Users")
    assert resp.status_code == 200
    body = resp.json()
    assert body["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:ListResponse"]
    assert body["totalResults"] == 1
    assert body["Resources"][0]["id"] == admin_id


def test_scim_list_users_unknown_team_404(client) -> None:
    resp = client.get("/scim/v2/Teams/does-not-exist/Users")
    assert resp.status_code == 404
    assert resp.json()["detail"]["schemas"] == ["urn:ietf:params:scim:api:messages:2.0:Error"]


def test_scim_create_user_provisions_new_user(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(
        f"/scim/v2/Teams/{team_id}/Users",
        json={"userName": "priya@acme.com", "emails": [{"value": "priya@acme.com"}], "active": True},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["userName"] == "priya@acme.com"
    assert body["emails"][0]["value"] == "priya@acme.com"
    assert body["active"] is True

    listed = client.get(f"/scim/v2/Teams/{team_id}/Users").json()
    assert listed["totalResults"] == 2


def test_scim_create_user_requires_username_or_external_id(client) -> None:
    team_id, _ = _team(client)
    resp = client.post(f"/scim/v2/Teams/{team_id}/Users", json={})
    assert resp.status_code == 400


def test_scim_create_duplicate_user_409(client) -> None:
    team_id, _ = _team(client)
    client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "dup@acme.com"})
    resp = client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "dup@acme.com"})
    assert resp.status_code == 409


def test_scim_get_user(client) -> None:
    team_id, admin_id = _team(client)
    resp = client.get(f"/scim/v2/Teams/{team_id}/Users/{admin_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == admin_id


def test_scim_get_user_not_on_team_404(client) -> None:
    team_id, _ = _team(client)
    outsider_id = _user(client)
    resp = client.get(f"/scim/v2/Teams/{team_id}/Users/{outsider_id}")
    assert resp.status_code == 404


def test_scim_patch_deactivate_removes_membership(client) -> None:
    team_id, _ = _team(client)
    created = client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "leaving@acme.com"}).json()

    resp = client.patch(
        f"/scim/v2/Teams/{team_id}/Users/{created['id']}",
        json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is False

    listed = client.get(f"/scim/v2/Teams/{team_id}/Users").json()
    assert all(u["id"] != created["id"] for u in listed["Resources"])


def test_scim_patch_reactivate_restores_membership(client) -> None:
    team_id, _ = _team(client)
    created = client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "backagain@acme.com"}).json()
    client.patch(
        f"/scim/v2/Teams/{team_id}/Users/{created['id']}",
        json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
    )
    resp = client.patch(
        f"/scim/v2/Teams/{team_id}/Users/{created['id']}",
        json={"Operations": [{"op": "replace", "path": "active", "value": True}]},
    )
    assert resp.status_code == 200
    assert resp.json()["active"] is True
    listed = client.get(f"/scim/v2/Teams/{team_id}/Users").json()
    assert any(u["id"] == created["id"] for u in listed["Resources"])


def test_scim_delete_user_removes_membership(client) -> None:
    team_id, _ = _team(client)
    created = client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "gone@acme.com"}).json()
    resp = client.delete(f"/scim/v2/Teams/{team_id}/Users/{created['id']}")
    assert resp.status_code == 204

    listed = client.get(f"/scim/v2/Teams/{team_id}/Users").json()
    assert all(u["id"] != created["id"] for u in listed["Resources"])


def test_scim_patch_unknown_user_404(client) -> None:
    team_id, _ = _team(client)
    resp = client.patch(
        f"/scim/v2/Teams/{team_id}/Users/does-not-exist",
        json={"Operations": [{"op": "replace", "path": "active", "value": False}]},
    )
    assert resp.status_code == 404


def test_scim_delete_unknown_user_404(client) -> None:
    team_id, _ = _team(client)
    resp = client.delete(f"/scim/v2/Teams/{team_id}/Users/does-not-exist")
    assert resp.status_code == 404


def test_scim_provisioning_appears_in_audit_log(client) -> None:
    team_id, _ = _team(client)
    client.post(f"/scim/v2/Teams/{team_id}/Users", json={"userName": "audited@acme.com"})
    body = client.get(f"/teams/{team_id}/audit-log").json()
    assert any(e["action"] == "team.scim.provision" for e in body)
