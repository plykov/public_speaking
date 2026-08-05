from __future__ import annotations

import pytest

from api.pipeline.roleplay import (
    PERSONAS,
    MockRoleplayLLMProvider,
    RoleplayTurnData,
    get_persona,
    get_roleplay_llm_provider,
)


def test_persona_catalog_has_at_least_one_persona() -> None:
    assert len(PERSONAS) >= 1
    for p in PERSONAS:
        assert p.opening_line
        assert p.closing_line
        assert len(p.follow_ups) > 0


def test_get_persona_known_id() -> None:
    persona = get_persona("skeptical_stakeholder")
    assert persona is not None
    assert persona.name == "Priya"


def test_get_persona_unknown_id_returns_none() -> None:
    assert get_persona("nope") is None


def test_reply_reacts_to_hedging() -> None:
    persona = get_persona("skeptical_stakeholder")
    history = [RoleplayTurnData(speaker="user", text="maybe we should ship it")]
    reply = MockRoleplayLLMProvider().reply(persona, history, user_turn_count=1)
    assert "maybe" in reply.text.lower()
    assert reply.is_closing is False


def test_reply_cycles_through_follow_ups_when_no_hedging() -> None:
    persona = get_persona("skeptical_stakeholder")
    history = [RoleplayTurnData(speaker="user", text="we should ship it now")]
    reply = MockRoleplayLLMProvider().reply(persona, history, user_turn_count=1)
    assert reply.text == persona.follow_ups[0]
    assert reply.is_closing is False


def test_reply_closes_after_max_user_turns() -> None:
    persona = get_persona("skeptical_stakeholder")
    history = [RoleplayTurnData(speaker="user", text="we should ship it")]
    reply = MockRoleplayLLMProvider().reply(persona, history, user_turn_count=persona.max_user_turns)
    assert reply.text == persona.closing_line
    assert reply.is_closing is True


def test_reply_with_empty_history_does_not_crash() -> None:
    persona = get_persona("skeptical_stakeholder")
    reply = MockRoleplayLLMProvider().reply(persona, [], user_turn_count=1)
    assert reply.text


def test_get_roleplay_llm_provider_mock() -> None:
    assert isinstance(get_roleplay_llm_provider("mock"), MockRoleplayLLMProvider)


def test_get_roleplay_llm_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_roleplay_llm_provider("openai")
