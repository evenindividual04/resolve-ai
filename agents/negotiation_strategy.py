from __future__ import annotations

from dataclasses import dataclass

from domain.borrower import BorrowerProfile, LoanSegment, RiskBand
from domain.models import BehaviorPattern, NegotiationStrategyType


@dataclass(frozen=True)
class NegotiationBounds:
    """Discount floor/ceiling and turn budget for a given segment + risk band."""
    min_payment_fraction: float   # Minimum acceptable as fraction of outstanding
    max_discount_fraction: float  # Maximum discount we will ever grant
    max_turns: int                # Escalate after this many turns without commitment
    emi_eligible: bool            # Whether to offer EMI schedule instead of lump sum


# Segment × risk band policy matrix
_BOUNDS: dict[LoanSegment, dict[RiskBand, NegotiationBounds]] = {
    LoanSegment.PERSONAL: {
        RiskBand.LOW:      NegotiationBounds(0.85, 0.15, 5, False),
        RiskBand.MEDIUM:   NegotiationBounds(0.75, 0.25, 5, True),
        RiskBand.HIGH:     NegotiationBounds(0.65, 0.35, 4, True),
        RiskBand.CRITICAL: NegotiationBounds(0.50, 0.50, 3, True),
    },
    LoanSegment.CREDIT_CARD: {
        RiskBand.LOW:      NegotiationBounds(0.90, 0.10, 4, False),
        RiskBand.MEDIUM:   NegotiationBounds(0.80, 0.20, 4, False),
        RiskBand.HIGH:     NegotiationBounds(0.70, 0.30, 3, True),
        RiskBand.CRITICAL: NegotiationBounds(0.55, 0.45, 2, True),
    },
    LoanSegment.BUSINESS: {
        RiskBand.LOW:      NegotiationBounds(0.90, 0.10, 8, False),
        RiskBand.MEDIUM:   NegotiationBounds(0.85, 0.15, 8, True),
        RiskBand.HIGH:     NegotiationBounds(0.75, 0.25, 6, True),
        RiskBand.CRITICAL: NegotiationBounds(0.60, 0.40, 4, True),
    },
    LoanSegment.GOLD: {
        RiskBand.LOW:      NegotiationBounds(0.95, 0.05, 3, False),
        RiskBand.MEDIUM:   NegotiationBounds(0.90, 0.10, 3, False),
        RiskBand.HIGH:     NegotiationBounds(0.80, 0.20, 2, False),
        RiskBand.CRITICAL: NegotiationBounds(0.70, 0.30, 2, False),
    },
    LoanSegment.VEHICLE: {
        RiskBand.LOW:      NegotiationBounds(0.88, 0.12, 5, False),
        RiskBand.MEDIUM:   NegotiationBounds(0.78, 0.22, 5, True),
        RiskBand.HIGH:     NegotiationBounds(0.68, 0.32, 4, True),
        RiskBand.CRITICAL: NegotiationBounds(0.55, 0.45, 3, True),
    },
}


class NegotiationStrategy:
    """Computes counter-offer amounts and manages multi-turn negotiation logic.

    Design decisions:
    - Risk-band × segment matrix drives discount floor/ceiling so a PERSONAL/LOW
      borrower never gets the same terms as a BUSINESS/CRITICAL borrower.
    - Anchoring detection: if borrower offers < 50% of the minimum acceptable,
      we hold firm for 2 turns before conceding — this avoids rewarding low anchors.
    - Turn budget enforced per segment: business cases get 8 turns (relationship-oriented),
      credit card gets 4 (high-volume, low-margin). Exceeding budget auto-escalates.
    - EMI schedule offered when lump-sum resolution is unlikely (HIGH/CRITICAL bands).
    """

    def __init__(self):
        self.strategy_metrics = {s: {"successes": 0, "total": 0} for s in NegotiationStrategyType}

    def record_outcome(self, strategy: NegotiationStrategyType, success: bool) -> None:
        self.strategy_metrics[strategy]["total"] += 1
        if success:
            self.strategy_metrics[strategy]["successes"] += 1

    def get_best_strategy(self) -> NegotiationStrategyType:
        best_strat = NegotiationStrategyType.PRAGMATIC
        best_rate = -1.0
        for s, metrics in self.strategy_metrics.items():
            if metrics["total"] >= 5:
                rate = metrics["successes"] / metrics["total"]
                if rate > best_rate:
                    best_rate = rate
                    best_strat = s
        return best_strat

    def get_bounds(
        self,
        profile: BorrowerProfile,
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> NegotiationBounds:
        segment_map = _BOUNDS.get(profile.loan_segment, _BOUNDS[LoanSegment.PERSONAL])
        base = segment_map.get(profile.risk_band, segment_map[RiskBand.MEDIUM])

        min_pay = base.min_payment_fraction
        max_disc = base.max_discount_fraction
        turns = base.max_turns
        emi = base.emi_eligible

        if strategy == NegotiationStrategyType.FIRM or behavior == BehaviorPattern.DELAYING:
            turns = max(2, turns - 1)
            max_disc = max(0.0, max_disc - 0.05)
            min_pay = min(1.0, min_pay + 0.05)
        elif strategy == NegotiationStrategyType.EMPATHETIC or behavior == BehaviorPattern.COMPLIANT:
            turns += 2
            max_disc = min(0.6, max_disc + 0.10)
            emi = True

        return NegotiationBounds(
            min_payment_fraction=min_pay,
            max_discount_fraction=max_disc,
            max_turns=turns,
            emi_eligible=emi,
        )

    def compute_counter_offer(
        self,
        outstanding: float,
        profile: BorrowerProfile,
        turn_count: int,
        prior_offers: list[float],
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> float:
        bounds = self.get_bounds(profile, strategy, behavior)
        floor = outstanding * bounds.min_payment_fraction

        if prior_offers and min(prior_offers) < floor * 0.5:
            if turn_count <= 2:
                return round(floor, 2)

        concession_turns = max(0, turn_count - 2)
        concession = floor * 0.05 * concession_turns
        hard_floor = outstanding * (1.0 - bounds.max_discount_fraction)
        counter = max(floor - concession, hard_floor)
        return round(counter, 2)

    def compute_emi_schedule(
        self,
        outstanding: float,
        profile: BorrowerProfile,
        months: int = 3,
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> list[float]:
        bounds = self.get_bounds(profile, strategy, behavior)
        if not bounds.emi_eligible:
            return []
        settled = outstanding * (1.0 - bounds.max_discount_fraction * 0.5)
        monthly = settled / months
        return [round(monthly, 2)] * months

    def turn_budget_exceeded(
        self,
        profile: BorrowerProfile,
        turn_count: int,
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> bool:
        bounds = self.get_bounds(profile, strategy, behavior)
        return turn_count >= bounds.max_turns

    def is_emi_eligible(
        self,
        profile: BorrowerProfile,
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> bool:
        return self.get_bounds(profile, strategy, behavior).emi_eligible

    def should_hold_firm(
        self,
        outstanding: float,
        profile: BorrowerProfile,
        prior_offers: list[float],
        turn_count: int,
        strategy: NegotiationStrategyType = NegotiationStrategyType.PRAGMATIC,
        behavior: BehaviorPattern = BehaviorPattern.COMPLIANT,
    ) -> bool:
        if not prior_offers:
            return False
        bounds = self.get_bounds(profile, strategy, behavior)
        floor = outstanding * bounds.min_payment_fraction
        is_aggressive_anchor = min(prior_offers) < floor * 0.5
        return is_aggressive_anchor and turn_count <= 2
