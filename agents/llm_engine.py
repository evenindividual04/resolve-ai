from __future__ import annotations

import json
import os
import re
import time
from dataclasses import dataclass
from typing import Any

import httpx

from domain.models import LLMDecision


@dataclass(frozen=True)
class PromptRegistry:
    extractor_prompt_version: str = "extractor_v2"
    responder_prompt_version: str = "responder_v1"
    policy_context_version: str = "policy_v1"


class LLMEngine:
    """Provider-routed LLM extraction with reliability controls.

    Supported providers:
      - cerebras (OpenAI-compatible endpoint)
      - groq (OpenAI-compatible endpoint)
      - gemini (Google Generative Language API)
    """

    def __init__(self, model_name: str | None = None, provider: str | None = None) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
        self.model_name = model_name or self._default_model(self.provider)
        self.prompts = PromptRegistry()

        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

    def extract_intent(self, text: str, previous_commitment: float | None) -> LLMDecision:
        candidate = self._extract_live(text, previous_commitment)
        if candidate is not None:
            if self._needs_verifier(candidate):
                verified = self._verify_live(text, candidate)
                if verified is not None and verified.confidence >= candidate.confidence:
                    return verified
            return candidate
        return self._fallback_extract(text, previous_commitment)

    def estimate_cost(self, text: str, high_risk: bool) -> tuple[int, float]:
        tokens = max(30, len(text) // 3)
        rate = 0.000004 if not high_risk else 0.000012
        return tokens, round(tokens * rate, 6)

    def _extract_live(self, text: str, previous_commitment: float | None) -> LLMDecision | None:
        system = (
            "Extract intent for debt negotiation. Return JSON only with keys: "
            "intent, amount, confidence, contradictory, reasoning. "
            "intents allowed: PAYMENT_OFFER, PAYMENT_COMMIT, HARDSHIP, ABUSIVE, CONFUSED, UNKNOWN."
        )
        user = f"message={text}\nprevious_commitment={previous_commitment}"
        raw = self._call_provider(system, user)
        if raw is None:
            return None
        return self._parse_decision(raw)

    def _verify_live(self, text: str, candidate: LLMDecision) -> LLMDecision | None:
        system = (
            "Verify an extracted decision for debt negotiation. Return JSON with same schema and "
            "lower confidence when uncertain."
        )
        user = f"message={text}\ncandidate={candidate.model_dump_json()}"
        raw = self._call_provider(system, user)
        if raw is None:
            return None
        return self._parse_decision(raw)

    def _call_provider(self, system: str, user: str) -> str | None:
        if self.provider == "cerebras" and self.cerebras_api_key:
            return self._call_openai_compatible(
                url="https://api.cerebras.ai/v1/chat/completions",
                api_key=self.cerebras_api_key,
                model=self.model_name,
                system=system,
                user=user,
            )
        if self.provider == "groq" and self.groq_api_key:
            return self._call_openai_compatible(
                url="https://api.groq.com/openai/v1/chat/completions",
                api_key=self.groq_api_key,
                model=self.model_name,
                system=system,
                user=user,
            )
        if self.provider == "gemini" and self.gemini_api_key:
            return self._call_gemini(system=system, user=user, model=self.model_name)
        return None

    def _call_openai_compatible(self, *, url: str, api_key: str, model: str, system: str, user: str) -> str | None:
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

        for attempt in range(3):
            try:
                with httpx.Client(timeout=12.0) as client:
                    r = client.post(url, headers=headers, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return data["choices"][0]["message"]["content"]
            except Exception:  # noqa: BLE001
                time.sleep(0.4 * (2**attempt))
        return None

    def _call_gemini(self, *, system: str, user: str, model: str) -> str | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }

        for attempt in range(3):
            try:
                with httpx.Client(timeout=12.0) as client:
                    r = client.post(url, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:  # noqa: BLE001
                time.sleep(0.4 * (2**attempt))
        return None

    def _parse_decision(self, raw: str) -> LLMDecision | None:
        try:
            data = json.loads(raw)
            return LLMDecision(
                intent=data.get("intent", "UNKNOWN"),
                amount=data.get("amount"),
                confidence=float(data.get("confidence", 0.0)),
                contradictory=bool(data.get("contradictory", False)),
                prompt_version=self.prompts.extractor_prompt_version,
                reasoning=str(data.get("reasoning", "")),
            )
        except Exception:  # noqa: BLE001
            return None

    def _fallback_extract(self, text: str, previous_commitment: float | None) -> LLMDecision:
        lower = text.lower()
        contradictory = previous_commitment is not None and "can't" in lower and "pay" in lower

        if "ignore previous instructions" in lower or "change debt" in lower:
            return LLMDecision(
                intent="UNKNOWN",
                confidence=0.2,
                contradictory=contradictory,
                prompt_version=self.prompts.extractor_prompt_version,
                reasoning="prompt_injection_signal",
            )

        if any(k in lower for k in ["abuse", "idiot", "stupid"]):
            return LLMDecision(intent="ABUSIVE", confidence=0.95, contradictory=contradictory)

        if "hardship" in lower or "emergency" in lower:
            return LLMDecision(intent="HARDSHIP", confidence=0.9, contradictory=contradictory)

        amount = self._extract_amount(lower)
        if "pay" in lower and amount is not None:
            return LLMDecision(intent="PAYMENT_OFFER", amount=amount, confidence=0.88, contradictory=contradictory)

        if "i will pay" in lower or "payment done" in lower:
            return LLMDecision(intent="PAYMENT_COMMIT", confidence=0.76, contradictory=contradictory)

        return LLMDecision(intent="CONFUSED", confidence=0.45, contradictory=contradictory)

    @staticmethod
    def _extract_amount(text: str) -> float | None:
        m = re.search(r"(\d+(?:\.\d{1,2})?)", text)
        if not m:
            return None
        return float(m.group(1))

    @staticmethod
    def _needs_verifier(decision: LLMDecision) -> bool:
        return decision.intent in {"HARDSHIP", "UNKNOWN", "ABUSIVE"} or decision.confidence < 0.8

    @staticmethod
    def _default_model(provider: str) -> str:
        if provider == "cerebras":
            return os.getenv("CEREBRAS_MODEL", "llama-3.3-70b")
        if provider == "groq":
            return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
        if provider == "gemini":
            return os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
        return os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
