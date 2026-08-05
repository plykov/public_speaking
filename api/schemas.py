"""Pydantic request/response models for the HTTP API."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class CreateSessionRequest(BaseModel):
    scenario: str = "general"


class SessionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    scenario: str
    status: str
    created_at: datetime


class UploadChunkResponse(BaseModel):
    bytes_received: int


class FeedbackItemOut(BaseModel):
    criterion: str
    observation: str
    rationale: str
    repair: str
    evidence_text: str
    evidence_start_ms: int
    evidence_end_ms: int


class DrillOut(BaseModel):
    id: str
    title: str
    prompt: str
    duration_minutes: str
    targets_criterion: str | None


class AnalysisResultOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    session_id: str
    rubric_version: str
    model_version: str
    transcript_text: str
    metrics_summary: dict
    feedback_items: list[FeedbackItemOut]
    drill: DrillOut
    created_at: datetime
