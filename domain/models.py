from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class WorkflowStatus(str, Enum):
    INIT = "init"
    CONTACTED = "contacted"
    NEGOTIATING = "negotiating"
    WAITING_FOR_PAYMENT = "waiting_for_payment"
    PAYMENT_FAILED = "payment_failed"
    REVALIDATION_REQUIRED = "revalidation_required"
    RESOLVED = "resolved"
    ESCALATED = "escalated"


class FailureType(str, Enum):
    HALLUCINATION = "hallucination"
    POLICY_VIOLATION = "policy_violation"
    STATE_INCONSISTENCY = "state_inconsistency"
    USER_AMBIGUITY = "user_ambiguity"
    INFRA_TIMEOUT_OUTAGE = "infra_timeout_outage"
    INFRA_FAILURE = "infra_failure"


class AutonomyLevel(str, Enum):
    FULL_AUTO = "full_auto"
    HUMAN_REVIEW = "human_review"
    BLOCKED = "blocked"


class IncidentType(str, Enum):
    DB_OUTAGE = "db_outage"
    QUEUE_DELAY = "queue_delay"
    LLM_TIMEOUT = "llm_timeout"
    TOOL_FAILURE = "tool_failure"


class EventType(str, Enum):
    USER_MESSAGE = "user_message"
    PAYMENT_WEBHOOK = "payment_webhook"
    TIMEOUT = "timeout"


class Event(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: str
    workflow_id: str
    event_type: EventType
    channel: str = "sms"
    payload: dict[str, Any] = Field(default_factory=dict)
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    idempotency_key: str
    schema_version: str = "v1"


class WorkflowState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    workflow_id: str
    user_id: str
    current_state: WorkflowStatus = WorkflowStatus.INIT
    outstanding_amount: float = 0.0
    negotiated_amount: float | None = None
    strike_count: int = 0
    last_message: str = ""
    history_summary: str = ""
    version: int = 0
    prompt_version: str = "extractor_v1"
    policy_version: str = "policy_v1"
    context_version: str = "ctx_v1"
    autonomy_level: AutonomyLevel = AutonomyLevel.HUMAN_REVIEW
    stale_after_hours: int = 48
    last_revalidated_at: datetime | None = None
    agreement_expires_at: datetime | None = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class LLMDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    intent: Literal[
        "PAYMENT_OFFER",
        "PAYMENT_COMMIT",
        "HARDSHIP",
        "ABUSIVE",
        "CONFUSED",
        "UNKNOWN",
    ]
    amount: float | None = None
    confidence: float = Field(ge=0.0, le=1.0)
    contradictory: bool = False
    prompt_version: str = "extractor_v1"
    reasoning: str = ""


class PolicyResult(BaseModel):
    allowed: bool
    reason_code: str
    next_action: str


class DecisionTrace(BaseModel):
    model_config = ConfigDict(extra="forbid")

    decision_id: str
    workflow_id: str
    event_id: str
    llm_output: dict[str, Any]
    policy_result: dict[str, Any]
    final_action: str
    prompt_version: str
    policy_version: str
    model_name: str
    confidence: float
    cost_usd: float
    tokens_used: int
    checksum: str
    autonomy_level: AutonomyLevel = AutonomyLevel.HUMAN_REVIEW
    critic_result: dict[str, Any] = Field(default_factory=dict)
    consistency_variance: float = 0.0
    failure_score: dict[str, Any] = Field(default_factory=dict)
    tool_compensation_applied: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class Escalation(BaseModel):
    escalation_id: str
    workflow_id: str
    reason: str
    priority: int = 2
    sla_due_at: datetime
    status: str = "open"
    operator: str | None = None
    notes: str = ""


class ReplayRequest(BaseModel):
    workflow_id: str


class EscalationAction(BaseModel):
    operator: str
    status: Literal["open", "in_progress", "closed"]
    notes: str


class FeedbackSignal(BaseModel):
    workflow_id: str
    decision_id: str | None = None
    signal_type: Literal["operator_override", "bad_decision", "good_decision", "policy_gap"]
    rating: int = Field(ge=1, le=5)
    notes: str = ""


class FailureRecord(BaseModel):
    workflow_id: str
    event_id: str | None = None
    failure_type: FailureType
    severity: Literal["low", "medium", "high"]
    recoverability: Literal["low", "medium", "high"]
    recovery_strategy: Literal["retry", "degrade", "escalate"]
    recovered: bool = False
    cost_impact_usd: float = 0.0
    notes: str = ""


class IncidentSimulationRequest(BaseModel):
    incident_type: IncidentType
    workflow_id: str
    payload: dict[str, Any] = Field(default_factory=dict)


class IncidentSimulationResult(BaseModel):
    incident_id: str
    workflow_id: str
    incident_type: IncidentType
    status: Literal["simulated", "failed"]
    recovery_status: Literal["recovered", "degraded", "escalated"]
    details: dict[str, Any] = Field(default_factory=dict)


class ToolExecutionRecord(BaseModel):
    workflow_id: str
    tool_name: str
    status: Literal["intent", "success", "failed", "compensated"]
    payload: dict[str, Any] = Field(default_factory=dict)


@dataclass(frozen=True)
class CostRecord:
    workflow_id: str
    decision_id: str
    tokens_used: int
    cost_usd: float
