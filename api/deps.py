"""Shared singletons for dependency injection."""

from __future__ import annotations

from functools import lru_cache

from api.billing import BillingProvider, get_billing_provider
from api.config import settings
from api.calendar import CalendarProvider, get_calendar_provider
from api.pipeline.exemplar import ExemplarProvider, get_exemplar_provider
from api.pipeline.llm import LLMRubricProvider, get_llm_provider
from api.pipeline.roleplay import RoleplayLLMProvider, get_roleplay_llm_provider
from api.sso import SSOProvider, get_sso_provider
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


@lru_cache
def get_billing() -> BillingProvider:
    return get_billing_provider(settings.billing_provider)


@lru_cache
def get_exemplar() -> ExemplarProvider:
    return get_exemplar_provider(settings.exemplar_provider)


@lru_cache
def get_roleplay_llm() -> RoleplayLLMProvider:
    return get_roleplay_llm_provider(settings.roleplay_llm_provider)


@lru_cache
def get_calendar() -> CalendarProvider:
    return get_calendar_provider(settings.calendar_provider)


@lru_cache
def get_sso() -> SSOProvider:
    return get_sso_provider(settings.sso_provider)
