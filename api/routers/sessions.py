"""Session lifecycle: create → chunked upload → analyze → fetch result → delete.

`/analyze` runs the pipeline synchronously in-process. In production
this is a Celery/Arq task off the request path (§6.1); the synchronous
call here is a deliberate MVP simplification — the seam
(`api.pipeline.orchestrator.run_pipeline`) is the same function a
worker would call, so swapping in a queue later doesn't change this
module's logic, only how it's invoked.
"""

from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from api.db import AnalysisResult, MediaAsset, PracticeSession, get_db
from api.deps import get_llm, get_normalizer, get_object_store, get_stt
from api.pipeline.llm import ScenarioRubric
from api.pipeline.orchestrator import run_pipeline
from api.schemas import AnalysisResultOut, CreateSessionRequest, SessionOut, UploadChunkResponse
from api.storage import ObjectStore, UploadConflict
from api.config import settings

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _media_key(session_id: str) -> str:
    return f"{session_id}/audio.raw"


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: CreateSessionRequest, db: OrmSession = Depends(get_db)) -> PracticeSession:
    session = PracticeSession(scenario=body.scenario, status="created")
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def _get_session_or_404(session_id: str, db: OrmSession) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.get("/{session_id}", response_model=SessionOut)
def get_session(session_id: str, db: OrmSession = Depends(get_db)) -> PracticeSession:
    return _get_session_or_404(session_id, db)


@router.post("/{session_id}/media", response_model=UploadChunkResponse)
async def upload_chunk(
    session_id: str,
    request: Request,
    offset: int = 0,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> UploadChunkResponse:
    """Resumable chunked upload (§4.1 M2). Retry the same offset safely;
    call GET /media/status first to resume after a dropped connection."""
    session = _get_session_or_404(session_id, db)
    key = _media_key(session_id)

    data = await request.body()
    try:
        status = store.write_chunk(key, offset, data)
    except UploadConflict as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    existing = db.query(MediaAsset).filter_by(session_id=session_id).one_or_none()
    if existing is None:
        db.add(MediaAsset(session_id=session_id, storage_key=key))
    session.status = "uploading"
    db.commit()

    return UploadChunkResponse(bytes_received=status.bytes_received)


@router.get("/{session_id}/media/status", response_model=UploadChunkResponse)
def upload_status(
    session_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> UploadChunkResponse:
    _get_session_or_404(session_id, db)
    status = store.status(_media_key(session_id))
    return UploadChunkResponse(bytes_received=status.bytes_received)


@router.post("/{session_id}/analyze", response_model=AnalysisResultOut)
def analyze_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> AnalysisResult:
    session = _get_session_or_404(session_id, db)
    media = db.query(MediaAsset).filter_by(session_id=session_id).one_or_none()
    if media is None:
        raise HTTPException(status_code=400, detail="no media uploaded for this session")

    raw_audio = store.read(media.storage_key)

    session.status = "analyzing"
    db.commit()

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
        # Processing state surfaced honestly (§6.7) rather than left "analyzing" forever.
        session.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail="analysis failed") from exc

    analysis = AnalysisResult(
        session_id=session_id,
        rubric_version=result.rubric_version,
        model_version=result.model_version,
        transcript_text=result.transcript_text,
        metrics_summary=result.metrics.summary,
        metric_events=[asdict(e) for e in result.metrics.events],
        feedback_items=[asdict(item) for item in result.feedback_items],
        drill=asdict(result.drill),
    )
    db.add(analysis)
    session.status = "complete"
    db.commit()
    db.refresh(analysis)
    return analysis


@router.get("/{session_id}/result", response_model=AnalysisResultOut)
def get_result(session_id: str, db: OrmSession = Depends(get_db)) -> AnalysisResult:
    _get_session_or_404(session_id, db)
    result = (
        db.query(AnalysisResult)
        .filter_by(session_id=session_id)
        .order_by(AnalysisResult.created_at.desc())
        .first()
    )
    if result is None:
        raise HTTPException(status_code=404, detail="no analysis for this session yet")
    return result


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> None:
    """One-click session delete (§4.1 M11, §6.5)."""
    session = _get_session_or_404(session_id, db)
    store.delete(_media_key(session_id))
    db.query(AnalysisResult).filter_by(session_id=session_id).delete()
    db.query(MediaAsset).filter_by(session_id=session_id).delete()
    db.delete(session)
    db.commit()
