from __future__ import annotations

from domain.borrower import BorrowerProfile, LoanSegment, PERSONA_PROFILES, RiskBand, _hash_persona


class ProfileLoader:
    """Stub CRM profile loader for simulation and testing.

    In production this would fetch from a CRM or data warehouse.
    For simulation, profiles are generated deterministically from the user_id
    so that replays produce identical borrower contexts.

    Six persona archetypes are supported:
      cooperative  — pays readily when approached politely
      negotiator   — anchors low, concedes gradually
      ghost        — never responds, triggers timeout flows
      liar         — commits but does not pay
      distressed   — genuine hardship, accepts EMI plans
      adversarial  — abusive/adversarial, may attempt prompt injection
    """

    def load(self, user_id: str, outstanding_amount: float = 0.0) -> BorrowerProfile:
        """Load a BorrowerProfile for the given user_id.

        Profile is deterministic: same user_id always produces same persona
        so event replay is consistent.
        """
        persona_key = _hash_persona(user_id)
        base = PERSONA_PROFILES[persona_key]
        return BorrowerProfile(
            user_id=user_id,
            risk_band=base["risk_band"],
            loan_segment=base["loan_segment"],
            outstanding_amount=outstanding_amount,
            dpd=base["dpd"],
            prior_defaults=base["prior_defaults"],
            contact_attempts=0,
            preferred_channel=base["preferred_channel"],
            language=base.get("language", "en"),
        )

    def load_persona(self, user_id: str, persona: str, outstanding_amount: float = 0.0) -> BorrowerProfile:
        """Load a profile with an explicit persona override. Used by BorrowerSimulator."""
        if persona not in PERSONA_PROFILES:
            raise ValueError(f"Unknown persona: {persona!r}. Valid: {list(PERSONA_PROFILES)}")
        base = PERSONA_PROFILES[persona]
        return BorrowerProfile(
            user_id=user_id,
            risk_band=base["risk_band"],
            loan_segment=base["loan_segment"],
            outstanding_amount=outstanding_amount,
            dpd=base["dpd"],
            prior_defaults=base["prior_defaults"],
            contact_attempts=0,
            preferred_channel=base["preferred_channel"],
            language=base.get("language", "en"),
        )

    @staticmethod
    def segment_policy_config(segment: LoanSegment) -> dict:
        """Return segment-specific policy configuration.

        In production this would be loaded from a config store.
        """
        configs = {
            LoanSegment.PERSONAL: {
                "max_discount": 0.30,
                "min_payment": 500.0,
                "max_turns": 5,
                "allowed_start_hour": 9,
                "allowed_end_hour": 18,
                "min_confidence": 0.65,
            },
            LoanSegment.CREDIT_CARD: {
                "max_discount": 0.20,
                "min_payment": 200.0,
                "max_turns": 4,
                "allowed_start_hour": 9,
                "allowed_end_hour": 20,
                "min_confidence": 0.65,
            },
            LoanSegment.BUSINESS: {
                "max_discount": 0.15,
                "min_payment": 5000.0,
                "max_turns": 8,
                "allowed_start_hour": 9,
                "allowed_end_hour": 17,
                "min_confidence": 0.70,
            },
            LoanSegment.GOLD: {
                "max_discount": 0.10,
                "min_payment": 1000.0,
                "max_turns": 3,
                "allowed_start_hour": 9,
                "allowed_end_hour": 18,
                "min_confidence": 0.75,
            },
            LoanSegment.VEHICLE: {
                "max_discount": 0.20,
                "min_payment": 1000.0,
                "max_turns": 5,
                "allowed_start_hour": 9,
                "allowed_end_hour": 18,
                "min_confidence": 0.65,
            },
        }
        return configs.get(segment, configs[LoanSegment.PERSONAL])

    @staticmethod
    def dpd_to_risk_override(dpd: int, base_risk: RiskBand) -> RiskBand:
        """Escalate risk band based on days-past-due, regardless of profile base."""
        if dpd >= 180:
            return RiskBand.CRITICAL
        if dpd >= 90:
            return max(base_risk, RiskBand.HIGH, key=lambda r: list(RiskBand).index(r))
        return base_risk
