from __future__ import annotations

import pytest

from api.sso import MockSSOProvider, get_sso_provider


def test_build_authorization_url_includes_team_and_redirect() -> None:
    url = MockSSOProvider().build_authorization_url("team-1", "https://app.example/callback")
    assert "team_id=team-1" in url
    assert "redirect_uri=https://app.example/callback" in url


def test_exchange_code_returns_deterministic_identity() -> None:
    identity = MockSSOProvider().exchange_code("abc123")
    assert identity.external_id == "mock-sso-abc123"
    assert identity.email == "abc123@mock-sso.example"


def test_exchange_code_same_code_is_stable() -> None:
    provider = MockSSOProvider()
    assert provider.exchange_code("x") == provider.exchange_code("x")


def test_exchange_code_empty_raises() -> None:
    with pytest.raises(ValueError):
        MockSSOProvider().exchange_code("")


def test_get_sso_provider_mock() -> None:
    assert isinstance(get_sso_provider("mock"), MockSSOProvider)


def test_get_sso_provider_unknown_raises() -> None:
    with pytest.raises(NotImplementedError):
        get_sso_provider("okta")
