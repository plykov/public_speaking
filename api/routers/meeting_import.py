"""Consented post-meeting analysis of Zoom/Teams/Meet recordings (§4.3).

An imported recording is analyzed through the exact same pipeline as any
other session — see `api.routers.sessions`'s `_persist_scoring`/
`_build_result_out`, reused here rather than duplicated, so an imported
attempt is indistinguishable from a live-recorded one everywhere else in
the app (Progress, share links, team analytics, ...). Only the recording
*fetch* is provider-specific; see `api/meeting_import.py` for what's real
(everything except the vendor call) vs. mocked (the vendor call itself).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.config import settings
from api.db import ConsentedRecordingImport, PracticeSession, TranscriptWord, User, get_db
from api.deps import get_llm, get_meeting_recordings, get_normalizer, get_object_store, get_stt
from api.meeting_import import MeetingRecordingProvider, RecordingNotFoundError
from api.pipeline.llm import ScenarioRubric
from api.pipeline.orchestrator import run_pipeline
from api.routers.sessions import _build_result_out, _media_key, _persist_scoring
from api.schemas import (
    AnalysisResultOut,
    ConsentedImportOut,
    ImportMeetingRecordingRequest,
    MeetingRecordingOut,
)
from api.storage import ObjectStore

router = APIRouter(tags=["meeting-import"])


@router.get("/meeting-recordings", response_model=list[MeetingRecordingOut])
def list_meeting_recordings(
    user_id: str,
    db: OrmSession = Depends(get_db),
    provider: MeetingRecordingProvider = Depends(get_meeting_recordings),
) -> list[MeetingRecordingOut]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    recordings = provider.list_available_recordings(user_id)
    return [
        MeetingRecordingOut(id=r.id, title=r.title, platform=r.platform, occurred_at=r.occurred_at)
        for r in recordings
    ]


@router.post("/meeting-recordings/{recording_id}/import", response_model=AnalysisResultOut, status_code=201)
def import_meeting_recording(
    recording_id: str,
    body: ImportMeetingRecordingRequest,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
    provider: MeetingRecordingProvider = Depends(get_meeting_recordings),
) -> AnalysisResultOut:
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    try:
        metadata = provider.get_recording_metadata(recording_id)
        raw_audio = provider.fetch_recording_bytes(recording_id)
    except RecordingNotFoundError as exc:
        raise HTTPException(status_code=404, detail=f"no such recording: {exc}") from exc

    session = PracticeSession(scenario="meeting_import", user_id=body.user_id, status="analyzing")
    db.add(session)
    db.flush()

    store.write_chunk(_media_key(session.id), 0, raw_audio)

    db.add(
        ConsentedRecordingImport(
            session_id=session.id,
            user_id=body.user_id,
            platform=metadata.platform,
            external_recording_id=metadata.id,
            title=metadata.title,
        )
    )

    try:
        result = run_pipeline(
            raw_audio,
            normalizer=get_normalizer(),
            stt_provider=get_stt(),
            llm_provider=get_llm(),
            rubric=ScenarioRubric(id=session.scenario),
            rubric_version=settings.rubric_version,
        )
    except Exception as exc:
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="analysis failed") from exc

    db.add_all(
        TranscriptWord(
            session_id=session.id,
            seq_index=i,
            text=w.text,
            start_ms=w.start_ms,
            end_ms=w.end_ms,
            confidence=w.confidence,
        )
        for i, w in enumerate(result.words)
    )

    analysis = _persist_scoring(db, session, result)
    db.commit()
    db.refresh(analysis)

    return _build_result_out(db, analysis)


@router.get("/users/{user_id}/meeting-imports", response_model=list[ConsentedImportOut])
def list_meeting_imports(user_id: str, db: OrmSession = Depends(get_db)) -> list[ConsentedRecordingImport]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    return (
        db.query(ConsentedRecordingImport)
        .filter_by(user_id=user_id)
        .order_by(ConsentedRecordingImport.consented_at.desc())
        .all()
    )
