"""Voice AI roleplay — single persona and multi-persona, turn-based (§4.2).

§6.1 pins this to "streaming STT → LLM → TTS." In this environment:
- **STT** is real plumbing already built for Practice Studio
  (`api.pipeline.stt`, `api.deps.get_stt`) — roleplay turns reuse it
  directly rather than duplicating it.
- **LLM** (persona reply generation) follows the same seam-plus-mock
  pattern as `api.pipeline.llm`: `RoleplayLLMProvider` is what a real
  frontier-model integration implements; `MockRoleplayLLMProvider` is
  deliberately rule-based, reusing the same deterministic
  `metrics.hedging` detector already in the pipeline rather than a
  fabricated "AI-sounding" response.
- **TTS** doesn't need a mock at all: the frontend speaks the persona's
  lines with the browser's native `SpeechSynthesis` API (Web Speech API),
  which is real, standards-based, and free — no vendor account, matching
  the Web Push precedent (§4.2) of finding a genuinely real implementation
  where the browser itself can do the work.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass

from metrics.hedging import compute_hedging_index
from metrics.models import Word


@dataclass(frozen=True)
class RoleplayPersona:
    id: str
    name: str
    role: str
    description: str
    opening_line: str
    follow_ups: tuple[str, ...]
    closing_line: str
    max_user_turns: int = 3


PERSONAS: tuple[RoleplayPersona, ...] = (
    RoleplayPersona(
        id="skeptical_stakeholder",
        name="Priya",
        role="Skeptical stakeholder",
        description=(
            "A senior stakeholder in a status update meeting who pushes back on vague "
            "recommendations and wants a clear, direct answer."
        ),
        opening_line="Okay, what's the update — and what do you actually recommend we do?",
        follow_ups=(
            "Why is that the right call instead of the alternative?",
            "What happens if we're wrong about that?",
            "Can you say that again in one sentence, no caveats?",
        ),
        closing_line="Alright — that's clear enough for me. Let's go with that.",
        max_user_turns=3,
    ),
    RoleplayPersona(
        id="data_driven_skeptic",
        name="Marcus",
        role="Data-driven skeptic",
        description=(
            "Wants every recommendation backed by a number — pushes past confident "
            "delivery straight to 'what's the evidence.'"
        ),
        opening_line="Before we go further — what's the data behind that?",
        follow_ups=(
            "What's the actual number, not the general sense of it?",
            "Where did that figure come from?",
            "How confident are you in that estimate?",
        ),
        closing_line="Good — that's the kind of specificity I needed.",
        max_user_turns=3,
    ),
    RoleplayPersona(
        id="time_pressured_exec",
        name="Elena",
        role="Time-pressured executive",
        description=(
            "Has five minutes and wants the recommendation first, reasoning only if asked — "
            "penalizes any answer that opens with context instead of the point."
        ),
        opening_line="I've got five minutes — what do you need from me?",
        follow_ups=(
            "Skip to the ask — what do you need me to decide?",
            "Shorter — what's the one sentence version?",
            "Is that a yes/no I can give you right now, or does it need more thought?",
        ),
        closing_line="Got it — decision made, let's move.",
        max_user_turns=3,
    ),
)

_BY_ID = {p.id: p for p in PERSONAS}


def get_persona(persona_id: str) -> RoleplayPersona | None:
    return _BY_ID.get(persona_id)


# §4.2 multi-persona: shared turn budget for a group conversation, instead
# of summing each persona's own `max_user_turns` — a 3-persona panel
# shouldn't take 3x as many rounds just because there are more speakers.
GROUP_MAX_USER_TURNS = 4


def pick_next_persona(personas: list[RoleplayPersona], user_turn_count: int) -> RoleplayPersona:
    """Round-robin: the persona whose turn it is to respond next, given how
    many user turns have happened so far (1-indexed: the 1st user turn is
    answered by personas[0], the 2nd by personas[1], and so on)."""
    return personas[(user_turn_count - 1) % len(personas)]


@dataclass(frozen=True)
class RoleplayTurnData:
    speaker: str  # "user" | "persona"
    text: str


@dataclass(frozen=True)
class RoleplayReply:
    text: str
    is_closing: bool


def _to_words(text: str) -> list[Word]:
    """Fabricate evenly-spaced timestamps so the real hedging detector
    (built for word-level ASR output) can run on plain reply text —
    the detector only uses word text for phrase matching; timestamps just
    need to be monotonic, not accurate, for this purpose."""
    tokens = text.split()
    return [Word(text=t, start_ms=i * 200, end_ms=i * 200 + 150, confidence=1.0) for i, t in enumerate(tokens)]


class RoleplayLLMProvider(ABC):
    @abstractmethod
    def reply(
        self,
        persona: RoleplayPersona,
        history: list[RoleplayTurnData],
        user_turn_count: int,
        max_user_turns: int | None = None,
    ) -> RoleplayReply: ...


class MockRoleplayLLMProvider(RoleplayLLMProvider):
    """Rule-based, not a language model — see module docstring. Reacts to
    detected hedging the same way a coach would, and otherwise cycles
    through the persona's scripted follow-up pressure questions."""

    def reply(
        self,
        persona: RoleplayPersona,
        history: list[RoleplayTurnData],
        user_turn_count: int,
        max_user_turns: int | None = None,
    ) -> RoleplayReply:
        turn_limit = max_user_turns if max_user_turns is not None else persona.max_user_turns
        if user_turn_count >= turn_limit:
            return RoleplayReply(text=persona.closing_line, is_closing=True)

        last_user_text = next(
            (t.text for t in reversed(history) if t.speaker == "user"), ""
        )
        _, hedge_events = compute_hedging_index(_to_words(last_user_text))
        if hedge_events:
            phrase = (hedge_events[0].value or {}).get("phrase", "")
            return RoleplayReply(
                text=f'You said "{phrase}" — are you confident in that, or is there something specific you\'re unsure of?',
                is_closing=False,
            )

        follow_up = persona.follow_ups[(user_turn_count - 1) % len(persona.follow_ups)]
        return RoleplayReply(text=follow_up, is_closing=False)


def get_roleplay_llm_provider(name: str) -> RoleplayLLMProvider:
    if name == "mock":
        return MockRoleplayLLMProvider()
    raise NotImplementedError(
        f"Roleplay LLM provider {name!r} is not wired up yet — integrate a frontier model "
        "behind this same RoleplayLLMProvider interface."
    )
