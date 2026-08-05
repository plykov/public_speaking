"""SCIM 2.0 user provisioning (§4.3 — the other half of "SSO/SCIM").

Unlike SSO (see `api/sso.py`), this one has **no vendor-credential gap**:
in SCIM, *we* are the server a real identity provider (Okta, Azure AD,
OneLogin, ...) calls into to provision/deprovision users on a team — not
a client calling out to someone else's API. Implementing the protocol
ourselves, correctly, is the whole deliverable; there's nothing left to
mock. This is a deliberately minimal but spec-correct (RFC 7643/7644)
subset: User resource list/create/read/deactivate/delete, scoped to one
team. No Groups resource, no filtering/pagination beyond returning
everything — a real deployment would add those as needed; the shape
here is real and IdP-compatible for the operations it covers.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session as OrmSession

from api.audit import log_audit_event
from api.db import Team, TeamMembership, User, get_db

router = APIRouter(prefix="/scim/v2/Teams", tags=["scim"])

_USER_SCHEMA = "urn:ietf:params:scim:schemas:core:2.0:User"
_LIST_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:ListResponse"
_ERROR_SCHEMA = "urn:ietf:params:scim:api:messages:2.0:Error"


def _scim_error(status_code: int, detail: str) -> HTTPException:
    return HTTPException(
        status_code=status_code,
        detail={"schemas": [_ERROR_SCHEMA], "status": str(status_code), "detail": detail},
    )


def _get_team_or_404(team_id: str, db: OrmSession) -> Team:
    team = db.get(Team, team_id)
    if team is None:
        raise _scim_error(404, "team not found")
    return team


def _user_resource(user: User, active: bool) -> dict:
    return {
        "schemas": [_USER_SCHEMA],
        "id": user.id,
        "externalId": user.external_id,
        "userName": user.external_id or user.email or user.id,
        "emails": [{"value": user.email, "primary": True}] if user.email else [],
        "active": active,
    }


@router.get("/{team_id}/Users")
def list_scim_users(team_id: str, db: OrmSession = Depends(get_db)) -> dict:
    _get_team_or_404(team_id, db)
    memberships = db.query(TeamMembership).filter_by(team_id=team_id).all()
    users = [db.get(User, m.user_id) for m in memberships]
    resources = [_user_resource(u, active=True) for u in users if u is not None]
    return {"schemas": [_LIST_SCHEMA], "totalResults": len(resources), "Resources": resources}


@router.post("/{team_id}/Users", status_code=201)
async def create_scim_user(team_id: str, request: Request, db: OrmSession = Depends(get_db)) -> dict:
    _get_team_or_404(team_id, db)
    body = await request.json()
    external_id = body.get("externalId") or body.get("userName")
    if not external_id:
        raise _scim_error(400, "userName or externalId is required")
    email = None
    emails = body.get("emails") or []
    if emails:
        email = emails[0].get("value")

    user = db.query(User).filter_by(external_id=external_id).one_or_none()
    if user is None:
        user = User(external_id=external_id, email=email)
        db.add(user)
        db.flush()

    existing = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user.id).one_or_none()
    if existing is not None:
        raise _scim_error(409, "user is already provisioned on this team")

    db.add(TeamMembership(team_id=team_id, user_id=user.id, role="member"))
    log_audit_event(
        db,
        team_id=team_id,
        actor_user_id=None,
        action="team.scim.provision",
        target_type="user",
        target_id=user.id,
        detail={"external_id": external_id},
    )
    db.commit()
    return _user_resource(user, active=True)


@router.get("/{team_id}/Users/{user_id}")
def get_scim_user(team_id: str, user_id: str, db: OrmSession = Depends(get_db)) -> dict:
    _get_team_or_404(team_id, db)
    membership = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user_id).one_or_none()
    if membership is None:
        raise _scim_error(404, "user not found on this team")
    user = db.get(User, user_id)
    return _user_resource(user, active=True)


@router.patch("/{team_id}/Users/{user_id}")
async def patch_scim_user(
    team_id: str, user_id: str, request: Request, db: OrmSession = Depends(get_db)
) -> dict:
    """Supports the one operation real IdPs actually send in practice:
    `{"op": "replace", "path": "active", "value": false}` to deprovision.
    `value: true` re-provisions (re-adds team membership) if the user
    still exists."""
    _get_team_or_404(team_id, db)
    user = db.get(User, user_id)
    if user is None:
        raise _scim_error(404, "user not found")

    body = await request.json()
    operations = body.get("Operations", [])
    active = True
    for op in operations:
        if op.get("path") == "active":
            active = bool(op.get("value"))

    membership = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user_id).one_or_none()
    if active and membership is None:
        db.add(TeamMembership(team_id=team_id, user_id=user_id, role="member"))
        log_audit_event(
            db, team_id=team_id, actor_user_id=None, action="team.scim.reactivate", target_type="user", target_id=user_id
        )
    elif not active and membership is not None:
        db.delete(membership)
        log_audit_event(
            db, team_id=team_id, actor_user_id=None, action="team.scim.deactivate", target_type="user", target_id=user_id
        )
    db.commit()
    return _user_resource(user, active=active)


@router.delete("/{team_id}/Users/{user_id}", status_code=204)
def delete_scim_user(team_id: str, user_id: str, db: OrmSession = Depends(get_db)) -> Response:
    """SCIM DELETE removes the resource from this team's roster — i.e.
    the membership, not the underlying `User` row, since that user may
    belong to other teams or have unrelated practice history. Mirrors
    `DELETE /teams/{id}/members/{user_id}`, just SCIM-shaped."""
    _get_team_or_404(team_id, db)
    membership = db.query(TeamMembership).filter_by(team_id=team_id, user_id=user_id).one_or_none()
    if membership is None:
        raise _scim_error(404, "user not found on this team")
    db.delete(membership)
    log_audit_event(
        db, team_id=team_id, actor_user_id=None, action="team.scim.deprovision", target_type="user", target_id=user_id
    )
    db.commit()
    return Response(status_code=204)
