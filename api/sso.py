"""SSO (§4.3) — SAML/OIDC single sign-on for team login.

Real SSO needs a real identity provider (Okta, Azure AD, Google
Workspace) with an actual app registration/metadata exchange — a vendor
credential gap in the same category as Stripe or a frontier LLM, not
something a client-side trick can substitute for (unlike Web Push or
SpeechSynthesis, there's no "the browser already does this" move
available here). `SSOProvider` is the seam a real SAML/OIDC integration
implements; `MockSSOProvider` simulates a successful login immediately,
so the genuinely real part — turning an authenticated identity into team
membership — can be built and tested without waiting on IdP onboarding.

See `api/scim.py` for the other half of §4.3's "SSO/SCIM": SCIM
provisioning doesn't have this gap, because our app is the SCIM *server*
an IdP calls into, not a SCIM client calling out to one.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class SSOIdentity:
    external_id: str
    email: str


class SSOProvider(ABC):
    @abstractmethod
    def build_authorization_url(self, team_id: str, redirect_uri: str) -> str: ...

    @abstractmethod
    def exchange_code(self, code: str) -> SSOIdentity: ...


class MockSSOProvider(SSOProvider):
    """Not a real IdP integration — see module docstring. Deterministic:
    the "code" is treated as an opaque identifier for a synthetic
    identity, rather than actually verifying anything against an IdP."""

    def build_authorization_url(self, team_id: str, redirect_uri: str) -> str:
        return f"https://mock-sso.example/authorize?team_id={team_id}&redirect_uri={redirect_uri}"

    def exchange_code(self, code: str) -> SSOIdentity:
        if not code:
            raise ValueError("code must not be empty")
        return SSOIdentity(external_id=f"mock-sso-{code}", email=f"{code}@mock-sso.example")


def get_sso_provider(name: str) -> SSOProvider:
    if name == "mock":
        return MockSSOProvider()
    raise NotImplementedError(
        f"SSO provider {name!r} is not wired up yet — integrate a real SAML/OIDC identity "
        "provider behind this same SSOProvider interface."
    )
