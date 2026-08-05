from __future__ import annotations

import json
from datetime import datetime, timezone

import pytest

from api.meeting_import import (
    MockMeetingRecordingProvider,
    RecordingNotFoundError,
    get_meeting_recording_provider,
)


def test_list_available_recordings_returns_past_meetings_only() -> None:
    provider = MockMeetingRecordingProvider()
    recordings = provider.list_available_recordings("some-user")
    assert len(recordings) >= 1
    now = datetime.now(timezone.utc)
    for r in recordings:
        assert r.occurred_at < now


def test_get_recording_metadata_known_id() -> None:
    provider = MockMeetingRecordingProvider()
    recordings = provider.list_available_recordings("some-user")
    meta = provider.get_recording_metadata(recordings[0].id)
    assert meta.id == recordings[0].id


def test_get_recording_metadata_unknown_raises() -> None:
    with pytest.raises(RecordingNotFoundError):
        MockMeetingRecordingProvider().get_recording_metadata("does-not-exist")


def test_fetch_recording_bytes_is_valid_mock_stt_payload() -> None:
    provider = MockMeetingRecordingProvider()
    recordings = provider.list_available_recordings("some-user")
    raw = provider.fetch_recording_bytes(recordings[0].id)
    words = json.loads(raw.decode("utf-8"))
    assert isinstance(words, list)
    assert all({"text", "start_ms", "end_ms", "confidence"} <= set(w) for w in words)


def test_fetch_recording_bytes_unknown_id_raises() -> None:
    with pytest.raises(RecordingNotFoundError):
        MockMeetingRecordingProvider().fetch_recording_bytes("does-not-exist")


def test_get_meeting_recording_provider_mock() -> None:
    assert isinstance(get_meeting_recording_provider("mock"), MockMeetingRecordingProvider)


def test_get_meeting_recording_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_meeting_recording_provider("zoom")
