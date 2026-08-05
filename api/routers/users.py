"""Onboarding (§4.1 M1): anonymous user + L1 profile.

No auth — a User row is created on demand and the client holds the id
(e.g. localStorage). L1Profile captures first language and self-declared
English confidence for onboarding copy and calibration only; nothing in
api/pipeline/llm.py or metrics/report.py reads this table.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.db import L1Profile, User, get_db
from api.schemas import CreateL1ProfileRequest, L1ProfileOut, UserOut

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserOut, status_code=201)
def create_user(db: OrmSession = Depends(get_db)) -> User:
    user = User()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/{user_id}", response_model=UserOut)
def get_user(user_id: str, db: OrmSession = Depends(get_db)) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")
    return user


@router.put("/{user_id}/l1-profile", response_model=L1ProfileOut)
def upsert_l1_profile(
    user_id: str, body: CreateL1ProfileRequest, db: OrmSession = Depends(get_db)
) -> L1Profile:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="user not found")

    profile = db.query(L1Profile).filter_by(user_id=user_id).one_or_none()
    if profile is None:
        profile = L1Profile(user_id=user_id, **body.model_dump())
        db.add(profile)
    else:
        profile.first_language = body.first_language
        profile.self_declared_confidence = body.self_declared_confidence
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/{user_id}/l1-profile", response_model=L1ProfileOut)
def get_l1_profile(user_id: str, db: OrmSession = Depends(get_db)) -> L1Profile:
    profile = db.query(L1Profile).filter_by(user_id=user_id).one_or_none()
    if profile is None:
        raise HTTPException(status_code=404, detail="no L1 profile for this user yet")
    return profile
