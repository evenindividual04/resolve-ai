"""Tests for NegotiationStrategy: counter-offer, turn budget, EMI, anchoring."""
from __future__ import annotations

import pytest

from agents.negotiation_strategy import NegotiationStrategy
from agents.profile_loader import ProfileLoader
from domain.borrower import LoanSegment, RiskBand


def _profile(segment=LoanSegment.PERSONAL, risk=RiskBand.MEDIUM, **kw):
    return ProfileLoader().load_persona("user-test", "negotiator", 10000.0)


strategy = NegotiationStrategy()


def test_counter_offer_within_bounds():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "negotiator", 10000.0)
    offer = strategy.compute_counter_offer(10000.0, profile, turn_count=1, prior_offers=[6000.0])
    bounds = strategy.get_bounds(profile)
    assert offer >= 10000.0 * (1 - bounds.max_discount_fraction)
    assert offer <= 10000.0


def test_counter_offer_hold_firm_on_aggressive_anchor():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "negotiator", 10000.0)
    # Borrower offered 40% of outstanding — very aggressive anchor
    offer_turn1 = strategy.compute_counter_offer(10000.0, profile, turn_count=1, prior_offers=[4000.0])
    offer_turn3 = strategy.compute_counter_offer(10000.0, profile, turn_count=3, prior_offers=[4000.0])
    # Turn 1 should hold firm (no concession), turn 3 may concede
    assert offer_turn1 >= offer_turn3 or offer_turn1 == offer_turn3


def test_turn_budget_exceeded():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "cooperative", 10000.0)  # cooperative = low risk, personal
    bounds = strategy.get_bounds(profile)
    assert not strategy.turn_budget_exceeded(profile, bounds.max_turns - 1)
    assert strategy.turn_budget_exceeded(profile, bounds.max_turns)


def test_emi_schedule_for_eligible_profile():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "distressed", 9000.0)
    # distressed → MEDIUM risk PERSONAL → EMI eligible
    emi = strategy.compute_emi_schedule(9000.0, profile, months=3)
    assert len(emi) == 3
    assert all(e > 0 for e in emi)
    # Each EMI = settled / months. Settled = outstanding * (1 - max_discount * 0.5)
    bounds = strategy.get_bounds(profile)
    expected_settled = 9000.0 * (1 - bounds.max_discount_fraction * 0.5)
    expected_monthly = expected_settled / 3
    assert abs(emi[0] - expected_monthly) < 1.0


def test_emi_not_offered_for_ineligible_profile():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "cooperative", 10000.0)  # LOW risk → not eligible
    bounds = strategy.get_bounds(profile)
    if not bounds.emi_eligible:
        emi = strategy.compute_emi_schedule(10000.0, profile, months=3)
        assert emi == []


def test_should_hold_firm_on_aggressive_anchor():
    loader = ProfileLoader()
    profile = loader.load_persona("u1", "negotiator", 10000.0)
    # Prior offer is 30% of outstanding — very aggressive
    assert strategy.should_hold_firm(10000.0, profile, prior_offers=[3000.0], turn_count=1)
    # Not aggressive (75% of outstanding)
    assert not strategy.should_hold_firm(10000.0, profile, prior_offers=[7500.0], turn_count=1)
