"""Tests for BorrowerProfile domain model and ProfileLoader."""
from __future__ import annotations

import pytest

from domain.borrower import BorrowerProfile, ContactChannel, LoanSegment, RiskBand
from agents.profile_loader import ProfileLoader


def test_profile_loader_deterministic():
    """Same user_id must always produce same persona (for replay consistency)."""
    loader = ProfileLoader()
    p1 = loader.load("user-abc-123", outstanding_amount=10000.0)
    p2 = loader.load("user-abc-123", outstanding_amount=10000.0)
    assert p1.risk_band == p2.risk_band
    assert p1.loan_segment == p2.loan_segment
    assert p1.preferred_channel == p2.preferred_channel


def test_profile_loader_persona_override():
    loader = ProfileLoader()
    p = loader.load_persona("any-user", "cooperative", 5000.0)
    assert p.risk_band == RiskBand.LOW
    assert p.dpd == 15


def test_profile_loader_unknown_persona_raises():
    loader = ProfileLoader()
    with pytest.raises(ValueError, match="Unknown persona"):
        loader.load_persona("user", "unicorn", 1000.0)


def test_borrower_profile_dnc_flag():
    profile = BorrowerProfile(
        user_id="u1",
        dnc_flag=True,
        outstanding_amount=10000.0,
    )
    assert profile.dnc_flag is True


def test_borrower_profile_legal_flag():
    profile = BorrowerProfile(
        user_id="u1",
        legal_flag=True,
        outstanding_amount=5000.0,
    )
    assert profile.legal_flag is True


def test_segment_policy_config_varies_by_segment():
    personal = ProfileLoader.segment_policy_config(LoanSegment.PERSONAL)
    business = ProfileLoader.segment_policy_config(LoanSegment.BUSINESS)
    assert personal["max_turns"] != business["max_turns"]
    assert personal["min_payment"] != business["min_payment"]


def test_dpd_risk_override_escalates():
    base = RiskBand.MEDIUM
    result = ProfileLoader.dpd_to_risk_override(180, base)
    assert result == RiskBand.CRITICAL

    result2 = ProfileLoader.dpd_to_risk_override(91, base)
    assert result2 == RiskBand.HIGH


def test_all_personas_loadable():
    loader = ProfileLoader()
    for persona in ["cooperative", "negotiator", "ghost", "liar", "distressed", "adversarial"]:
        p = loader.load_persona(f"user-{persona}", persona, 1000.0)
        assert isinstance(p, BorrowerProfile)
