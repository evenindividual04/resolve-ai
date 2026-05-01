"""Tests for ComplianceGuard output filter."""
from __future__ import annotations

import pytest

from agents.compliance_guard import ComplianceGuard
from domain.borrower import BorrowerProfile


guard = ComplianceGuard()


def _profile(**kw) -> BorrowerProfile:
    return BorrowerProfile(user_id="u1", outstanding_amount=10000.0, **kw)


def test_clean_message_passes():
    result = guard.check("Please complete your payment by Friday. Thank you.")
    assert result.passed
    assert result.violations == []


def test_threat_language_blocked():
    result = guard.check("Pay now or we will send the police and file an FIR.")
    assert not result.passed
    assert any("threat_language" in v for v in result.violations)


def test_arrest_keyword_blocked():
    result = guard.check("You will be arrested if you don't pay.")
    assert not result.passed


def test_illegal_amount_promise_blocked():
    result = guard.check("We will waive your entire loan balance if you call us.")
    assert not result.passed
    assert any("illegal_amount_promise" in v for v in result.violations)


def test_pii_aadhaar_blocked_and_redacted():
    result = guard.check("Your Aadhaar 123456789012 has been noted.")
    assert not result.passed
    assert any("pii_leakage" in v for v in result.violations)
    assert result.sanitized_text is not None
    assert "123456789012" not in result.sanitized_text
    assert "[REDACTED]" in result.sanitized_text


def test_dnc_flag_blocks_all_messages():
    profile = _profile(dnc_flag=True)
    result = guard.check("Please call us to discuss your outstanding balance.", profile)
    assert not result.passed
    assert any("dnc_violation" in v for v in result.violations)


def test_non_dnc_profile_passes_clean_message():
    profile = _profile(dnc_flag=False)
    result = guard.check("Your payment has been received. Thank you.", profile)
    assert result.passed


def test_is_safe_shortcut():
    assert guard.is_safe("Your payment has been received.")
    assert not guard.is_safe("Pay or we'll have you arrested.")
