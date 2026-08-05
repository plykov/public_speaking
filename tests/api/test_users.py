from __future__ import annotations


def test_create_user(client) -> None:
    resp = client.post("/users")
    assert resp.status_code == 201
    body = resp.json()
    assert body["id"]
    assert body["created_at"]


def test_get_user(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}")
    assert resp.status_code == 200
    assert resp.json()["id"] == user_id


def test_get_unknown_user_404(client) -> None:
    resp = client.get("/users/does-not-exist")
    assert resp.status_code == 404


def test_create_and_fetch_l1_profile(client) -> None:
    user_id = client.post("/users").json()["id"]

    resp = client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Russian", "self_declared_confidence": "comfortable"},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["user_id"] == user_id
    assert body["first_language"] == "Russian"

    resp = client.get(f"/users/{user_id}/l1-profile")
    assert resp.status_code == 200
    assert resp.json()["self_declared_confidence"] == "comfortable"


def test_l1_profile_upsert_overwrites(client) -> None:
    user_id = client.post("/users").json()["id"]
    client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Dutch", "self_declared_confidence": "building"},
    )
    resp = client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Dutch", "self_declared_confidence": "fluent"},
    )
    assert resp.json()["self_declared_confidence"] == "fluent"

    resp = client.get(f"/users/{user_id}/l1-profile")
    assert resp.json()["self_declared_confidence"] == "fluent"


def test_l1_profile_for_unknown_user_404(client) -> None:
    resp = client.put(
        "/users/does-not-exist/l1-profile",
        json={"first_language": "French", "self_declared_confidence": "fluent"},
    )
    assert resp.status_code == 404


def test_get_l1_profile_before_created_404(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.get(f"/users/{user_id}/l1-profile")
    assert resp.status_code == 404


def test_l1_calibration_catalog(client) -> None:
    resp = client.get("/l1-calibration-profiles")
    assert resp.status_code == 200
    body = resp.json()
    codes = {p["code"] for p in body}
    assert {"ru", "nl", "de", "fr", "es", "pt-br", "zh", "hi", "ja"} <= codes
    for p in body:
        assert p["label"]
        assert p["calibration_note"]


def test_l1_profile_with_catalog_code_returns_calibration_note(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(
        f"/users/{user_id}/l1-profile",
        json={
            "first_language": "Russian",
            "self_declared_confidence": "comfortable",
            "first_language_code": "ru",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["first_language_code"] == "ru"
    assert "point" in body["calibration_note"].lower() or "context" in body["calibration_note"].lower()

    resp = client.get(f"/users/{user_id}/l1-profile")
    assert resp.json()["calibration_note"] == body["calibration_note"]


def test_l1_profile_without_catalog_code_has_no_calibration_note(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(
        f"/users/{user_id}/l1-profile",
        json={"first_language": "Klingon", "self_declared_confidence": "fluent"},
    )
    assert resp.json()["first_language_code"] is None
    assert resp.json()["calibration_note"] is None


def test_l1_profile_unknown_code_falls_back_to_no_note(client) -> None:
    user_id = client.post("/users").json()["id"]
    resp = client.put(
        f"/users/{user_id}/l1-profile",
        json={
            "first_language": "Whatever",
            "self_declared_confidence": "fluent",
            "first_language_code": "xx-not-real",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["calibration_note"] is None
