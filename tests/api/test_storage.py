from __future__ import annotations

import pytest

from api.storage import LocalObjectStore, UploadConflict


def test_write_and_read_single_chunk(tmp_path) -> None:
    store = LocalObjectStore(str(tmp_path))
    status = store.write_chunk("k1", 0, b"hello ")
    assert status.bytes_received == 6
    status = store.write_chunk("k1", 6, b"world")
    assert status.bytes_received == 11
    assert store.read("k1") == b"hello world"


def test_retrying_same_offset_is_idempotent(tmp_path) -> None:
    store = LocalObjectStore(str(tmp_path))
    store.write_chunk("k1", 0, b"hello")
    # Client retries the same chunk after a dropped ack — must not duplicate.
    status = store.write_chunk("k1", 0, b"hello")
    assert status.bytes_received == 5
    assert store.read("k1") == b"hello"


def test_chunk_ahead_of_received_bytes_raises_conflict(tmp_path) -> None:
    store = LocalObjectStore(str(tmp_path))
    store.write_chunk("k1", 0, b"hello")
    with pytest.raises(UploadConflict):
        store.write_chunk("k1", 100, b"gap")


def test_status_before_any_write(tmp_path) -> None:
    store = LocalObjectStore(str(tmp_path))
    status = store.status("never-written")
    assert status.bytes_received == 0


def test_delete_removes_object(tmp_path) -> None:
    store = LocalObjectStore(str(tmp_path))
    store.write_chunk("k1", 0, b"data")
    store.delete("k1")
    assert store.status("k1").bytes_received == 0
