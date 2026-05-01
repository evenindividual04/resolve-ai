from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from domain.models import LLMDecision, PolicyResult


@dataclass(frozen=True)
class PolicyConfig:
    max_discount: float = 0.3
    min_payment: float = 100.0
    allowed_start_hour: int = 9
    allowed_end_hour: int = 18
    min_confidence: float = 0.65


class PolicyEngine:
    def __init__(self, cfg: PolicyConfig | None = None) -> None:
        self.cfg = cfg or PolicyConfig()

    def evaluate(self, *, decision: LLMDecision, outstanding_amount: float, now: datetime) -> PolicyResult:
        if decision.intent == "ABUSIVE":
            return PolicyResult(allowed=False, reason_code="abuse_detected", next_action="escalate")

        if decision.confidence < self.cfg.min_confidence:
            return PolicyResult(allowed=False, reason_code="low_confidence", next_action="clarify")

        if decision.contradictory:
            return PolicyResult(allowed=False, reason_code="intent_contradiction", next_action="clarify")

        if not (self.cfg.allowed_start_hour <= now.hour <= self.cfg.allowed_end_hour):
            return PolicyResult(allowed=False, reason_code="outside_allowed_hours", next_action="wait")

        if decision.intent == "PAYMENT_OFFER":
            if decision.amount is None:
                return PolicyResult(allowed=False, reason_code="missing_amount", next_action="clarify")
            max_allowed_discounted = outstanding_amount * (1.0 - self.cfg.max_discount)
            if decision.amount < self.cfg.min_payment:
                return PolicyResult(allowed=False, reason_code="below_min_payment", next_action="counter_offer")
            if decision.amount < max_allowed_discounted:
                return PolicyResult(allowed=False, reason_code="discount_too_high", next_action="counter_offer")
            return PolicyResult(allowed=True, reason_code="offer_acceptable", next_action="accept_offer")

        if decision.intent == "PAYMENT_COMMIT":
            return PolicyResult(allowed=True, reason_code="commit_detected", next_action="await_payment")

        if decision.intent == "HARDSHIP":
            return PolicyResult(allowed=False, reason_code="hardship_review", next_action="escalate")

        if decision.intent in {"CONFUSED", "UNKNOWN"}:
            return PolicyResult(allowed=False, reason_code="user_ambiguity", next_action="clarify")

        return PolicyResult(allowed=False, reason_code="policy_default_deny", next_action="escalate")
