"""Shared singletons for dependency injection."""

from __future__ import annotations

from functools import lru_cache

from api.config import settings
from api.pipeline.llm import LLMRubricProvider, get_llm_provider
from api.pipeline.normalize import AudioNormalizer, PassthroughNormalizer
from api.pipeline.stt import STTProvider, get_stt_provider
from api.storage import LocalObjectStore, ObjectStore


@lru_cache
def get_object_store() -> ObjectStore:
    return LocalObjectStore(settings.storage_dir)


@lru_cache
def get_normalizer() -> AudioNormalizer:
    return PassthroughNormalizer()


@lru_cache
def get_stt() -> STTProvider:
    return get_stt_provider(settings.stt_provider)


@lru_cache
def get_llm() -> LLMRubricProvider:
    return get_llm_provider(settings.llm_provider)
