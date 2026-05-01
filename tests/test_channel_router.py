"""Tests for ChannelRouter: timezone-aware hours, DNC, escalation sequence."""
from __future__ import annotations

from datetime import datetime, timezone

import pytest

from domain.borrower import BorrowerProfile, ContactChannel, LoanSegment
from domain.channel_router import ChannelRouter


router = ChannelRouter()


def _profile(**kw) -> BorrowerProfile:
    return BorrowerProfile(user_id="u1", outstanding_amount=10000.0, **kw)


def _utc(hour: int) -> datetime:
    return datetime(2024, 6, 15, hour, 0, 0, tzinfo=timezone.utc)


def test_dnc_flag_returns_halt():
    profile = _profile(dnc_flag=True, preferred_channel=ContactChannel.WHATSAPP)
    result = router.select_channel(profile, attempt_number=1, now=_utc(10))
    assert result == "halt"


def test_legal_flag_returns_halt():
    profile = _profile(legal_flag=True, preferred_channel=ContactChannel.SMS)
    result = router.select_channel(profile, attempt_number=1, now=_utc(10))
    assert result == "halt"


def test_preferred_channel_used_for_first_two_attempts():
    profile = _profile(preferred_channel=ContactChannel.EMAIL, loan_segment=LoanSegment.PERSONAL)
    # UTC 10:00 = IST 15:30 → within allowed window
    for attempt in [1, 2]:
        result = router.select_channel(profile, attempt_number=attempt, now=_utc(10))
        assert result == ContactChannel.EMAIL.value


def test_escalation_channel_beyond_attempt_2():
    profile = _profile(preferred_channel=ContactChannel.EMAIL, loan_segment=LoanSegment.PERSONAL)
    result = router.select_channel(profile, attempt_number=3, now=_utc(10))
    assert result == ContactChannel.SMS.value


def test_outside_allowed_window_returns_wait():
    profile = _profile(preferred_channel=ContactChannel.SMS, loan_segment=LoanSegment.PERSONAL, timezone="Asia/Kolkata")
    # UTC 22:00 = IST 03:30 → outside allowed window (9-21 IST)
    result = router.select_channel(profile, attempt_number=1, now=_utc(22))
    assert result == "wait"


def test_ist_timezone_calculation():
    profile = _profile(preferred_channel=ContactChannel.SMS, timezone="Asia/Kolkata")
    # UTC 04:00 = IST 09:30 → inside window (9-21)
    result = router.is_contact_allowed(profile, _utc(4))
    assert result is True
    # UTC 16:00 = IST 21:30 → outside window
    result2 = router.is_contact_allowed(profile, _utc(16))
    assert result2 is False


def test_business_segment_tighter_window():
    profile = _profile(preferred_channel=ContactChannel.SMS, loan_segment=LoanSegment.BUSINESS, timezone="Asia/Kolkata")
    # UTC 12:00 = IST 17:30 → outside business hours (9-17 IST)
    result = router.is_contact_allowed(profile, _utc(12))
    assert result is False
