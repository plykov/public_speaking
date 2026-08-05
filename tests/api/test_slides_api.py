from __future__ import annotations

import fitz


def _make_pdf(n_pages: int) -> bytes:
    doc = fitz.open()
    for i in range(n_pages):
        page = doc.new_page(width=300, height=200)
        page.insert_text((20, 100), f"Slide {i + 1}")
    return doc.tobytes()


def _make_session(client) -> str:
    return client.post("/sessions", json={"scenario": "standup"}).json()["id"]


def test_upload_slides_returns_deck_metadata(client) -> None:
    session_id = _make_session(client)
    resp = client.post(
        f"/sessions/{session_id}/slides?filename=deck.pdf",
        content=_make_pdf(3),
        headers={"content-type": "application/pdf"},
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["filename"] == "deck.pdf"
    assert body["page_count"] == 3
    assert len(body["thumbnail_urls"]) == 3


def test_get_slides_before_upload_404(client) -> None:
    session_id = _make_session(client)
    resp = client.get(f"/sessions/{session_id}/slides")
    assert resp.status_code == 404


def test_get_slides_after_upload(client) -> None:
    session_id = _make_session(client)
    client.post(f"/sessions/{session_id}/slides", content=_make_pdf(2))
    resp = client.get(f"/sessions/{session_id}/slides")
    assert resp.status_code == 200
    assert resp.json()["page_count"] == 2


def test_thumbnail_is_a_real_png(client) -> None:
    session_id = _make_session(client)
    client.post(f"/sessions/{session_id}/slides", content=_make_pdf(2))
    resp = client.get(f"/sessions/{session_id}/slides/0/thumbnail")
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/png"
    assert resp.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_thumbnail_out_of_range_404(client) -> None:
    session_id = _make_session(client)
    client.post(f"/sessions/{session_id}/slides", content=_make_pdf(2))
    resp = client.get(f"/sessions/{session_id}/slides/5/thumbnail")
    assert resp.status_code == 404


def test_reupload_replaces_previous_deck(client) -> None:
    session_id = _make_session(client)
    client.post(f"/sessions/{session_id}/slides", content=_make_pdf(5))
    resp = client.post(f"/sessions/{session_id}/slides", content=_make_pdf(2))
    assert resp.json()["page_count"] == 2

    resp = client.get(f"/sessions/{session_id}/slides")
    assert resp.json()["page_count"] == 2
    # the old 5th-page thumbnail must be gone, not just orphaned
    assert client.get(f"/sessions/{session_id}/slides/4/thumbnail").status_code == 404


def test_upload_garbage_bytes_is_422(client) -> None:
    session_id = _make_session(client)
    resp = client.post(f"/sessions/{session_id}/slides", content=b"not a pdf")
    assert resp.status_code == 422


def test_slides_for_unknown_session_404(client) -> None:
    resp = client.post("/sessions/does-not-exist/slides", content=_make_pdf(1))
    assert resp.status_code == 404


def test_upsert_and_get_slide_transitions(client) -> None:
    session_id = _make_session(client)
    resp = client.put(
        f"/sessions/{session_id}/slide-transitions",
        json={"transitions": [{"slide_index": 1, "timestamp_ms": 5000}, {"slide_index": 0, "timestamp_ms": 0}]},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert [t["slide_index"] for t in body] == [0, 1]  # sorted by timestamp

    resp = client.get(f"/sessions/{session_id}/slide-transitions")
    assert [t["timestamp_ms"] for t in resp.json()] == [0, 5000]


def test_upsert_slide_transitions_replaces_not_appends(client) -> None:
    session_id = _make_session(client)
    client.put(
        f"/sessions/{session_id}/slide-transitions",
        json={"transitions": [{"slide_index": 0, "timestamp_ms": 0}]},
    )
    client.put(
        f"/sessions/{session_id}/slide-transitions",
        json={"transitions": [{"slide_index": 0, "timestamp_ms": 0}, {"slide_index": 1, "timestamp_ms": 3000}]},
    )
    resp = client.get(f"/sessions/{session_id}/slide-transitions")
    assert len(resp.json()) == 2


def test_negative_slide_index_rejected(client) -> None:
    session_id = _make_session(client)
    resp = client.put(
        f"/sessions/{session_id}/slide-transitions",
        json={"transitions": [{"slide_index": -1, "timestamp_ms": 0}]},
    )
    assert resp.status_code == 422


def test_session_delete_removes_slide_deck(client) -> None:
    session_id = _make_session(client)
    client.post(f"/sessions/{session_id}/slides", content=_make_pdf(2))
    client.put(
        f"/sessions/{session_id}/slide-transitions",
        json={"transitions": [{"slide_index": 0, "timestamp_ms": 0}]},
    )
    resp = client.delete(f"/sessions/{session_id}")
    assert resp.status_code == 204

    # session itself is gone, so slide endpoints now 404 at the session check
    assert client.get(f"/sessions/{session_id}/slides").status_code == 404
