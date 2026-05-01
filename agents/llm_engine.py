from __future__ import annotations

import asyncio
import json
import os
import re
import time
from dataclasses import dataclass, field
from hashlib import sha256
from typing import TYPE_CHECKING, Any

import httpx

from domain.models import LLMDecision
from infra.settings import settings

if TYPE_CHECKING:
    from domain.borrower import BorrowerProfile
    from domain.models import WorkflowState


@dataclass(frozen=True)
class PromptRegistry:
    default_extractor_version: str = "extractor_v2"
    extractor_prompts: dict[str, str] = field(
        default_factory=lambda: {
            "extractor_v1": (
                "Extract intent for debt negotiation. Return JSON only with keys: "
                "intent, amount, confidence, contradictory, reasoning."
            ),
            "extractor_v2": (
                "Extract intent for debt negotiation. Return JSON only with keys: "
                "intent, amount, confidence, contradictory, reasoning. "
                "intents allowed: PAYMENT_OFFER, PAYMENT_COMMIT, HARDSHIP, ABUSIVE, CONFUSED, UNKNOWN."
            ),
        }
    )
    responder_prompt_version: str = "responder_v1"
    policy_context_version: str = "policy_v1"

    def extractor_prompt(self, version: str) -> str:
        return self.extractor_prompts.get(version, self.extractor_prompts[self.default_extractor_version])

    def resolve_extractor_prompt_version(self, version: str | None) -> str:
        if version in self.extractor_prompts:
            return str(version)
        return self.default_extractor_version


