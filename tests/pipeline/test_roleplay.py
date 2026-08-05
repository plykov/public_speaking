from __future__ import annotations

import pytest

from api.pipeline.roleplay import (
    GROUP_MAX_USER_TURNS,
    PERSONAS,
    MockRoleplayLLMProvider,
    RoleplayTurnData,
    get_persona,
    get_roleplay_llm_provider,
    pick_next_persona,
)


def test_persona_catalog_has_at_least_one_persona() -> None:
    assert len(PERSONAS) >= 1
    for p in PERSONAS:
        assert p.opening_line
        assert p.closing_line
        assert len(p.follow_ups) > 0


def test_persona_catalog_has_multiple_distinct_personas_for_multi_mode() -> None:
    assert len(PERSONAS) >= 3
    assert len({p.id for p in PERSONAS}) == len(PERSONAS)


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


def test_pick_next_persona_round_robins() -> None:
    personas = list(PERSONAS[:3])
    assert pick_next_persona(personas, user_turn_count=1) is personas[0]
    assert pick_next_persona(personas, user_turn_count=2) is personas[1]
    assert pick_next_persona(personas, user_turn_count=3) is personas[2]
    assert pick_next_persona(personas, user_turn_count=4) is personas[0]


def test_reply_uses_max_user_turns_override_for_group_mode() -> None:
    persona = get_persona("skeptical_stakeholder")  # max_user_turns=3
    history = [RoleplayTurnData(speaker="user", text="we should ship it")]
    # Without override, turn 3 would already close (persona.max_user_turns == 3);
    # with a higher group override it should still be open.
    reply = MockRoleplayLLMProvider().reply(
        persona, history, user_turn_count=3, max_user_turns=GROUP_MAX_USER_TURNS
    )
    assert reply.is_closing is False

    reply = MockRoleplayLLMProvider().reply(
        persona, history, user_turn_count=GROUP_MAX_USER_TURNS, max_user_turns=GROUP_MAX_USER_TURNS
    )
    assert reply.is_closing is True
