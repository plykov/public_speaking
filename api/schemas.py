"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


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
