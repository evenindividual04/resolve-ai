from __future__ import annotations

from datetime import datetime

from domain.borrower import BorrowerProfile, ContactChannel


# Escalation sequence: which channel to try at each contact attempt number
_ESCALATION_SEQUENCE: list[ContactChannel] = [
    ContactChannel.WHATSAPP,
    ContactChannel.WHATSAPP,
    ContactChannel.SMS,
    ContactChannel.EMAIL,
    ContactChannel.VOICE,
]

# Per-timezone allowed contact windows (start_hour, end_hour) in local time
# Based on TRAI regulations: no contact before 9am or after 9pm local time.
_DEFAULT_WINDOW = (9, 21)

# Segment-specific tighter windows (business: 9-17 to match office hours)
_SEGMENT_WINDOWS: dict[str, tuple[int, int]] = {
    "business": (9, 17),
    "personal": (9, 21),
    "credit_card": (9, 21),
    "gold": (9, 18),
    "vehicle": (9, 18),
}


class ChannelRouter:
    """Selects the optimal contact channel for a borrower.

    Design decisions vs the original:
    - DNC is a hard gate: if dnc_flag is set, no channel is ever returned.
    - Allowed hours use the borrower's local timezone, not server UTC.
      The original code used `now.hour` which is UTC on most servers,
      giving wrong results for borrowers in IST (UTC+5:30).
    - Escalation sequence: WhatsApp first (highest open rate), then SMS,
      email, voice — based on typical debt collection response rates.
    - Preferred channel from BorrowerProfile is honored on attempts 1-2.
      Beyond that, the system escalates to the next channel regardless.
    """

    def select_channel(
        self,
        profile: BorrowerProfile,
        attempt_number: int,
        now: datetime,
    ) -> str:
        """Return the channel to use for the given contact attempt.

        Returns "halt" if DNC is active or contact window is closed.
        """
        # Hard gate: Do Not Contact
        if profile.dnc_flag:
            return "halt"

        # Hard gate: Legal flag — no agent contact, only legal team
        if profile.legal_flag:
            return "halt"

        # Timing gate: borrower's local hour
        local_hour = self._local_hour(now, profile.timezone)
        window = _SEGMENT_WINDOWS.get(profile.loan_segment.value, _DEFAULT_WINDOW)
        if not (window[0] <= local_hour < window[1]):
            return "wait"

        # For first two attempts, honour preferred channel
        if attempt_number <= 2:
            return profile.preferred_channel.value

        # Beyond attempt 2, escalate through the sequence
        idx = min(attempt_number - 1, len(_ESCALATION_SEQUENCE) - 1)
        return _ESCALATION_SEQUENCE[idx].value

    def is_contact_allowed(self, profile: BorrowerProfile, now: datetime) -> bool:
        """True if contact is permitted right now for this borrower."""
        if profile.dnc_flag or profile.legal_flag:
            return False
        local_hour = self._local_hour(now, profile.timezone)
        window = _SEGMENT_WINDOWS.get(profile.loan_segment.value, _DEFAULT_WINDOW)
        return window[0] <= local_hour < window[1]

    @staticmethod
    def _local_hour(now: datetime, timezone_str: str) -> int:
        """Convert UTC datetime to borrower's local hour.

        Uses a lookup table for common Indian timezones to avoid a pytz dependency.
        For production, replace with zoneinfo (Python 3.9+) or pytz.
        """
        # UTC offsets for common zones in this use-case
        tz_offsets: dict[str, float] = {
            "Asia/Kolkata": 5.5,
            "Asia/Calcutta": 5.5,
            "Asia/Mumbai": 5.5,
            "Asia/Delhi": 5.5,
            "Asia/Colombo": 5.5,
            "Asia/Dubai": 4.0,
            "UTC": 0.0,
        }
        offset_hours = tz_offsets.get(timezone_str, 5.5)  # Default to IST
        utc_hour = now.hour + now.minute / 60.0
        local_hour = (utc_hour + offset_hours) % 24
        return int(local_hour)
