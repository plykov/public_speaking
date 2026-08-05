from __future__ import annotations

from api.l1_calibration import L1_CALIBRATION_PROFILES, get_calibration_profile


def test_catalog_has_the_nine_scoped_languages() -> None:
    codes = {p.code for p in L1_CALIBRATION_PROFILES}
    assert codes == {"ru", "nl", "de", "fr", "es", "pt-br", "zh", "hi", "ja"}


def test_every_profile_has_label_and_note() -> None:
    for profile in L1_CALIBRATION_PROFILES:
        assert profile.label
        assert profile.calibration_note


def test_get_calibration_profile_known_code() -> None:
    profile = get_calibration_profile("ru")
    assert profile is not None
    assert profile.label == "Russian"


def test_get_calibration_profile_is_case_insensitive() -> None:
    assert get_calibration_profile("RU") is get_calibration_profile("ru")


def test_get_calibration_profile_unknown_code_returns_none() -> None:
    assert get_calibration_profile("xx") is None
