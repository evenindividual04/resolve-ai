from __future__ import annotations

import pytest

from agents.llm_engine import LLMEngine


def test_provider_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    e = LLMEngine()
    assert e.provider == "groq"
    assert "llama" in e.model_name


@pytest.mark.asyncio
async def test_fallback_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    e = LLMEngine()
    d, _ = await e.extract_intent("I can pay 500", None)
    assert d.intent == "PAYMENT_OFFER"
    assert d.amount == 500


@pytest.mark.asyncio
async def test_route_to_openai_compatible(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    e = LLMEngine()

    async def fake_call(**kwargs):
        return '{"intent":"PAYMENT_COMMIT","amount":null,"confidence":0.95,"contradictory":false,"reasoning":"ok"}'

    e._call_openai_compatible = fake_call  # type: ignore[method-assign]
    d, _ = await e.extract_intent("payment done", None)
    assert d.intent == "PAYMENT_COMMIT"


@pytest.mark.asyncio
async def test_route_to_gemini(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    e = LLMEngine()

    async def fake_call(*, system, user, model):
        return '{"intent":"HARDSHIP","amount":null,"confidence":0.9,"contradictory":false,"reasoning":"ok"}'

    e._call_gemini = fake_call  # type: ignore[method-assign]
    d, _ = await e.extract_intent("hardship", None)
    assert d.intent == "HARDSHIP"
