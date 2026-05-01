from __future__ import annotations

from datetime import UTC
from typing import TYPE_CHECKING

from domain.models import Event, WorkflowState

if TYPE_CHECKING:
    from domain.borrower import BorrowerProfile


class ContextBuilder:
    def build(self, state: WorkflowState, event: Event, profile: BorrowerProfile | None = None) -> dict:
        ctx: dict = {
            "user_constraints": {
                "outstanding_amount": state.outstanding_amount,
                "negotiated_amount": state.negotiated_amount,
                "counter_offer_amount": state.counter_offer_amount,
            },
            "last_decision": state.current_state,
            "negotiation": {
                "turn_count": state.turn_count,
                "prior_offers": state.prior_offers,
                "strike_count": state.strike_count,
            },
            "risk_flags": {
                "strike_count": state.strike_count,
                "stale": self._is_stale(state, event),
            },
            "relevant_events": [
                {"event_type": event.event_type.value, "channel": event.channel},
            ],
        }

        if profile is not None:
            ctx["borrower"] = {
                "risk_band": profile.risk_band.value,
                "loan_segment": profile.loan_segment.value,
                "dpd": profile.dpd,
                "prior_defaults": profile.prior_defaults,
                "preferred_channel": profile.preferred_channel.value,
                "language": profile.language,
                "dnc_flag": profile.dnc_flag,
                "legal_flag": profile.legal_flag,
            }

        return ctx

    @staticmethod
    def _is_stale(state: WorkflowState, event: Event) -> bool:
        e = event.occurred_at if event.occurred_at.tzinfo else event.occurred_at.replace(tzinfo=UTC)
        s = state.updated_at if state.updated_at.tzinfo else state.updated_at.replace(tzinfo=UTC)
        age_hours = (e - s).total_seconds() / 3600
        return age_hours > state.stale_after_hours
