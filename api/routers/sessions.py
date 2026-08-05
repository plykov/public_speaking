"""Session lifecycle: create → chunked upload → analyze → fetch result → delete.

`/analyze` runs the pipeline synchronously in-process. In production
this is a Celery/Arq task off the request path (§6.1); the synchronous
call here is a deliberate MVP simplification — the seam
(`api.pipeline.orchestrator.run_pipeline`) is the same function a
worker would call, so swapping in a queue later doesn't change this
module's logic, only how it's invoked.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from api.config import settings
from api.db import (
    AnalysisResult,
    FeedbackItemRow,
    L1Profile,
    MediaAsset,
    MetricEventRow,
    PracticeSession,
    TranscriptCorrection,
    TranscriptWord,
    User,
    get_db,
)
from api.deps import get_llm, get_normalizer, get_object_store, get_stt
from api.lifecycle import delete_session_data
from api.pipeline.llm import ScenarioRubric
from api.pipeline.orchestrator import PipelineResult, run_pipeline, score_words
from api.schemas import (
    AnalysisResultOut,
    CreateSessionRequest,
    DrillOut,
    FeedbackItemOut,
    SessionOut,
    TranscriptWordOut,
    UpdateTranscriptRequest,
    UploadChunkResponse,
)
from api.storage import ObjectStore, UploadConflict
from metrics.models import Word

router = APIRouter(prefix="/sessions", tags=["sessions"])


def _media_key(session_id: str) -> str:
    return f"{session_id}/audio.raw"


def _get_session_or_404(session_id: str, db: OrmSession) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("", response_model=SessionOut, status_code=201)
def create_session(body: CreateSessionRequest, db: OrmSession = Depends(get_db)) -> PracticeSession:
    if body.user_id is not None and db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    if body.parent_session_id is not None and db.get(PracticeSession, body.parent_session_id) is None:
        raise HTTPException(status_code=404, detail="parent_session_id not found")

    session = PracticeSession(
        scenario=body.scenario,
        user_id=body.user_id,
        parent_session_id=body.parent_session_id,
        status="created",
    )
    db.add(session)
    db.commit()
    db.refresh(session)
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


def _build_result_out(db: OrmSession, analysis: AnalysisResult) -> AnalysisResultOut:
    words = (
        db.query(TranscriptWord)
        .filter_by(session_id=analysis.session_id)
        .order_by(TranscriptWord.seq_index)
        .all()
    )
    feedback_rows = (
        db.query(FeedbackItemRow)
        .filter_by(session_id=analysis.session_id)
        .order_by(FeedbackItemRow.rank)
        .all()
    )
    return AnalysisResultOut(
        session_id=analysis.session_id,
        rubric_version=analysis.rubric_version,
        model_version=analysis.model_version,
        transcript_text=" ".join(w.text for w in words),
        metrics_summary=analysis.metrics_summary,
        feedback_items=[
            FeedbackItemOut(
                id=f.id,
                criterion=f.criterion,
                observation=f.observation,
                rationale=f.rationale,
                repair=f.repair,
                evidence_text=f.evidence_text,
                evidence_start_ms=f.evidence_start_ms,
                evidence_end_ms=f.evidence_end_ms,
                user_rating=f.user_rating,
            )
            for f in feedback_rows
        ],
        drill=DrillOut(
            id=analysis.drill_id,
            title=analysis.drill_title,
            prompt=analysis.drill_prompt,
            duration_minutes=analysis.drill_duration_minutes,
            targets_criterion=analysis.drill_targets_criterion,
        ),
        created_at=analysis.created_at,
    )


def _persist_scoring(db: OrmSession, session: PracticeSession, result: PipelineResult) -> AnalysisResult:
    """Replace this session's metric_events/feedback_items/analysis_result
    (never appends — one attempt's derived data at a time). Does not touch
    `TranscriptWord`: callers write the transcript themselves, since a
    first-pass analysis inserts new rows while a transcript correction
    (§4.1 M8) updates existing ones in place."""
    db.query(MetricEventRow).filter_by(session_id=session.id).delete()
    db.query(FeedbackItemRow).filter_by(session_id=session.id).delete()
    db.query(AnalysisResult).filter_by(session_id=session.id).delete()

    db.add_all(
        MetricEventRow(
            session_id=session.id,
            type=e.type,
            start_ms=e.start_ms,
            end_ms=e.end_ms,
            value=e.value,
        )
        for e in result.metrics.events
    )
    db.add_all(
        FeedbackItemRow(
            session_id=session.id,
            rank=i,
            criterion=item.criterion,
            observation=item.observation,
            rationale=item.rationale,
            repair=item.repair,
            evidence_text=item.evidence_text,
            evidence_start_ms=item.evidence_start_ms,
            evidence_end_ms=item.evidence_end_ms,
        )
        for i, item in enumerate(result.feedback_items)
    )
    analysis = AnalysisResult(
        session_id=session.id,
        rubric_version=result.rubric_version,
        model_version=result.model_version,
        metrics_summary=result.metrics.summary,
        drill_id=result.drill.id,
        drill_title=result.drill.title,
        drill_prompt=result.drill.prompt,
        drill_duration_minutes=result.drill.duration_minutes,
        drill_targets_criterion=result.drill.targets_criterion,
    )
    db.add(analysis)
    session.status = "complete"
    return analysis


@router.post("/{session_id}/analyze", response_model=AnalysisResultOut)
def analyze_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> AnalysisResultOut:
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

    # Wipe any prior attempt's transcript for this session (re-analysis is
    # a replace, not an append) before writing the fresh transcription.
    db.query(TranscriptWord).filter_by(session_id=session_id).delete()
    db.add_all(
        TranscriptWord(
            session_id=session_id,
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


@router.get("/{session_id}/result", response_model=AnalysisResultOut)
def get_result(session_id: str, db: OrmSession = Depends(get_db)) -> AnalysisResultOut:
    _get_session_or_404(session_id, db)
    analysis = db.query(AnalysisResult).filter_by(session_id=session_id).one_or_none()
    if analysis is None:
        raise HTTPException(status_code=404, detail="no analysis for this session yet")
    return _build_result_out(db, analysis)


@router.get("/{session_id}/transcript", response_model=list[TranscriptWordOut])
def get_transcript(session_id: str, db: OrmSession = Depends(get_db)) -> list[TranscriptWord]:
    """§4.1 M8: the editable word list. Empty until the session has been analyzed."""
    _get_session_or_404(session_id, db)
    return (
        db.query(TranscriptWord)
        .filter_by(session_id=session_id)
        .order_by(TranscriptWord.seq_index)
        .all()
    )


@router.put("/{session_id}/transcript", response_model=AnalysisResultOut)
def update_transcript(
    session_id: str, body: UpdateTranscriptRequest, db: OrmSession = Depends(get_db)
) -> AnalysisResultOut:
    """§4.1 M8: correct ASR errors and re-run scoring on the corrected text.

    Every changed word is logged as a `TranscriptCorrection` — an ASR
    quality signal per L1 background (§6.6) — before re-scoring. Only the
    words themselves are user-editable; timestamps and confidence are
    carried over unchanged from the original transcription, so evidence
    spans in the new feedback stay anchored to real audio positions.
    """
    session = _get_session_or_404(session_id, db)
    existing = (
        db.query(TranscriptWord)
        .filter_by(session_id=session_id)
        .order_by(TranscriptWord.seq_index)
        .all()
    )
    if not existing:
        raise HTTPException(status_code=400, detail="session has no transcript yet")
    if len(body.words) != len(existing):
        raise HTTPException(
            status_code=400,
            detail=f"expected {len(existing)} words, got {len(body.words)} — "
            "corrections must match the original word count",
        )

    l1_first_language = None
    if session.user_id:
        profile = db.query(L1Profile).filter_by(user_id=session.user_id).one_or_none()
        if profile:
            l1_first_language = profile.first_language

    corrected_words: list[Word] = []
    for row, corrected_text in zip(existing, body.words):
        if corrected_text != row.text:
            db.add(
                TranscriptCorrection(
                    session_id=session_id,
                    seq_index=row.seq_index,
                    original_text=row.text,
                    corrected_text=corrected_text,
                    l1_first_language=l1_first_language,
                )
            )
            row.text = corrected_text
        corrected_words.append(
            Word(
                text=row.text,
                start_ms=row.start_ms,
                end_ms=row.end_ms,
                confidence=row.confidence,
            )
        )

    result = score_words(
        corrected_words,
        llm_provider=get_llm(),
        rubric=ScenarioRubric(id=session.scenario),
        rubric_version=settings.rubric_version,
    )
    analysis = _persist_scoring(db, session, result)
    db.commit()
    db.refresh(analysis)

    return _build_result_out(db, analysis)


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: str,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> None:
    """One-click session delete (§4.1 M11, §6.5)."""
    _get_session_or_404(session_id, db)
    delete_session_data(db, store, session_id)
    db.commit()
