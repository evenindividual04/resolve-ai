from __future__ import annotations

import pytest

from agents.llm_engine import LLMEngine
from infra.settings import settings


def test_llm_settings_reject_non_positive_timeout(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_request_timeout_seconds", 0)
    monkeypatch.setattr(settings, "llm_request_max_retries", 3)
    monkeypatch.setattr(settings, "llm_min_request_interval_seconds", 0)
    with pytest.raises(ValueError, match="LLM_REQUEST_TIMEOUT_SECONDS"):
        LLMEngine(provider="groq")


def test_llm_settings_reject_zero_retries(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_request_timeout_seconds", 12)
    monkeypatch.setattr(settings, "llm_request_max_retries", 0)
    monkeypatch.setattr(settings, "llm_min_request_interval_seconds", 0)
    with pytest.raises(ValueError, match="LLM_REQUEST_MAX_RETRIES"):
        LLMEngine(provider="groq")


def test_llm_settings_reject_negative_request_interval(monkeypatch) -> None:
    monkeypatch.setattr(settings, "llm_request_timeout_seconds", 12)
    monkeypatch.setattr(settings, "llm_request_max_retries", 1)
    monkeypatch.setattr(settings, "llm_min_request_interval_seconds", -1)
    with pytest.raises(ValueError, match="LLM_MIN_REQUEST_INTERVAL_SECONDS"):
        LLMEngine(provider="groq")