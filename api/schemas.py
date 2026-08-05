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
    first_language_code: str | None = None  # §4.2: catalog code, e.g. "ru" — see api/l1_calibration.py


class L1ProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    first_language: str
    self_declared_confidence: str
    first_language_code: str | None = None
    calibration_note: str | None = None  # §4.2 — derived from first_language_code, never stored


class L1CalibrationProfileOut(BaseModel):
    code: str
    label: str
    calibration_note: str


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


class CreateCheckoutRequest(BaseModel):
    tier: str  # "pro" | "event_sprint" — team is sold out of band


class CheckoutSessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tier: str
    status: str
    url: str


class SubscriptionOut(BaseModel):
    tier: str  # the EFFECTIVE tier (event_sprint auto-reverts to free once expired)
    status: str
    current_period_end: datetime | None
    analyses_this_month: int
    analyses_limit: int | None  # None = unlimited


class VapidPublicKeyOut(BaseModel):
    public_key: str


class PushSubscriptionKeys(BaseModel):
    p256dh: str
    auth: str


class PushSubscribeRequest(BaseModel):
    """The shape `PushSubscription.toJSON()` produces in the browser."""

    endpoint: str
    keys: PushSubscriptionKeys


class PushUnsubscribeRequest(BaseModel):
    endpoint: str


class PushTestResult(BaseModel):
    sent: int
    failed: int
    removed_stale: int


class SlideDeckOut(BaseModel):
    filename: str
    page_count: int
    thumbnail_urls: list[str]  # index-ordered, one per page


class SlideTransitionIn(BaseModel):
    slide_index: int
    timestamp_ms: int

    @field_validator("slide_index")
    @classmethod
    def _non_negative_index(cls, value: int) -> int:
        if value < 0:
            raise ValueError("slide_index must be >= 0")
        return value

    @field_validator("timestamp_ms")
    @classmethod
    def _non_negative_timestamp(cls, value: int) -> int:
        if value < 0:
            raise ValueError("timestamp_ms must be >= 0")
        return value


class UpsertSlideTransitionsRequest(BaseModel):
    transitions: list[SlideTransitionIn]


class SlideTransitionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slide_index: int
    timestamp_ms: int


class CreateShareLinkRequest(BaseModel):
    label: str | None = None
    can_view_progress: bool = True
    can_view_transcripts: bool = False
    can_view_feedback: bool = False
    expires_in_days: int | None = None  # convenience; server converts to expires_at

    @field_validator("expires_in_days")
    @classmethod
    def _positive_expiry(cls, value: int | None) -> int | None:
        if value is not None and value <= 0:
            raise ValueError("expires_in_days must be positive")
        return value


class ShareLinkOut(BaseModel):
    id: str
    token: str
    label: str | None
    can_view_progress: bool
    can_view_transcripts: bool
    can_view_feedback: bool
    created_at: datetime
    expires_at: datetime | None
    revoked: bool


class SharedFeedbackItemOut(BaseModel):
    criterion: str
    observation: str
    rationale: str
    repair: str


class SharedAttemptOut(BaseModel):
    session_id: str
    scenario: str
    created_at: datetime
    # Each of these is None when the link's corresponding permission is off —
    # not omitted, so a coach/manager viewer can see plainly what wasn't shared.
    wpm_overall: float | None = None
    filler_rate_per_100_words: float | None = None
    hedging_rate_per_100_words: float | None = None
    point_position_score: float | None = None
    transcript_text: str | None = None
    feedback_items: list[SharedFeedbackItemOut] | None = None


class SharedViewOut(BaseModel):
    label: str | None
    can_view_progress: bool
    can_view_transcripts: bool
    can_view_feedback: bool
    attempts: list[SharedAttemptOut]


class ExemplarOut(BaseModel):
    """§4.2 exemplar mode: a stronger version of the attempt + the delta."""

    original_text: str
    rewritten_text: str
    explanation: list[str]
    model_version: str
