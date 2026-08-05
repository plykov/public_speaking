"""Audit logging (§4.3). A thin, deliberately dumb helper: one function
that appends one immutable row. No redaction, no retention policy of its
own (audit entries are never purged by `api.lifecycle`), no query
builder — keeping it trivial is the point, since an audit log with
complex logic is harder to trust.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session as OrmSession

from api.db import AuditLogEntry


def log_audit_event(
    db: OrmSession,
    *,
    team_id: str | None,
    actor_user_id: str | None,
    action: str,
    target_type: str | None = None,
    target_id: str | None = None,
    detail: dict[str, Any] | None = None,
) -> AuditLogEntry:
    """Append an audit entry. Does not commit — caller's existing
    transaction commits it alongside the action it records, so an audit
    entry is never persisted for an action that itself failed to save."""
    entry = AuditLogEntry(
        team_id=team_id,
        actor_user_id=actor_user_id,
        action=action,
        target_type=target_type,
        target_id=target_id,
        detail=detail,
    )
    db.add(entry)
    return entry
