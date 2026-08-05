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
    rubric_version: str = os.environ.get("RUBRIC_VERSION", "rubric-v1")
    model_version: str = os.environ.get("MODEL_VERSION", "mock-llm-v1")


settings = Settings()
