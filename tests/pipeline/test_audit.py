from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.audit import log_audit_event
from api.db import AuditLogEntry, Base, User


@pytest.fixture()
def db():
    """An isolated in-memory SQLite DB, independent of api.db's
    module-level engine/DATABASE_URL — this test shouldn't care which
    file the rest of the suite happens to be pointed at."""
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_log_audit_event_creates_row(db) -> None:
    user = User()
    db.add(user)
    db.commit()

    entry = log_audit_event(
        db,
        team_id=None,
        actor_user_id=user.id,
        action="test.action",
        target_type="thing",
        target_id="abc",
        detail={"k": "v"},
    )
    db.commit()

    fetched = db.query(AuditLogEntry).filter_by(id=entry.id).one()
    assert fetched.action == "test.action"
    assert fetched.actor_user_id == user.id
    assert fetched.target_type == "thing"
    assert fetched.target_id == "abc"
    assert fetched.detail == {"k": "v"}


def test_log_audit_event_does_not_commit(db) -> None:
    """The caller commits — a rollback should discard the audit row along
    with whatever action it would have accompanied."""
    entry = log_audit_event(db, team_id=None, actor_user_id=None, action="uncommitted")
    entry_id = entry.id
    db.rollback()
    assert db.query(AuditLogEntry).filter_by(id=entry_id).one_or_none() is None
