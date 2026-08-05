"""Voice AI roleplay, single persona, turn-based (§4.2).

Real audio in, real STT (`api.deps.get_stt`, mock in this environment for
the same reason Practice Studio's is), real turn-based conversation logic
— see `api.pipeline.roleplay` for what's genuinely real (STT reuse,
browser-native TTS) vs. mocked (persona reply generation, pending a real
LLM integration).

No raw audio is ever stored for a roleplay turn: it's transcribed
in-memory from the request body and discarded — only the transcript text
persists, tighter than the 30-day retention default elsewhere (§6.5),
because there's no product reason to keep it at all.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session as OrmSession

from api.db import RoleplaySession, RoleplayTurn, User, get_db
from api.deps import get_roleplay_llm, get_stt
from api.pipeline.roleplay import PERSONAS, RoleplayLLMProvider, RoleplayTurnData, get_persona
from api.pipeline.stt import STTProvider, TranscriptionError
from api.schemas import (
    CreateRoleplaySessionRequest,
    RoleplayPersonaOut,
    RoleplaySessionOut,
    RoleplayTurnOut,
    SubmitRoleplayTurnResponse,
)

router = APIRouter(prefix="/roleplay-sessions", tags=["roleplay"])
persona_router = APIRouter(tags=["roleplay"])


@persona_router.get("/roleplay-personas", response_model=list[RoleplayPersonaOut])
def list_personas() -> list[RoleplayPersonaOut]:
    return [RoleplayPersonaOut(id=p.id, name=p.name, role=p.role, description=p.description) for p in PERSONAS]


def _session_out(db: OrmSession, session: RoleplaySession) -> RoleplaySessionOut:
    turns = (
        db.query(RoleplayTurn)
        .filter_by(roleplay_session_id=session.id)
        .order_by(RoleplayTurn.turn_index)
        .all()
    )
    return RoleplaySessionOut(
        id=session.id,
        persona_id=session.persona_id,
        scenario=session.scenario,
        status=session.status,
        turns=[RoleplayTurnOut(turn_index=t.turn_index, speaker=t.speaker, text=t.text) for t in turns],
    )


@router.post("", response_model=RoleplaySessionOut, status_code=201)
def create_roleplay_session(
    body: CreateRoleplaySessionRequest, db: OrmSession = Depends(get_db)
) -> RoleplaySessionOut:
    persona = get_persona(body.persona_id)
    if persona is None:
        raise HTTPException(status_code=404, detail="unknown persona_id")
    if body.user_id is not None and db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    session = RoleplaySession(
        user_id=body.user_id, persona_id=persona.id, scenario=body.scenario, status="active"
    )
    db.add(session)
    db.flush()
    db.add(
        RoleplayTurn(
            roleplay_session_id=session.id, turn_index=0, speaker="persona", text=persona.opening_line
        )
    )
    db.commit()
    db.refresh(session)
    return _session_out(db, session)


@router.get("/{session_id}", response_model=RoleplaySessionOut)
def get_roleplay_session(session_id: str, db: OrmSession = Depends(get_db)) -> RoleplaySessionOut:
    session = db.get(RoleplaySession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="roleplay session not found")
    return _session_out(db, session)


@router.post("/{session_id}/turns", response_model=SubmitRoleplayTurnResponse)
async def submit_turn(
    session_id: str,
    request: Request,
    db: OrmSession = Depends(get_db),
    stt: STTProvider = Depends(get_stt),
    roleplay_llm: RoleplayLLMProvider = Depends(get_roleplay_llm),
) -> SubmitRoleplayTurnResponse:
    session = db.get(RoleplaySession, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="roleplay session not found")
    if session.status != "active":
        raise HTTPException(status_code=400, detail="this roleplay session has already ended")
    persona = get_persona(session.persona_id)

    audio = await request.body()
    try:
        words = stt.transcribe(audio, sample_rate=16000)
    except TranscriptionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    user_text = " ".join(w.text for w in words)

    existing_turns = (
        db.query(RoleplayTurn)
        .filter_by(roleplay_session_id=session_id)
        .order_by(RoleplayTurn.turn_index)
        .all()
    )
    next_index = existing_turns[-1].turn_index + 1 if existing_turns else 0
    history = [RoleplayTurnData(speaker=t.speaker, text=t.text) for t in existing_turns]
    history.append(RoleplayTurnData(speaker="user", text=user_text))
    user_turn_count = sum(1 for t in history if t.speaker == "user")

    user_turn = RoleplayTurn(
        roleplay_session_id=session_id, turn_index=next_index, speaker="user", text=user_text
    )
    db.add(user_turn)

    reply = roleplay_llm.reply(persona, history, user_turn_count)
    persona_turn = RoleplayTurn(
        roleplay_session_id=session_id, turn_index=next_index + 1, speaker="persona", text=reply.text
    )
    db.add(persona_turn)

    if reply.is_closing:
        session.status = "completed"

    db.commit()

    return SubmitRoleplayTurnResponse(
        session_status=session.status,
        new_turns=[
            RoleplayTurnOut(turn_index=user_turn.turn_index, speaker="user", text=user_turn.text),
            RoleplayTurnOut(turn_index=persona_turn.turn_index, speaker="persona", text=persona_turn.text),
        ],
    )