class LLMEngine:
    """Provider-routed LLM extraction with reliability controls.

    Supported providers:
      - cerebras (OpenAI-compatible endpoint)
      - groq (OpenAI-compatible endpoint)
      - gemini (Google Generative Language API)

    All LLM calls are async to avoid blocking the event loop.
    Within a single request, repeated identical texts are short-circuit
    cached to avoid redundant calls and reduce rate-limit pressure.
    """

    def __init__(self, model_name: str | None = None, provider: str | None = None) -> None:
        self.provider = (provider or os.getenv("LLM_PROVIDER", "groq")).lower()
        self.model_name = model_name or self._default_model(self.provider)
        self.prompts = PromptRegistry()
        self.active_extractor_prompt_version = self.prompts.resolve_extractor_prompt_version(os.getenv("LLM_PROMPT_VERSION"))

        self.request_timeout_seconds = settings.llm_request_timeout_seconds
        self.request_max_retries = settings.llm_request_max_retries
        self.min_request_interval_seconds = settings.llm_min_request_interval_seconds
        self._last_request_at = 0.0

        # Per-request in-memory cache: keyed on sha256(text + prompt_version).
        # Prevents redundant LLM calls for identical text within the same event.
        self._decision_cache: dict[str, LLMDecision] = {}

        self.cerebras_api_key = os.getenv("CEREBRAS_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "")

        self._validate_runtime_settings()

    def clear_cache(self) -> None:
        """Clear per-request cache. Call at the start of each event processing cycle."""
        self._decision_cache.clear()

    async def extract_intent(self, text: str, previous_commitment: float | None, prompt_version: str | None = None) -> tuple[LLMDecision, bool]:
        resolved_prompt_version = self._resolve_prompt_version(prompt_version)

        # Check in-request cache first
        cache_key = self._cache_key(text, resolved_prompt_version)
        if cache_key in self._decision_cache:
            return self._decision_cache[cache_key], False

        candidate, is_real = await self._extract_live(text, previous_commitment, prompt_version=resolved_prompt_version)
        if candidate is not None:
            if self._needs_verifier(candidate):
                verified, verify_real = await self._verify_live(text, candidate, prompt_version=resolved_prompt_version)
                if verified is not None and verified.confidence >= candidate.confidence:
                    self._decision_cache[cache_key] = verified
                    return verified, is_real or verify_real
            self._decision_cache[cache_key] = candidate
            return candidate, is_real
        fallback = self._fallback_extract(text, previous_commitment, prompt_version=resolved_prompt_version)
        self._decision_cache[cache_key] = fallback
        return fallback, False

    async def extract_intent_multi(
        self,
        text: str,
        previous_commitment: float | None,
        prompt_version: str | None = None,
        n: int = 3,
    ) -> list[tuple[LLMDecision, bool]]:
        """Run N intent extractions concurrently for consistency sampling.

        This replaces the previous sequential 3-call pattern and is safe to
        call from async context without blocking the event loop.
        """
        resolved = self._resolve_prompt_version(prompt_version)
        tasks = [self.extract_intent(text, previous_commitment, resolved) for _ in range(n)]
        return list(await asyncio.gather(*tasks))

    async def generate_response(
        self,
        action: str,
        state: WorkflowState,
        profile: BorrowerProfile | None = None,
    ) -> str:
        """Generate a borrower-facing message for the given action.

        Uses a constrained prompt that enforces:
        - No threatening language
        - No amount promises outside policy
        - Tone calibrated to borrower's risk band and language
        """
        language = profile.language if profile else "en"
        risk_label = profile.risk_band.value if profile else "medium"
        channel = profile.preferred_channel.value if profile else "sms"

        tone_map = {
            "low": "warm and professional",
            "medium": "firm but empathetic",
            "high": "direct and urgent",
            "critical": "formal and factual",
        }
        tone = tone_map.get(risk_label, "professional")

        action_instructions = {
            "accept_offer": f"Confirm that the payment offer of {state.negotiated_amount} has been accepted. Provide the payment link.",
            "counter_offer": f"Politely counter-propose {state.counter_offer_amount or 'an amount'} as the minimum acceptable payment.",
            "clarify": "Ask the borrower to clarify their intent in one concise sentence.",
            "await_payment": "Confirm commitment noted. Remind them of the payment deadline.",
            "escalate": "Inform the borrower that this case is being reviewed by a specialist.",
            "halt": "Do not generate any message. Return empty string.",
            "resolve": "Confirm that payment has been received and the case is closed. Thank the borrower.",
            "payment_failed": "Inform the borrower that the payment was not received and ask them to retry.",
            "wait": "Politely acknowledge the message and inform them you will follow up at an appropriate time.",
        }
        instruction = action_instructions.get(action, f"Respond appropriately to action: {action}")

        if action == "halt":
            return ""

        system = (
            f"You are a professional debt recovery agent. Tone: {tone}. "
            f"Channel: {channel}. Language: {language}. "
            "Rules: Never threaten. Never promise discounts beyond what policy allows. "
            "Keep message under 80 words. Return plain text only, no JSON."
        )
        user = f"Borrower case: outstanding={state.outstanding_amount}, state={state.current_state.value}. Task: {instruction}"

        raw, _ = await self._call_provider(system, user)
        if raw:
            return raw.strip()
        # Deterministic fallback if LLM unavailable
        return self._fallback_response(action, state)

    def estimate_cost(self, text: str, high_risk: bool) -> tuple[int, float]:
        tokens = max(30, len(text) // 3)
        rate = 0.000004 if not high_risk else 0.000012
        return tokens, round(tokens * rate, 6)

    async def _extract_live(self, text: str, previous_commitment: float | None, *, prompt_version: str) -> tuple[LLMDecision | None, bool]:
        system = self.prompts.extractor_prompt(prompt_version)
        user = f"message={text}\nprevious_commitment={previous_commitment}"
        raw, is_real = await self._call_provider(system, user)
        if raw is None:
            return None, is_real
        decision = self._parse_decision(raw, prompt_version=prompt_version)
        return decision, is_real

    async def _verify_live(self, text: str, candidate: LLMDecision, *, prompt_version: str) -> tuple[LLMDecision | None, bool]:
        system = (
            "Verify an extracted decision for debt negotiation. Return JSON with same schema and "
            "lower confidence when uncertain."
        )
        user = f"message={text}\ncandidate={candidate.model_dump_json()}"
        raw, is_real = await self._call_provider(system, user)
        if raw is None:
            return None, is_real
        decision = self._parse_decision(raw, prompt_version=prompt_version)
        return decision, is_real

    async def _call_provider(self, system: str, user: str) -> tuple[str | None, bool]:
        """Call LLM provider asynchronously and return (content, was_real_call).

        Uses httpx.AsyncClient to avoid blocking the event loop. Sync client
        usage in async context was a critical bug that starved concurrent requests.
        """
        if self.provider == "cerebras" and self.cerebras_api_key:
            result = await self._call_openai_compatible(
                url="https://api.cerebras.ai/v1/chat/completions",
                api_key=self.cerebras_api_key,
                model=self.model_name,
                system=system,
                user=user,
            )
            return result, True
        if self.provider == "groq" and self.groq_api_key:
            result = await self._call_openai_compatible(
                url="https://api.groq.com/openai/v1/chat/completions",
                api_key=self.groq_api_key,
                model=self.model_name,
                system=system,
                user=user,
            )
            return result, True
        if self.provider == "gemini" and self.gemini_api_key:
            result = await self._call_gemini(system=system, user=user, model=self.model_name)
            return result, True
        return None, False

    async def _call_openai_compatible(self, *, url: str, api_key: str, model: str, system: str, user: str) -> str | None:
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

        for attempt in range(self.request_max_retries):
            try:
                await self._throttle_requests_async()
                async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
                    r = await client.post(url, headers=headers, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return data["choices"][0]["message"]["content"]
            except Exception:  # noqa: BLE001
                await asyncio.sleep(0.4 * (2**attempt))
        return None

    async def _call_gemini(self, *, system: str, user: str, model: str) -> str | None:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"temperature": 0, "responseMimeType": "application/json"},
        }

        for attempt in range(self.request_max_retries):
            try:
                await self._throttle_requests_async()
                async with httpx.AsyncClient(timeout=self.request_timeout_seconds) as client:
                    r = await client.post(url, json=payload)
                    r.raise_for_status()
                    data = r.json()
                    return data["candidates"][0]["content"]["parts"][0]["text"]
            except Exception:  # noqa: BLE001
                await asyncio.sleep(0.4 * (2**attempt))
        return None

    def _validate_runtime_settings(self) -> None:
        if self.request_timeout_seconds <= 0:
            raise ValueError("LLM_REQUEST_TIMEOUT_SECONDS must be > 0")
        if self.request_max_retries < 1:
            raise ValueError("LLM_REQUEST_MAX_RETRIES must be >= 1")
        if self.min_request_interval_seconds < 0:
            raise ValueError("LLM_MIN_REQUEST_INTERVAL_SECONDS must be >= 0")

    async def _throttle_requests_async(self) -> None:
        if self.min_request_interval_seconds <= 0:
            return
        now = time.monotonic()
        elapsed = now - self._last_request_at
        if elapsed < self.min_request_interval_seconds:
            await asyncio.sleep(self.min_request_interval_seconds - elapsed)
        self._last_request_at = time.monotonic()

    def _parse_decision(self, raw: str, *, prompt_version: str) -> LLMDecision | None:
        try:
            data = json.loads(raw)
            return LLMDecision(
                intent=data.get("intent", "UNKNOWN"),
                amount=data.get("amount"),
                confidence=float(data.get("confidence", 0.0)),
                contradictory=bool(data.get("contradictory", False)),
                prompt_version=prompt_version,
                reasoning=str(data.get("reasoning", "")),
            )
        except Exception:  # noqa: BLE001
            return None

    def _fallback_extract(self, text: str, previous_commitment: float | None, *, prompt_version: str) -> LLMDecision:
        lower = text.lower()
        contradictory = previous_commitment is not None and "can't" in lower and "pay" in lower

        if "ignore previous instructions" in lower or "change debt" in lower:
            return LLMDecision(
                intent="UNKNOWN",
                confidence=0.2,
                contradictory=contradictory,
                prompt_version=prompt_version,
                reasoning="prompt_injection_signal",
            )

        if any(k in lower for k in ["abuse", "idiot", "stupid"]):
            return LLMDecision(intent="ABUSIVE", confidence=0.95, contradictory=contradictory, prompt_version=prompt_version)

        if "hardship" in lower or "emergency" in lower:
            return LLMDecision(intent="HARDSHIP", confidence=0.9, contradictory=contradictory, prompt_version=prompt_version)

        amount = self._extract_amount(lower)
        if "pay" in lower and amount is not None:
            return LLMDecision(intent="PAYMENT_OFFER", amount=amount, confidence=0.88, contradictory=contradictory, prompt_version=prompt_version)

        if "i will pay" in lower or "payment done" in lower:
            return LLMDecision(intent="PAYMENT_COMMIT", confidence=0.76, contradictory=contradictory, prompt_version=prompt_version)

        return LLMDecision(intent="CONFUSED", confidence=0.45, contradictory=contradictory, prompt_version=prompt_version)

    @staticmethod
    def _fallback_response(action: str, state: WorkflowState) -> str:
        """Deterministic response fallback when LLM is unavailable."""
        msgs: dict[str, str] = {
            "accept_offer": f"Thank you. Your offer of {state.negotiated_amount} has been accepted. Please complete your payment.",
            "counter_offer": f"We can accept a minimum payment of {state.counter_offer_amount or state.outstanding_amount}. Please confirm.",
            "clarify": "Could you please clarify your intention regarding the outstanding balance?",
            "await_payment": "Thank you for your commitment. Please complete the payment by the agreed date.",
            "escalate": "Your case is being reviewed by a specialist who will contact you shortly.",
            "resolve": "Payment confirmed. Your account is now settled. Thank you.",
            "payment_failed": "We noticed your payment was not processed. Please retry at your earliest convenience.",
            "wait": "Thank you for reaching out. We will follow up with you soon.",
        }
        return msgs.get(action, "Thank you for contacting us.")

    def _resolve_prompt_version(self, prompt_version: str | None) -> str:
        return self.prompts.resolve_extractor_prompt_version(prompt_version or self.active_extractor_prompt_version)

    @staticmethod
    def _cache_key(text: str, prompt_version: str) -> str:
        return sha256(f"{text}|{prompt_version}".encode()).hexdigest()[:16]

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
