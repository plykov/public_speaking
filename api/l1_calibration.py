"""L1 calibration profiles (§4.2 — "Additional L1 calibration profiles").

Phase 1 shipped a free-text "first language" field: it was stored and shown
back verbatim in copy, but taught the product nothing. This module adds a
curated catalog of specific L1 backgrounds so onboarding can show a
calibration note that is actually about *that* speaker's likely transfer
patterns into English meetings — never used to score a recording (that
constraint from §4.1 M1 doesn't change), only to make the "why this matters
for you" copy concrete instead of generic.

Notes are deliberately hedged ("some speakers of...", "often", "can") and
scoped to well-documented, non-stigmatizing contrastive-linguistics patterns
(topic-comment ordering, discourse markers, register calibration) — never
claims about accent, intelligence, or "fixing" how someone sounds. A speaker
who doesn't recognise themselves in the note is exactly as welcome to ignore
it as one who does; `first_language_other` exists for anyone not in the
catalog, or who'd rather not say.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class L1CalibrationProfile:
    code: str
    label: str
    calibration_note: str


L1_CALIBRATION_PROFILES: list[L1CalibrationProfile] = [
    L1CalibrationProfile(
        code="ru",
        label="Russian",
        calibration_note=(
            "Russian tends to build context before the conclusion. In English "
            "meetings that reads as burying the recommendation — try leading "
            "with the point, then the reasoning."
        ),
    ),
    L1CalibrationProfile(
        code="nl",
        label="Dutch",
        calibration_note=(
            "Directness is often already a strength coming from Dutch — the "
            "more common trap is softening it right back out with hedges "
            "('maybe', 'a bit') when speaking English formally."
        ),
    ),
    L1CalibrationProfile(
        code="de",
        label="German",
        calibration_note=(
            "German conditional and subordinate-clause habits can carry over as "
            "long qualifying clauses before the main verb in English — watch for "
            "the point arriving late in the sentence, not just late in the turn."
        ),
    ),
    L1CalibrationProfile(
        code="fr",
        label="French",
        calibration_note=(
            "French argumentative style often builds toward a conclusion "
            "through structured stages (thesis-antithesis-synthesis). English "
            "meetings usually want the conclusion first, evidence after."
        ),
    ),
    L1CalibrationProfile(
        code="es",
        label="Spanish",
        calibration_note=(
            "Spanish discourse often uses more elaboration and repetition for "
            "emphasis; in English that repetition can read as restating instead "
            "of adding new information — one clear statement usually lands "
            "better than three restatements."
        ),
    ),
    L1CalibrationProfile(
        code="pt-br",
        label="Portuguese (Brazil)",
        calibration_note=(
            "Brazilian Portuguese speech is often high-energy and fast; in a "
            "second language that pace can outrun a listener's processing "
            "speed before it outruns your own — a few more/longer pauses can "
            "raise perceived clarity without changing content."
        ),
    ),
    L1CalibrationProfile(
        code="zh",
        label="Mandarin Chinese",
        calibration_note=(
            "Mandarin commonly favors topic-comment ordering (setting context, "
            "then commenting on it) over English's subject-verb-object, "
            "recommendation-first pattern — practice starting with the "
            "recommendation even when it feels like skipping a step."
        ),
    ),
    L1CalibrationProfile(
        code="hi",
        label="Hindi",
        calibration_note=(
            "Hindi business register often uses more indirect, deferential "
            "phrasing toward seniority. That register is easy to over-carry "
            "into English as excess hedging ('I was just thinking, perhaps...') "
            "even among peers."
        ),
    ),
    L1CalibrationProfile(
        code="ja",
        label="Japanese",
        calibration_note=(
            "Japanese business communication often defers the main point and "
            "leaves some conclusions implicit by design (a listener is expected "
            "to infer them). English meetings usually expect the point stated "
            "explicitly, even when it feels over-direct to say so."
        ),
    ),
]

_BY_CODE = {p.code: p for p in L1_CALIBRATION_PROFILES}


def get_calibration_profile(code: str) -> L1CalibrationProfile | None:
    """Look up a catalog profile by code; `None` for "other"/unrecognised codes."""
    return _BY_CODE.get(code.lower())
