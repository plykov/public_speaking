"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

import re
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

_VALID_DAYS = {"mon", "tue", "wed", "thu", "fri", "sat", "sun"}
_TIME_RE = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    created_at: datetime


class CreateL1ProfileRequest(BaseModel):
    first_language: str
    self_declared_confidence: str  # e.g. "building" | "comfortable" | "fluent" — copy/calibration only


class L1ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    first_language: str
    self_declared_confidence: str


class CreateSessionRequest(BaseModel):
    scenario: str = "general"
    user_id: str | None = None
    parent_session_id: str | None = None  # set on a retry to link it to the original attempt


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str | None
    parent_session_id: str | None
    scenario: str
    status: str
    created_at: datetime


class UploadChunkResponse(BaseModel):
    bytes_received: int


class FeedbackItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    criterion: str
    observation: str
    rationale: str
    repair: str
    evidence_text: str
    evidence_start_ms: int
    evidence_end_ms: int
    user_rating: bool | None


class RateFeedbackRequest(BaseModel):
    useful: bool


class DrillOut(BaseModel):
    id: str
    title: str
    prompt: str
    duration_minutes: str
    targets_criterion: str | None


class AnalysisResultOut(BaseModel):
    session_id: str
    rubric_version: str
    model_version: str
    transcript_text: str
    metrics_summary: dict
    feedback_items: list[FeedbackItemOut]
    drill: DrillOut
    created_at: datetime


class TranscriptWordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    seq_index: int
    text: str
    start_ms: int
    end_ms: int
    confidence: float


class UpdateTranscriptRequest(BaseModel):
    """§4.1 M8: corrected word text, same length/order as the original
    transcript — timestamps are never user-editable, only what was said."""

    words: list[str]


class UpsertReminderRequest(BaseModel):
    """§4.1 M10: calendar-free reminder window preference."""

    days: list[str]  # subset of mon/tue/wed/thu/fri/sat/sun
    time_of_day: str  # "HH:MM", 24h

    @field_validator("days")
    @classmethod
    def _validate_days(cls, value: list[str]) -> list[str]:
        invalid = set(value) - _VALID_DAYS
        if invalid:
            raise ValueError(f"invalid day(s): {sorted(invalid)}")
        if not value:
            raise ValueError("days must not be empty")
        return value

    @field_validator("time_of_day")
    @classmethod
    def _validate_time(cls, value: str) -> str:
        if not _TIME_RE.match(value):
            raise ValueError('time_of_day must be "HH:MM" in 24h format')
        return value


class ReminderOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    days: list[str]
    time_of_day: str


class StreakOut(BaseModel):
    """§4.1 M10: non-punitive streak, self-relative — see api/streaks.py."""

    current_streak: int
    longest_streak: int
    freeze_used_in_current_streak: bool
    last_practice_date: str | None


class AttemptSummaryOut(BaseModel):
    """One row of §4.1 M9 progress data — self-relative only, no ranking
    against other users' attempts."""

    session_id: str
    parent_session_id: str | None
    scenario: str
    created_at: datetime
    wpm_overall: float
    filler_rate_per_100_words: float
    hedging_rate_per_100_words: float
    point_position_score: float
