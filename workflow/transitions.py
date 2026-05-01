from __future__ import annotations

from domain.models import PolicyResult, WorkflowState, WorkflowStatus


class TransitionError(ValueError):
    pass


def apply_transition(state: WorkflowState, policy: PolicyResult) -> WorkflowState:
    src = state.current_state
    action = policy.next_action

    if action == "escalate":
        state.current_state = WorkflowStatus.ESCALATED
    elif src == WorkflowStatus.INIT:
        state.current_state = WorkflowStatus.CONTACTED
    elif src in {WorkflowStatus.CONTACTED, WorkflowStatus.REVALIDATION_REQUIRED} and action in {"accept_offer", "clarify", "counter_offer"}:
        state.current_state = WorkflowStatus.NEGOTIATING
    elif src == WorkflowStatus.NEGOTIATING and action == "await_payment":
        state.current_state = WorkflowStatus.WAITING_FOR_PAYMENT
    elif src == WorkflowStatus.WAITING_FOR_PAYMENT and action == "resolve":
        state.current_state = WorkflowStatus.RESOLVED
    elif src == WorkflowStatus.WAITING_FOR_PAYMENT and action == "payment_failed":
        state.current_state = WorkflowStatus.PAYMENT_FAILED
    elif src in {WorkflowStatus.CONTACTED, WorkflowStatus.NEGOTIATING, WorkflowStatus.WAITING_FOR_PAYMENT, WorkflowStatus.REVALIDATION_REQUIRED} and action in {"clarify", "counter_offer", "wait"}:
        # remain in current state for bounded clarification loop
        state.current_state = src
    else:
        raise TransitionError(f"illegal transition: {src} with action {action}")

    if state.current_state not in WorkflowStatus:
        raise TransitionError("invalid state")

    return state
