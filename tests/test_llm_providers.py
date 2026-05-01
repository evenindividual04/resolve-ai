from __future__ import annotations

from agents.llm_engine import LLMEngine


def test_provider_defaults(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    e = LLMEngine()
    assert e.provider == "groq"
    assert "llama" in e.model_name


def test_fallback_without_keys(monkeypatch) -> None:
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    e = LLMEngine()
    d = e.extract_intent("I can pay 500", None)
    assert d.intent == "PAYMENT_OFFER"
    assert d.amount == 500


def test_route_to_openai_compatible(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("GROQ_API_KEY", "x")
    e = LLMEngine()

    def fake_call(**kwargs):
        return '{"intent":"PAYMENT_COMMIT","amount":null,"confidence":0.95,"contradictory":false,"reasoning":"ok"}'

    e._call_openai_compatible = fake_call  # type: ignore[method-assign]
    d = e.extract_intent("payment done", None)
    assert d.intent == "PAYMENT_COMMIT"


def test_route_to_gemini(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "gemini")
    monkeypatch.setenv("GEMINI_API_KEY", "x")
    e = LLMEngine()

    def fake_call(*, system, user, model):
        return '{"intent":"HARDSHIP","amount":null,"confidence":0.9,"contradictory":false,"reasoning":"ok"}'

    e._call_gemini = fake_call  # type: ignore[method-assign]
    d = e.extract_intent("hardship", None)
    assert d.intent == "HARDSHIP"
