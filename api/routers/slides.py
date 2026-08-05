"""Slide/PDF upload with slide-linked transcript (§4.2).

A session can have one PDF slide deck. The presenter marks slide
transitions during/after the recording (elapsed-ms timestamps, same clock
as `TranscriptWord.start_ms`); the frontend computes which slide was live
at any transcript timestamp from that list — kept client-side rather than
joined server-side so this feature never touches the transcript/evidence
tables the deterministic pipeline owns.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as OrmSession

from api.db import PracticeSession, SlideDeck, SlideTransition, get_db
from api.deps import get_object_store
from api.schemas import (
    SlideDeckOut,
    SlideTransitionOut,
    UpsertSlideTransitionsRequest,
)
from api.slides import InvalidPdfError, count_pages, render_thumbnails, slide_deck_key, slide_thumbnail_key
from api.storage import ObjectStore

router = APIRouter(prefix="/sessions", tags=["slides"])


def _get_session_or_404(session_id: str, db: OrmSession) -> PracticeSession:
    session = db.get(PracticeSession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="session not found")
    return session


@router.post("/{session_id}/slides", response_model=SlideDeckOut, status_code=201)
async def upload_slides(
    session_id: str,
    request: Request,
    filename: str = "slides.pdf",
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> SlideDeckOut:
    """Replace this session's slide deck with the uploaded PDF."""
    _get_session_or_404(session_id, db)
    pdf_bytes = await request.body()

    try:
        page_count = count_pages(pdf_bytes)
        thumbnails = render_thumbnails(pdf_bytes)
    except InvalidPdfError as exc:
        raise HTTPException(status_code=422, detail=f"not a readable PDF: {exc}") from exc

    existing = db.query(SlideDeck).filter_by(session_id=session_id).one_or_none()
    if existing is not None:
        store.delete(existing.storage_key)
        for page in range(existing.page_count):
            store.delete(slide_thumbnail_key(session_id, page))
        db.delete(existing)
        db.flush()

    pdf_key = slide_deck_key(session_id)
    store.write_chunk(pdf_key, 0, pdf_bytes)
    for i, thumbnail in enumerate(thumbnails):
        store.write_chunk(slide_thumbnail_key(session_id, i), 0, thumbnail)

    deck = SlideDeck(session_id=session_id, filename=filename, page_count=page_count, storage_key=pdf_key)
    db.add(deck)
    db.commit()

    return SlideDeckOut(
        filename=deck.filename,
        page_count=deck.page_count,
        thumbnail_urls=[f"/sessions/{session_id}/slides/{i}/thumbnail" for i in range(deck.page_count)],
    )


@router.get("/{session_id}/slides", response_model=SlideDeckOut)
def get_slides(session_id: str, db: OrmSession = Depends(get_db)) -> SlideDeckOut:
    _get_session_or_404(session_id, db)
    deck = db.query(SlideDeck).filter_by(session_id=session_id).one_or_none()
    if deck is None:
        raise HTTPException(status_code=404, detail="no slide deck uploaded for this session yet")
    return SlideDeckOut(
        filename=deck.filename,
        page_count=deck.page_count,
        thumbnail_urls=[f"/sessions/{session_id}/slides/{i}/thumbnail" for i in range(deck.page_count)],
    )


@router.get("/{session_id}/slides/{page_index}/thumbnail")
def get_slide_thumbnail(
    session_id: str,
    page_index: int,
    db: OrmSession = Depends(get_db),
    store: ObjectStore = Depends(get_object_store),
) -> Response:
    _get_session_or_404(session_id, db)
    deck = db.query(SlideDeck).filter_by(session_id=session_id).one_or_none()
    if deck is None or not (0 <= page_index < deck.page_count):
        raise HTTPException(status_code=404, detail="no such slide")
    return Response(content=store.read(slide_thumbnail_key(session_id, page_index)), media_type="image/png")


@router.put("/{session_id}/slide-transitions", response_model=list[SlideTransitionOut])
def upsert_slide_transitions(
    session_id: str, body: UpsertSlideTransitionsRequest, db: OrmSession = Depends(get_db)
) -> list[SlideTransition]:
    """Replace the full set of transitions for this session (a retake
    re-marks slides from scratch, same "replace, don't append" pattern as
    §4.1 M8's transcript correction)."""
    _get_session_or_404(session_id, db)
    db.query(SlideTransition).filter_by(session_id=session_id).delete()
    rows = [
        SlideTransition(session_id=session_id, slide_index=t.slide_index, timestamp_ms=t.timestamp_ms)
        for t in body.transitions
    ]
    db.add_all(rows)
    db.commit()
    return sorted(rows, key=lambda r: r.timestamp_ms)


@router.get("/{session_id}/slide-transitions", response_model=list[SlideTransitionOut])
def get_slide_transitions(session_id: str, db: OrmSession = Depends(get_db)) -> list[SlideTransition]:
    _get_session_or_404(session_id, db)
    return (
        db.query(SlideTransition)
        .filter_by(session_id=session_id)
        .order_by(SlideTransition.timestamp_ms.asc())
        .all()
    )
