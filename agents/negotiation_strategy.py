from __future__ import annotations

from dataclasses import dataclass

from domain.borrower import BorrowerProfile, LoanSegment, RiskBand


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

    def get_bounds(self, profile: BorrowerProfile) -> NegotiationBounds:
        segment_map = _BOUNDS.get(profile.loan_segment, _BOUNDS[LoanSegment.PERSONAL])
        return segment_map.get(profile.risk_band, segment_map[RiskBand.MEDIUM])

    def compute_counter_offer(
        self,
        outstanding: float,
        profile: BorrowerProfile,
        turn_count: int,
        prior_offers: list[float],
    ) -> float:
        """Return the counter-offer amount to propose to the borrower.

        Concession strategy: start at the minimum acceptable floor.
        If borrower persists across turns, concede by 5% per turn beyond turn 2,
        down to the maximum discount floor. This is a deliberate, bounded concession
        curve — not a random number.
        """
        bounds = self.get_bounds(profile)
        floor = outstanding * bounds.min_payment_fraction

        # Detect aggressive anchor: borrower offering < 50% of floor
        if prior_offers and min(prior_offers) < floor * 0.5:
            # Hold firm for 2 turns before any concession
            if turn_count <= 2:
                return round(floor, 2)

        # Concession curve: 5% of floor per turn beyond turn 2, bounded by max discount
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
    ) -> list[float]:
        """Return a monthly EMI schedule for the given outstanding amount.

        EMI is only offered when the profile's segment × risk band is EMI-eligible.
        """
        bounds = self.get_bounds(profile)
        if not bounds.emi_eligible:
            return []
        # Apply the maximum discount to get settled amount, then split into monthly EMIs
        settled = outstanding * (1.0 - bounds.max_discount_fraction * 0.5)  # 50% of max discount for EMI
        monthly = settled / months
        return [round(monthly, 2)] * months

    def turn_budget_exceeded(self, profile: BorrowerProfile, turn_count: int) -> bool:
        """Return True when negotiation turn budget is exhausted.

        Exceeding the turn budget means the borrower is stalling. The policy engine
        should escalate rather than allow infinite clarification loops.
        """
        bounds = self.get_bounds(profile)
        return turn_count >= bounds.max_turns

    def is_emi_eligible(self, profile: BorrowerProfile) -> bool:
        return self.get_bounds(profile).emi_eligible

    def should_hold_firm(
        self,
        outstanding: float,
        profile: BorrowerProfile,
        prior_offers: list[float],
        turn_count: int,
    ) -> bool:
        """Return True if we should hold firm (not concede) on this turn."""
        if not prior_offers:
            return False
        bounds = self.get_bounds(profile)
        floor = outstanding * bounds.min_payment_fraction
        is_aggressive_anchor = min(prior_offers) < floor * 0.5
        return is_aggressive_anchor and turn_count <= 2
