from __future__ import annotations

from domain.models import Event, WorkflowState


class ContextBuilder:
    def build(self, state: WorkflowState, event: Event) -> dict:
        return {
            "user_constraints": {
                "outstanding_amount": state.outstanding_amount,
                "negotiated_amount": state.negotiated_amount,
            },
            "last_decision": state.current_state,
            "risk_flags": {
                "strike_count": state.strike_count,
                "stale": self._is_stale(state, event),
            },
            "relevant_events": [
                {"event_type": event.event_type.value, "channel": event.channel},
            ],
        }

    @staticmethod
    def _is_stale(state: WorkflowState, event: Event) -> bool:
        e = event.occurred_at if event.occurred_at.tzinfo else event.occurred_at.replace(tzinfo=__import__("datetime").UTC)
        s = state.updated_at if state.updated_at.tzinfo else state.updated_at.replace(tzinfo=__import__("datetime").UTC)
        age_hours = (e - s).total_seconds() / 3600
        return age_hours > state.stale_after_hours
