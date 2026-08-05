"""Private coach/manager share links (§4.2).

Two surfaces: an owner-authenticated-by-user-id management API
(`/users/{id}/share-links`, matching every other owner-scoped endpoint in
this codebase's no-auth-yet model) and one public, token-authenticated
read-only view (`/share/{token}`) that a coach or manager opens without any
account at all.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.db import AnalysisResult, FeedbackItemRow, PracticeSession, ShareLink, TranscriptWord, User, get_db
from api.schemas import (
    CreateShareLinkRequest,
    SharedAttemptOut,
    SharedFeedbackItemOut,
    SharedViewOut,
    ShareLinkOut,
)
from api.sharing import generate_token, is_link_active

router = APIRouter(tags=["sharing"])


def _share_link_out(link: ShareLink, now: datetime | None = None) -> ShareLinkOut:
    now = now or datetime.now(timezone.utc)
    return ShareLinkOut(
        id=link.id,
        token=link.token,
        label=link.label,
        can_view_progress=link.can_view_progress,
        can_view_transcripts=link.can_view_transcripts,
        can_view_feedback=link.can_view_feedback,
        created_at=link.created_at,
        expires_at=link.expires_at,
        revoked=not is_link_active(link.revoked_at, link.expires_at, now),
    )


@router.post("/users/{user_id}/share-links", response_model=ShareLinkOut, status_code=201)
def create_share_link(
    user_id: str, body: CreateShareLinkRequest, db: OrmSession = Depends(get_db)
) -> ShareLinkOut:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    expires_at = (
        datetime.now(timezone.utc) + timedelta(days=body.expires_in_days)
        if body.expires_in_days is not None
        else None
    )
    link = ShareLink(
        user_id=user_id,
        token=generate_token(),
        label=body.label,
        can_view_progress=body.can_view_progress,
        can_view_transcripts=body.can_view_transcripts,
        can_view_feedback=body.can_view_feedback,
        expires_at=expires_at,
    )
    db.add(link)
    db.commit()
    db.refresh(link)
    return _share_link_out(link)


@router.get("/users/{user_id}/share-links", response_model=list[ShareLinkOut])
def list_share_links(user_id: str, db: OrmSession = Depends(get_db)) -> list[ShareLinkOut]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    links = (
        db.query(ShareLink).filter_by(user_id=user_id).order_by(ShareLink.created_at.desc()).all()
    )
    return [_share_link_out(link) for link in links]


@router.delete("/users/{user_id}/share-links/{share_id}", status_code=204)
def revoke_share_link(user_id: str, share_id: str, db: OrmSession = Depends(get_db)) -> None:
    link = db.query(ShareLink).filter_by(id=share_id, user_id=user_id).one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="share link not found")
    link.revoked_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/share/{token}", response_model=SharedViewOut)
def get_shared_view(token: str, db: OrmSession = Depends(get_db)) -> SharedViewOut:
    link = db.query(ShareLink).filter_by(token=token).one_or_none()
    if link is None:
        raise HTTPException(status_code=404, detail="this share link doesn't exist")
    if not is_link_active(link.revoked_at, link.expires_at, datetime.now(timezone.utc)):
        raise HTTPException(status_code=410, detail="this share link has been revoked or expired")

    rows = (
        db.query(PracticeSession, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id == link.user_id)
        .order_by(AnalysisResult.created_at.asc())
        .all()
    )

    attempts: list[SharedAttemptOut] = []
    for session, analysis in rows:
        summary = analysis.metrics_summary
        transcript_text = None
        if link.can_view_transcripts:
            words = (
                db.query(TranscriptWord)
                .filter_by(session_id=session.id)
                .order_by(TranscriptWord.seq_index)
                .all()
            )
            transcript_text = " ".join(w.text for w in words)

        feedback_items = None
        if link.can_view_feedback:
            feedback_rows = (
                db.query(FeedbackItemRow)
                .filter_by(session_id=session.id)
                .order_by(FeedbackItemRow.rank)
                .all()
            )
            feedback_items = [
                SharedFeedbackItemOut(
                    criterion=f.criterion,
                    observation=f.observation,
                    rationale=f.rationale,
                    repair=f.repair,
                )
                for f in feedback_rows
            ]

        attempts.append(
            SharedAttemptOut(
                session_id=session.id,
                scenario=session.scenario,
                created_at=analysis.created_at,
                wpm_overall=summary.get("wpm_overall") if link.can_view_progress else None,
                filler_rate_per_100_words=(
                    summary.get("filler_rate_per_100_words") if link.can_view_progress else None
                ),
                hedging_rate_per_100_words=(
                    summary.get("hedging_rate_per_100_words") if link.can_view_progress else None
                ),
                point_position_score=(
                    (summary.get("point_position") or {}).get("score") if link.can_view_progress else None
                ),
                transcript_text=transcript_text,
                feedback_items=feedback_items,
            )
        )

    return SharedViewOut(
        label=link.label,
        can_view_progress=link.can_view_progress,
        can_view_transcripts=link.can_view_transcripts,
        can_view_feedback=link.can_view_feedback,
        attempts=attempts,
    )
