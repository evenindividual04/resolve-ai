from __future__ import annotations

from enum import Enum
from hashlib import sha256

from pydantic import BaseModel, ConfigDict, Field


class RiskBand(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class LoanSegment(str, Enum):
    PERSONAL = "personal"
    CREDIT_CARD = "credit_card"
    BUSINESS = "business"
    GOLD = "gold"
    VEHICLE = "vehicle"


class ContactChannel(str, Enum):
    WHATSAPP = "whatsapp"
    SMS = "sms"
    EMAIL = "email"
    VOICE = "voice"


class BorrowerProfile(BaseModel):
    """Central domain entity representing a borrower in the collections system.

    This model feeds all downstream decisions: policy evaluation, LLM prompt
    construction, channel routing, and compliance enforcement. It is the primary
    abstraction that separates a generic AI agent from a domain-aware collections
    system.
    """

    model_config = ConfigDict(extra="forbid")

    user_id: str
    risk_band: RiskBand = RiskBand.MEDIUM
    loan_segment: LoanSegment = LoanSegment.PERSONAL
    outstanding_amount: float = 0.0
    dpd: int = Field(default=0, ge=0, description="Days past due")
    prior_defaults: int = Field(default=0, ge=0)
    contact_attempts: int = Field(default=0, ge=0)
    preferred_channel: ContactChannel = ContactChannel.SMS
    language: str = "en"
    timezone: str = "Asia/Kolkata"
    dnc_flag: bool = False   # Do Not Contact — contacts must stop immediately
    legal_flag: bool = False  # Case referred to legal — escalate immediately
    notes: str = ""


# ---------------------------------------------------------------------------
# Persona archetypes used by BorrowerSimulator and ProfileLoader
# ---------------------------------------------------------------------------

PERSONA_PROFILES: dict[str, dict] = {
    "cooperative": {
        "risk_band": RiskBand.LOW,
        "loan_segment": LoanSegment.PERSONAL,
        "dpd": 15,
        "prior_defaults": 0,
        "preferred_channel": ContactChannel.WHATSAPP,
        "language": "en",
    },
    "negotiator": {
        "risk_band": RiskBand.MEDIUM,
        "loan_segment": LoanSegment.PERSONAL,
        "dpd": 45,
        "prior_defaults": 1,
        "preferred_channel": ContactChannel.SMS,
        "language": "en",
    },
    "ghost": {
        "risk_band": RiskBand.HIGH,
        "loan_segment": LoanSegment.CREDIT_CARD,
        "dpd": 90,
        "prior_defaults": 2,
        "preferred_channel": ContactChannel.SMS,
        "language": "en",
    },
    "liar": {
        "risk_band": RiskBand.HIGH,
        "loan_segment": LoanSegment.PERSONAL,
        "dpd": 60,
        "prior_defaults": 2,
        "preferred_channel": ContactChannel.WHATSAPP,
        "language": "en",
    },
    "distressed": {
        "risk_band": RiskBand.MEDIUM,
        "loan_segment": LoanSegment.PERSONAL,
        "dpd": 30,
        "prior_defaults": 0,
        "preferred_channel": ContactChannel.EMAIL,
        "language": "en",
    },
    "adversarial": {
        "risk_band": RiskBand.CRITICAL,
        "loan_segment": LoanSegment.BUSINESS,
        "dpd": 120,
        "prior_defaults": 3,
        "preferred_channel": ContactChannel.VOICE,
        "language": "en",
    },
}


def _hash_persona(user_id: str) -> str:
    """Deterministically map a user_id to a persona for replay consistency."""
    digest = int(sha256(user_id.encode()).hexdigest(), 16)
    personas = list(PERSONA_PROFILES.keys())
    return personas[digest % len(personas)]
