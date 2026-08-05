"""Team workspaces (§4.3).

**No authorization is enforced here.** This app has no auth/session
system at all — `User` (api/db.py) is an anonymous, device-scoped id with
no login. Team membership and roles are tracked and shown in the UI, but
any caller who knows a `team_id` and a `user_id` can currently call
"admin" actions; there is no session to check a caller's identity
against. A real deployment needs an auth system before this is a security
boundary, not just a data model — stated plainly rather than pretending
role checks exist where they don't.
"""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as OrmSession

from api.analytics import AttemptMetrics, compute_team_analytics
from api.db import (
    AnalysisResult,
    PracticeSession,
    Team,
    TeamInvite,
    TeamMembership,
    TeamRubric,
    TeamScenario,
    User,
    get_db,
)
from api.schemas import (
    AcceptInviteRequest,
    CreateTeamInviteRequest,
    CreateTeamRequest,
    CreateTeamRubricRequest,
    CreateTeamScenarioRequest,
    MemberAnalyticsOut,
    TeamAnalyticsOut,
    TeamInviteOut,
    TeamMemberOut,
    TeamOut,
    TeamRubricOut,
    TeamScenarioOut,
    TeamWithMembersOut,
    UpdateMemberRoleRequest,
)
from api.sharing import generate_token

router = APIRouter(tags=["teams"])


def _get_team_or_404(team_id: str, db: OrmSession) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise HTTPException(status_code=404, detail="team not found")
    return team


def _team_with_members_out(db: OrmSession, team: Team) -> TeamWithMembersOut:
    memberships = db.query(TeamMembership).filter_by(team_id=team.id).order_by(TeamMembership.joined_at).all()
    return TeamWithMembersOut(
        id=team.id,
        name=team.name,
        created_at=team.created_at,
        members=[TeamMemberOut(user_id=m.user_id, role=m.role, joined_at=m.joined_at) for m in memberships],
    )


@router.post("/teams", response_model=TeamWithMembersOut, status_code=201)
def create_team(body: CreateTeamRequest, db: OrmSession = Depends(get_db)) -> TeamWithMembersOut:
    if db.get(User, body.admin_user_id) is None:
        raise HTTPException(status_code=404, detail="admin_user_id not found")

    team = Team(name=body.name)
    db.add(team)
    db.flush()
    db.add(TeamMembership(team_id=team.id, user_id=body.admin_user_id, role="admin"))
    db.commit()
    db.refresh(team)
    return _team_with_members_out(db, team)


@router.get("/teams/{team_id}", response_model=TeamWithMembersOut)
def get_team(team_id: str, db: OrmSession = Depends(get_db)) -> TeamWithMembersOut:
    team = _get_team_or_404(team_id, db)
    return _team_with_members_out(db, team)


@router.get("/users/{user_id}/teams", response_model=list[TeamOut])
def list_teams_for_user(user_id: str, db: OrmSession = Depends(get_db)) -> list[Team]:
    if db.get(User, user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")
    team_ids = [m.team_id for m in db.query(TeamMembership).filter_by(user_id=user_id).all()]
    if not team_ids:
        return []
    return db.query(Team).filter(Team.id.in_(team_ids)).order_by(Team.created_at).all()


@router.delete("/teams/{team_id}/members/{user_id}", status_code=204)
def remove_team_member(team_id: str, user_id: str, db: OrmSession = Depends(get_db)) -> None:
    _get_team_or_404(team_id, db)
    membership = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user_id).one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="this user is not a member of this team")
    db.delete(membership)
    db.commit()


@router.put("/teams/{team_id}/members/{user_id}/role", response_model=TeamMemberOut)
def update_member_role(
    team_id: str, user_id: str, body: UpdateMemberRoleRequest, db: OrmSession = Depends(get_db)
) -> TeamMemberOut:
    _get_team_or_404(team_id, db)
    membership = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user_id).one_or_none()
    if membership is None:
        raise HTTPException(status_code=404, detail="this user is not a member of this team")
    membership.role = body.role
    db.commit()
    return TeamMemberOut(user_id=membership.user_id, role=membership.role, joined_at=membership.joined_at)


@router.post("/teams/{team_id}/invites", response_model=TeamInviteOut, status_code=201)
def create_team_invite(
    team_id: str, body: CreateTeamInviteRequest, db: OrmSession = Depends(get_db)
) -> TeamInviteOut:
    _get_team_or_404(team_id, db)
    invite = TeamInvite(team_id=team_id, token=generate_token(), role=body.role)
    db.add(invite)
    db.commit()
    return TeamInviteOut(token=invite.token, team_id=team_id, role=invite.role, accepted=False)


@router.post("/team-invites/{token}/accept", response_model=TeamMemberOut)
def accept_team_invite(
    token: str, body: AcceptInviteRequest, db: OrmSession = Depends(get_db)
) -> TeamMemberOut:
    invite = db.query(TeamInvite).filter_by(token=token).one_or_none()
    if invite is None:
        raise HTTPException(status_code=404, detail="this invite doesn't exist")
    if invite.accepted_at is not None:
        raise HTTPException(status_code=410, detail="this invite has already been used")
    if db.get(User, body.user_id) is None:
        raise HTTPException(status_code=404, detail="user not found")

    existing = db.query(TeamMembership).filter_by(team_id=invite.team_id, user_id=body.user_id).one_or_none()
    if existing is not None:
        raise HTTPException(status_code=409, detail="this user is already a member of this team")

    membership = TeamMembership(team_id=invite.team_id, user_id=body.user_id, role=invite.role)
    db.add(membership)
    invite.accepted_at = datetime.now(timezone.utc)
    invite.accepted_by_user_id = body.user_id
    db.commit()
    return TeamMemberOut(user_id=membership.user_id, role=membership.role, joined_at=membership.joined_at)


