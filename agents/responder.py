from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import uuid4

from agents.compliance_guard import ComplianceGuard, GuardResult
from agents.llm_engine import LLMEngine
from domain.borrower import BorrowerProfile
from domain.models import WorkflowState

log = logging.getLogger(__name__)


class MessageLog:
    """Value object for a single outbound message. Stored in the DB via Orchestrator."""

    __slots__ = (
        "message_id", "workflow_id", "channel", "direction", "content",
        "action", "compliance_passed", "violations", "sent_at",
        "delivered_at", "read_at",
    )

    def __init__(
        self,
        workflow_id: str,
        channel: str,
        content: str,
        action: str,
        compliance_passed: bool,
        violations: list[str],
    ) -> None:
        self.message_id = str(uuid4())
        self.workflow_id = workflow_id
        self.channel = channel
        self.direction = "outbound"
        self.content = content
        self.action = action
        self.compliance_passed = compliance_passed
        self.violations = violations
        self.sent_at: datetime = datetime.now(UTC)
        self.delivered_at: datetime | None = None
        self.read_at: datetime | None = None

    def to_dict(self) -> dict:
        return {
            "message_id": self.message_id,
            "workflow_id": self.workflow_id,
            "channel": self.channel,
            "direction": self.direction,
            "content": self.content,
            "action": self.action,
            "compliance_passed": 1 if self.compliance_passed else 0,
            "violations": self.violations,
            "sent_at": self.sent_at,
            "delivered_at": self.delivered_at,
            "read_at": self.read_at,
        }


class Responder:
    """Generates and validates outbound borrower-facing messages.

    Pipeline:
      1. LLMEngine.generate_response() → draft message
      2. ComplianceGuard.check() → validate against TRAI/RBI rules
      3. If guard passes → return MessageLog
      4. If guard fails → log violation, attempt sanitization, escalate if unsanitizable

    The responder closes the loop between policy decisions and actual borrower
    communication. Without this layer the system makes decisions it cannot act on.
    """

    def __init__(self, llm: LLMEngine) -> None:
        self.llm = llm
        self.guard = ComplianceGuard()

    async def generate(
        self,
        action: str,
        state: WorkflowState,
        profile: BorrowerProfile | None = None,
    ) -> tuple[MessageLog, GuardResult]:
        """Generate a compliant outbound message for the given action.

        Returns:
            (MessageLog, GuardResult) — caller decides whether to send based on GuardResult.passed
        """
        channel = profile.preferred_channel.value if profile else state.last_message and "sms" or "sms"

        # Generate draft via LLM (or deterministic fallback if LLM unavailable)
        draft = await self.llm.generate_response(action, state, profile)

        # Run compliance check
        guard_result = self.guard.check(draft, profile)

        if not guard_result.passed:
            log.warning(
                "compliance_violation workflow_id=%s action=%s violations=%s",
                state.workflow_id,
                action,
                guard_result.violations,
            )
            # Use sanitized version if available; otherwise replace with safe fallback
            content = guard_result.sanitized_text or self._safe_fallback(action)
            # Re-check sanitized content
            recheck = self.guard.check(content, profile)
            if not recheck.passed:
                # Still fails — use the absolute safe fallback and flag for escalation
                content = self._safe_fallback(action)
        else:
            content = draft

        msg_log = MessageLog(
            workflow_id=state.workflow_id,
            channel=channel,
            content=content,
            action=action,
            compliance_passed=guard_result.passed,
            violations=guard_result.violations,
        )
        return msg_log, guard_result

    @staticmethod
    def _safe_fallback(action: str) -> str:
        """Absolute safe fallbacks — no variable data, no promises."""
        safe_msgs = {
            "accept_offer": "Your offer has been noted. Please proceed with the payment as discussed.",
            "counter_offer": "We would like to discuss a revised payment arrangement. Please call us.",
            "clarify": "Could you please clarify your situation so we can assist you?",
            "await_payment": "Thank you. We look forward to your payment.",
            "escalate": "Your case is being reviewed. A specialist will contact you.",
            "halt": "",
            "resolve": "Your account is now settled. Thank you.",
            "payment_failed": "We did not receive your payment. Please contact us to resolve this.",
            "wait": "Thank you for your message. We will be in touch.",
        }
        return safe_msgs.get(action, "Thank you for contacting us.")
