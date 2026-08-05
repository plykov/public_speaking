from __future__ import annotations

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from api.db import Base, Team, TeamMembership, User
from api.lifecycle import DEFAULT_RETENTION_DAYS, effective_retention_days


@pytest.fixture()
def db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    try:
        yield session
    finally:
        session.close()


def test_no_teams_uses_default(db) -> None:
    user = User()
    db.add(user)
    db.commit()
    assert effective_retention_days(db, user.id) == DEFAULT_RETENTION_DAYS


def test_none_user_id_uses_default(db) -> None:
    assert effective_retention_days(db, None) == DEFAULT_RETENTION_DAYS


def test_team_with_no_override_uses_default(db) -> None:
    user = User()
    db.add(user)
    db.flush()
    team = Team(name="Acme", retention_days=None)
    db.add(team)
    db.flush()
    db.add(TeamMembership(team_id=team.id, user_id=user.id, role="admin"))
    db.commit()
    assert effective_retention_days(db, user.id) == DEFAULT_RETENTION_DAYS


def test_team_with_override_is_used(db) -> None:
    user = User()
    db.add(user)
    db.flush()
    team = Team(name="Acme", retention_days=7)
    db.add(team)
    db.flush()
    db.add(TeamMembership(team_id=team.id, user_id=user.id, role="admin"))
    db.commit()
    assert effective_retention_days(db, user.id) == 7


def test_most_restrictive_team_wins(db) -> None:
    user = User()
    db.add(user)
    db.flush()
    lenient = Team(name="Lenient", retention_days=90)
    strict = Team(name="Strict", retention_days=7)
    db.add_all([lenient, strict])
    db.flush()
    db.add(TeamMembership(team_id=lenient.id, user_id=user.id, role="member"))
    db.add(TeamMembership(team_id=strict.id, user_id=user.id, role="member"))
    db.commit()
    assert effective_retention_days(db, user.id) == 7


def test_unconfigured_team_does_not_beat_configured_one(db) -> None:
    """A team with no override shouldn't count as 'infinite retention' and
    win — only teams that explicitly set a value compete."""
    user = User()
    db.add(user)
    db.flush()
    unconfigured = Team(name="Unconfigured", retention_days=None)
    configured = Team(name="Configured", retention_days=14)
    db.add_all([unconfigured, configured])
    db.flush()
    db.add(TeamMembership(team_id=unconfigured.id, user_id=user.id, role="member"))
    db.add(TeamMembership(team_id=configured.id, user_id=user.id, role="member"))
    db.commit()
    assert effective_retention_days(db, user.id) == 14