@router.post("/teams/{team_id}/scenarios", response_model=TeamScenarioOut, status_code=201)
def create_team_scenario(
    team_id: str, body: CreateTeamScenarioRequest, db: OrmSession = Depends(get_db)
) -> TeamScenario:
    """§4.3 custom scenarios — genuinely usable: the title/prompt is shown
    to team members as a real practice prompt in Practice Studio, no LLM
    or mock involved."""
    _get_team_or_404(team_id, db)
    scenario = TeamScenario(team_id=team_id, title=body.title, prompt=body.prompt)
    db.add(scenario)
    db.commit()
    db.refresh(scenario)
    return scenario


@router.get("/teams/{team_id}/scenarios", response_model=list[TeamScenarioOut])
def list_team_scenarios(team_id: str, db: OrmSession = Depends(get_db)) -> list[TeamScenario]:
    _get_team_or_404(team_id, db)
    return db.query(TeamScenario).filter_by(team_id=team_id).order_by(TeamScenario.created_at).all()


@router.delete("/teams/{team_id}/scenarios/{scenario_id}", status_code=204)
def delete_team_scenario(team_id: str, scenario_id: str, db: OrmSession = Depends(get_db)) -> None:
    _get_team_or_404(team_id, db)
    scenario = db.query(TeamScenario).filter_by(id=scenario_id, team_id=team_id).one_or_none()
    if scenario is None:
        raise HTTPException(status_code=404, detail="scenario not found")
    db.delete(scenario)
    db.commit()


@router.post("/teams/{team_id}/rubrics", response_model=TeamRubricOut, status_code=201)
def create_team_rubric(
    team_id: str, body: CreateTeamRubricRequest, db: OrmSession = Depends(get_db)
) -> TeamRubric:
    """§4.3 custom rubrics — the criteria list is stored and manageable for
    real, but **not yet consumed by scoring**: `MockLLMRubricProvider`
    (api/pipeline/llm.py) is rule-based over deterministic metrics and
    never reads `ScenarioRubric.criteria` at all, mock or custom. Wiring a
    team's custom criteria into what gets judged is only meaningful once a
    real LLM provider exists behind that same seam — stated here rather
    than faking a cosmetic effect."""
    _get_team_or_404(team_id, db)
    rubric = TeamRubric(team_id=team_id, name=body.name, criteria=body.criteria)
    db.add(rubric)
    db.commit()
    db.refresh(rubric)
    return rubric


@router.get("/teams/{team_id}/rubrics", response_model=list[TeamRubricOut])
def list_team_rubrics(team_id: str, db: OrmSession = Depends(get_db)) -> list[TeamRubric]:
    _get_team_or_404(team_id, db)
    return db.query(TeamRubric).filter_by(team_id=team_id).order_by(TeamRubric.created_at).all()


@router.delete("/teams/{team_id}/rubrics/{rubric_id}", status_code=204)
def delete_team_rubric(team_id: str, rubric_id: str, db: OrmSession = Depends(get_db)) -> None:
    _get_team_or_404(team_id, db)
    rubric = db.query(TeamRubric).filter_by(id=rubric_id, team_id=team_id).one_or_none()
    if rubric is None:
        raise HTTPException(status_code=404, detail="rubric not found")
    db.delete(rubric)
    db.commit()


@router.get("/teams/{team_id}/analytics", response_model=TeamAnalyticsOut)
def get_team_analytics(team_id: str, db: OrmSession = Depends(get_db)) -> TeamAnalyticsOut:
    """§4.3 manager aggregate analytics — recording access off by default.

    "Off by default" is absolute here, not a toggle defaulted to off:
    nothing in this response can ever be a recording, transcript, or
    feedback item — see `api.analytics`'s docstring for why that's a
    schema-level guarantee, not a permission check that could be
    misconfigured.
    """
    _get_team_or_404(team_id, db)
    member_ids = [m.user_id for m in db.query(TeamMembership).filter_by(team_id=team_id).all()]

    rows = (
        db.query(PracticeSession, AnalysisResult)
        .join(AnalysisResult, AnalysisResult.session_id == PracticeSession.id)
        .filter(PracticeSession.user_id.in_(member_ids))
        .all()
        if member_ids
        else []
    )
    attempts = [
        AttemptMetrics(
            user_id=session.user_id,
            wpm_overall=analysis.metrics_summary.get("wpm_overall"),
            filler_rate_per_100_words=analysis.metrics_summary.get("filler_rate_per_100_words"),
            hedging_rate_per_100_words=analysis.metrics_summary.get("hedging_rate_per_100_words"),
            point_position_score=(analysis.metrics_summary.get("point_position") or {}).get("score"),
        )
        for session, analysis in rows
    ]

    result = compute_team_analytics(member_ids, attempts)
    return TeamAnalyticsOut(
        member_count=result.member_count,
        total_attempts=result.total_attempts,
        avg_wpm=result.avg_wpm,
        avg_filler_rate=result.avg_filler_rate,
        avg_hedging_rate=result.avg_hedging_rate,
        avg_point_position_score=result.avg_point_position_score,
        per_member=[
            MemberAnalyticsOut(
                user_id=m.user_id,
                attempt_count=m.attempt_count,
                avg_wpm=m.avg_wpm,
                avg_filler_rate=m.avg_filler_rate,
                avg_hedging_rate=m.avg_hedging_rate,
                avg_point_position_score=m.avg_point_position_score,
            )
            for m in result.per_member
        ],
    )
