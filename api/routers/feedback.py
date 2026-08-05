"""Feedback-item rating (§4.1 M6: "Every item has a thumbs up/down")."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.db import FeedbackItemRow, get_db
from api.schemas import FeedbackItemOut, RateFeedbackRequest

router = APIRouter(prefix="/feedback-items", tags=["feedback"])


@router.put("/{feedback_item_id}/rating", response_model=FeedbackItemOut)
def rate_feedback_item(
    feedback_item_id: str, body: RateFeedbackRequest, db: OrmSession = Depends(get_db)
) -> FeedbackItemRow:
    item = db.get(FeedbackItemRow, feedback_item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="feedback item not found")
    item.user_rating = body.useful
    db.commit()
    db.refresh(item)
    return item
