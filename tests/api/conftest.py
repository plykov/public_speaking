from __future__ import annotations

import os
import tempfile

# Must be set before `api.config` (and anything importing it) is first
# imported, since Settings() reads the environment at import time.
_tmpdir = tempfile.mkdtemp(prefix="cadence-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmpdir}/test.db"
os.environ["STORAGE_DIR"] = os.path.join(_tmpdir, "media")

import json

import pytest
from fastapi.testclient import TestClient

from api.db import init_db
from api.main import app


@pytest.fixture(scope="session", autouse=True)
def _init_db():
    init_db()


@pytest.fixture()
def client():
    return TestClient(app)


def mock_transcript_bytes(words: list[dict]) -> bytes:
    """Build the fake 'audio' payload MockSTTProvider understands."""
    return json.dumps(words).encode("utf-8")
