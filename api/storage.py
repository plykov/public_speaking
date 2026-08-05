"""Object storage abstraction (§6.1: S3-compatible, private, signed URLs).

`LocalObjectStore` is the dev/test implementation — it writes chunks to
disk and supports resumable append-by-offset uploads so a dropped
connection never destroys a partially-uploaded recording (§4.1 M2, §5
"a completed recording is never lost to a network failure"). Swapping in
a real S3-compatible backend means implementing this same interface
against boto3 / a presigned-URL flow; nothing above this layer should
need to change.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass


class UploadConflict(Exception):
    """Raised when a chunk write does not match the expected offset."""


@dataclass(frozen=True)
class UploadStatus:
    key: str
    bytes_received: int


class ObjectStore(ABC):
    @abstractmethod
    def write_chunk(self, key: str, offset: int, data: bytes) -> UploadStatus:
        """Append `data` at `offset`. Re-sending the same offset is a no-op-safe retry."""

    @abstractmethod
    def read(self, key: str) -> bytes:
        """Read the full object back."""

    @abstractmethod
    def status(self, key: str) -> UploadStatus:
        """Bytes received so far for a resumable upload, without reading the payload."""

    @abstractmethod
    def delete(self, key: str) -> None:
        """One-click delete (§6.5 privacy controls)."""

    @abstractmethod
    def signed_url(self, key: str) -> str:
        """A short-lived, private access URL (§6.5: signed URLs only, never public)."""


class LocalObjectStore(ObjectStore):
    def __init__(self, base_dir: str) -> None:
        self._base_dir = base_dir
        os.makedirs(self._base_dir, exist_ok=True)

    def _path(self, key: str) -> str:
        safe_key = key.replace("/", "_")
        return os.path.join(self._base_dir, safe_key)

    def write_chunk(self, key: str, offset: int, data: bytes) -> UploadStatus:
        path = self._path(key)
        current_size = os.path.getsize(path) if os.path.exists(path) else 0

        if offset > current_size:
            raise UploadConflict(
                f"chunk offset {offset} is ahead of {current_size} bytes received for {key!r}"
            )
        if offset < current_size:
            # Already-received bytes being retried — accept idempotently, no rewrite.
            return UploadStatus(key=key, bytes_received=current_size)

        with open(path, "ab") as f:
            f.write(data)
        return UploadStatus(key=key, bytes_received=current_size + len(data))

    def read(self, key: str) -> bytes:
        with open(self._path(key), "rb") as f:
            return f.read()

    def status(self, key: str) -> UploadStatus:
        path = self._path(key)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        return UploadStatus(key=key, bytes_received=size)

    def delete(self, key: str) -> None:
        path = self._path(key)
        if os.path.exists(path):
            os.remove(path)

    def signed_url(self, key: str) -> str:
        # Dev stand-in only — a real backend returns a short-lived presigned S3 URL.
        return f"local://{self._path(key)}"
