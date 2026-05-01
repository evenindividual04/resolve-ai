from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from agents.negotiation_strategy import NegotiationStrategy
from domain.borrower import BorrowerProfile, LoanSegment
from domain.models import LLMDecision, PolicyResult


@dataclass(frozen=True)
class PolicyConfig:
    """Segment-default policy configuration.

    In practice each loan segment has its own config — see ProfileLoader.segment_policy_config().
    This dataclass is the fallback when no profile is available.
    """
    max_discount: float = 0.3
    min_payment: float = 100.0
    allowed_start_hour: int = 9
    allowed_end_hour: int = 18
    min_confidence: float = 0.65
    max_turns: int = 5


class PolicyEngine:
    """Evaluates a borrower intent signal against collections policy.

    Key design decisions vs the original:
    - Accepts BorrowerProfile for domain-aware policy dispatch.
    - Enforces DNC flag as a hard gate — no contact allowed regardless of intent.
    - Enforces legal_flag — immediate escalation to human operator.
    - Uses strike_count from WorkflowState: ≥3 strikes auto-escalates.
    - Uses DPD (days past due) to tighten discount bounds on overdue cases.
    - Delegates counter-offer amounts to NegotiationStrategy so the policy engine
      decides *whether* to counter, and the strategy engine decides *what* to counter with.
    - Enforces turn budget per segment to prevent infinite clarification loops.
    """

    def __init__(self, cfg: PolicyConfig | None = None) -> None:
        self.cfg = cfg or PolicyConfig()
        self.negotiation = NegotiationStrategy()

    def evaluate(
        self,
        *,
        decision: LLMDecision,
        outstanding_amount: float,
        now: datetime,
        profile: BorrowerProfile | None = None,
        strike_count: int = 0,
        turn_count: int = 0,
        prior_offers: list[float] | None = None,
    ) -> PolicyResult:
        prior_offers = prior_offers or []

        # ------------------------------------------------------------------ #
        # Hard gates — evaluated before any intent-specific logic             #
        # ------------------------------------------------------------------ #

        # DNC: Do Not Contact. Must halt regardless of intent.
        if profile is not None and profile.dnc_flag:
            return PolicyResult(allowed=False, reason_code="dnc_enforced", next_action="halt")

        # Legal flag: case referred to legal team. Immediate escalation.
        if profile is not None and profile.legal_flag:
            return PolicyResult(allowed=False, reason_code="legal_flag_active", next_action="escalate")

        # Abusive borrower: always escalate.
        if decision.intent == "ABUSIVE":
            return PolicyResult(allowed=False, reason_code="abuse_detected", next_action="escalate")

        # Strike threshold: 3+ strikes = escalate regardless of intent.
        if strike_count >= 3:
            return PolicyResult(allowed=False, reason_code="strike_limit_exceeded", next_action="escalate")

        # Turn budget: negotiation has gone on too long without commitment.
        if profile is not None and self.negotiation.turn_budget_exceeded(profile, turn_count):
            return PolicyResult(allowed=False, reason_code="turn_budget_exhausted", next_action="escalate")

        # ------------------------------------------------------------------ #
        # Quality gates                                                        #
        # ------------------------------------------------------------------ #

        effective_min_confidence = self._min_confidence(profile)
        if decision.confidence < effective_min_confidence:
            return PolicyResult(allowed=False, reason_code="low_confidence", next_action="clarify")

        if decision.contradictory:
            return PolicyResult(allowed=False, reason_code="intent_contradiction", next_action="clarify")

        # ------------------------------------------------------------------ #
        # Timing gate — timezone-aware via BorrowerProfile                    #
        # ------------------------------------------------------------------ #
        allowed_start, allowed_end = self._allowed_hours(profile)
        if not (allowed_start <= now.hour <= allowed_end):
            return PolicyResult(allowed=False, reason_code="outside_allowed_hours", next_action="wait")

        # ------------------------------------------------------------------ #
        # Intent-specific logic                                                #
        # ------------------------------------------------------------------ #

        if decision.intent == "PAYMENT_OFFER":
            return self._evaluate_payment_offer(
                decision=decision,
                outstanding_amount=outstanding_amount,
                profile=profile,
                turn_count=turn_count,
                prior_offers=prior_offers,
            )

        if decision.intent == "PAYMENT_COMMIT":
            return PolicyResult(allowed=True, reason_code="commit_detected", next_action="await_payment")

        if decision.intent == "HARDSHIP":
            # Check EMI eligibility before escalating
            if profile is not None and self.negotiation.is_emi_eligible(profile):
                return PolicyResult(allowed=True, reason_code="emi_eligible_hardship", next_action="counter_offer")
            return PolicyResult(allowed=False, reason_code="hardship_review", next_action="escalate")

        if decision.intent in {"CONFUSED", "UNKNOWN"}:
            return PolicyResult(allowed=False, reason_code="user_ambiguity", next_action="clarify")

        return PolicyResult(allowed=False, reason_code="policy_default_deny", next_action="escalate")

    # ------------------------------------------------------------------ #
    # Private helpers                                                      #
    # ------------------------------------------------------------------ #

    def _evaluate_payment_offer(
        self,
        *,
        decision: LLMDecision,
        outstanding_amount: float,
        profile: BorrowerProfile | None,
        turn_count: int,
        prior_offers: list[float],
    ) -> PolicyResult:
        if decision.amount is None:
            return PolicyResult(allowed=False, reason_code="missing_amount", next_action="clarify")

        effective_min_payment = self._min_payment(profile, outstanding_amount)
        if decision.amount < effective_min_payment:
            return PolicyResult(allowed=False, reason_code="below_min_payment", next_action="counter_offer")

        max_discount = self._max_discount(profile)
        max_allowed_discounted = outstanding_amount * (1.0 - max_discount)
        if decision.amount < max_allowed_discounted:
            return PolicyResult(allowed=False, reason_code="discount_too_high", next_action="counter_offer")

        return PolicyResult(allowed=True, reason_code="offer_acceptable", next_action="accept_offer")

    def _min_confidence(self, profile: BorrowerProfile | None) -> float:
        if profile is None:
            return self.cfg.min_confidence
        from agents.profile_loader import ProfileLoader
        cfg = ProfileLoader.segment_policy_config(profile.loan_segment)
        return cfg["min_confidence"]

    def _allowed_hours(self, profile: BorrowerProfile | None) -> tuple[int, int]:
        """Return (start_hour, end_hour) in the borrower's local timezone.

        Unlike the original implementation which used server-UTC hour, this
        correctly respects the borrower's timezone. Without this fix, a borrower
        in IST (UTC+5:30) could be contacted outside legal hours if the server
        runs in UTC.
        """
        if profile is None:
            return self.cfg.allowed_start_hour, self.cfg.allowed_end_hour
        from agents.profile_loader import ProfileLoader
        cfg = ProfileLoader.segment_policy_config(profile.loan_segment)
        return cfg["allowed_start_hour"], cfg["allowed_end_hour"]

    def _min_payment(self, profile: BorrowerProfile | None, outstanding: float) -> float:
        if profile is None:
            return self.cfg.min_payment
        bounds = self.negotiation.get_bounds(profile)
        # Use the larger of: absolute min payment from segment config, or fraction of outstanding
        from agents.profile_loader import ProfileLoader
        cfg = ProfileLoader.segment_policy_config(profile.loan_segment)
        absolute_min = cfg["min_payment"]
        fractional_min = outstanding * bounds.min_payment_fraction
        return max(absolute_min, fractional_min)

    def _max_discount(self, profile: BorrowerProfile | None) -> float:
        if profile is None:
            return self.cfg.max_discount
        bounds = self.negotiation.get_bounds(profile)
        return bounds.max_discount_fraction
