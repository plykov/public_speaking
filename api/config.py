"""Runtime configuration, read from environment variables (§6.1 stack)."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get("DATABASE_URL", "sqlite:///./cadence_dev.db")
    storage_dir: str = os.environ.get("STORAGE_DIR", "./media_store")
    stt_provider: str = os.environ.get("STT_PROVIDER", "mock")
    llm_provider: str = os.environ.get("LLM_PROVIDER", "mock")
    billing_provider: str = os.environ.get("BILLING_PROVIDER", "mock")
    exemplar_provider: str = os.environ.get("EXEMPLAR_PROVIDER", "mock")
    roleplay_llm_provider: str = os.environ.get("ROLEPLAY_LLM_PROVIDER", "mock")
    calendar_provider: str = os.environ.get("CALENDAR_PROVIDER", "mock")
    sso_provider: str = os.environ.get("SSO_PROVIDER", "mock")
    rubric_version: str = os.environ.get("RUBRIC_VERSION", "rubric-v1")
    model_version: str = os.environ.get("MODEL_VERSION", "mock-llm-v1")
    cors_allow_origins: tuple[str, ...] = tuple(
        o.strip()
        for o in os.environ.get("CORS_ALLOW_ORIGINS", "http://localhost:3000").split(",")
        if o.strip()
    )
    # §4.2 Web Push. If unset, api.push generates an ephemeral keypair at
    # process start — fine for local dev, but subscriptions won't survive
    # a restart. Set these to persist subscriptions across restarts.
    vapid_public_key: str | None = os.environ.get("VAPID_PUBLIC_KEY")
    vapid_private_key: str | None = os.environ.get("VAPID_PRIVATE_KEY")
    vapid_subject: str = os.environ.get("VAPID_SUBJECT", "mailto:support@example.com")


settings = Settings()
