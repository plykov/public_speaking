"""Consented post-meeting analysis of Zoom/Teams/Meet recordings (§4.3).

Real Zoom/Teams/Meet API integration needs an actual OAuth app
registration with each platform (client id/secret, cloud-recording scope
approval) — a vendor-credential gap in the same category as Stripe,
calendar, or SSO. `MeetingRecordingProvider` is the seam a real
integration implements; `MockMeetingRecordingProvider` returns a
deterministic catalog of synthetic past meetings and a JSON word-list
payload when "fetching" one — exactly `api.pipeline.stt`'s mock STT
contract, so an imported recording flows through the exact same real
pipeline (STT → deterministic metrics → LLM rubric → evidence
validation) any other session does. Only the "get bytes from a
video-platform vendor" leg is mocked.

**Never live interception**, structurally, not just by policy:
`list_available_recordings` only returns recordings whose `occurred_at`
is already in the past, and nothing in this module has a "join meeting,"
"start capture," or streaming code path at all — importing is a one-shot
fetch of an already-finished, already-recorded meeting the user explicitly
chooses and consents to.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone


@dataclass(frozen=True)
class MeetingRecording:
    id: str
    title: str
    platform: str  # "zoom" | "teams" | "meet"
    occurred_at: datetime


class RecordingNotFoundError(Exception):
    pass


class MeetingRecordingProvider(ABC):
    @abstractmethod
    def list_available_recordings(self, external_user_id: str) -> list[MeetingRecording]: ...

    @abstractmethod
    def get_recording_metadata(self, recording_id: str) -> MeetingRecording: ...

    @abstractmethod
    def fetch_recording_bytes(self, recording_id: str) -> bytes: ...


_MOCK_WORDS = [
    {"text": "So", "start_ms": 0, "end_ms": 150, "confidence": 0.97},
    {"text": "maybe", "start_ms": 200, "end_ms": 420, "confidence": 0.9},
    {"text": "we", "start_ms": 430, "end_ms": 520, "confidence": 0.97},
    {"text": "should", "start_ms": 530, "end_ms": 680, "confidence": 0.96},
    {"text": "revisit", "start_ms": 690, "end_ms": 950, "confidence": 0.95},
    {"text": "the", "start_ms": 960, "end_ms": 1020, "confidence": 0.97},
    {"text": "timeline.", "start_ms": 1030, "end_ms": 1400, "confidence": 0.95},
]


class MockMeetingRecordingProvider(MeetingRecordingProvider):
    def _catalog(self) -> list[MeetingRecording]:
        now = datetime.now(timezone.utc)
        return [
            MeetingRecording(
                id="mock-standup-recording",
                title="Team Standup — recorded",
                platform="zoom",
                occurred_at=now - timedelta(days=1),
            ),
            MeetingRecording(
                id="mock-review-recording",
                title="Quarterly Review — recorded",
                platform="teams",
                occurred_at=now - timedelta(days=3),
            ),
        ]

    def list_available_recordings(self, external_user_id: str) -> list[MeetingRecording]:
        return self._catalog()

    def get_recording_metadata(self, recording_id: str) -> MeetingRecording:
        for recording in self._catalog():
            if recording.id == recording_id:
                return recording
        raise RecordingNotFoundError(recording_id)

    def fetch_recording_bytes(self, recording_id: str) -> bytes:
        self.get_recording_metadata(recording_id)  # raises RecordingNotFoundError if unknown
        return json.dumps(_MOCK_WORDS).encode("utf-8")


def get_meeting_recording_provider(name: str) -> MeetingRecordingProvider:
    if name == "mock":
        return MockMeetingRecordingProvider()
    raise NotImplementedError(
        f"Meeting recording provider {name!r} is not wired up yet — integrate the Zoom/Teams/"
        "Meet cloud-recording API behind this same MeetingRecordingProvider interface."
    )
