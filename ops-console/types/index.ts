// ─── Base ─────────────────────────────────────────────────────────────────────

export interface BaseEntity {
  created_at: string;
}

// ─── Borrower ─────────────────────────────────────────────────────────────────

export type RiskBand = "low" | "medium" | "high" | "critical";
export type LoanSegment = "personal" | "credit_card" | "business" | "gold" | "vehicle";
export type ContactChannel = "whatsapp" | "sms" | "email" | "voice";

export interface BorrowerProfile {
  user_id: string;
  risk_band: RiskBand;
  loan_segment: LoanSegment;
  outstanding_amount: number;
  dpd: number;
  prior_defaults: number;
  contact_attempts: number;
  preferred_channel: ContactChannel;
  language: string;
  timezone: string;
  dnc_flag: boolean;
  legal_flag: boolean;
  notes: string;
  updated_at: string;
}

// ─── Escalation ───────────────────────────────────────────────────────────────

export interface Escalation extends BaseEntity {
  escalation_id: string;
  workflow_id: string;
  reason: string;
  priority: number; // 1 = highest
  status: "open" | "in_progress" | "closed";
  sla_breached: boolean;
  sla_age_minutes: number;
  operator: string | null;
  notes: string;
}

export interface EscalationAction {
  operator: string;
  status: "open" | "in_progress" | "closed";
  notes?: string;
}

// ─── Event ────────────────────────────────────────────────────────────────────

export type EventType =
  | "user_message"
  | "payment_webhook"
  | "timeout"
  | "scheduler_timeout"
  | "channel_switch";

export interface WorkflowEvent extends BaseEntity {
  event_id: string;
  workflow_id: string;
  event_type: EventType;
  channel: string;
  payload: Record<string, unknown>;
  idempotency_key: string;
  schema_version: string;
  occurred_at: string;
}

// ─── Workflow ─────────────────────────────────────────────────────────────────

export type WorkflowStatusValue =
  | "init"
  | "contacted"
  | "negotiating"
  | "waiting_for_payment"
  | "payment_failed"
  | "revalidation_required"
  | "resolved"
  | "escalated"
  | "halted";

export interface WorkflowState extends BaseEntity {
  workflow_id: string;
  user_id: string;
  current_state: WorkflowStatusValue;
  outstanding_amount: number;
  negotiated_amount: number | null;
  counter_offer_amount: number | null;
  strike_count: number;
  turn_count: number;
  prior_offers: number[];
  loan_segment: LoanSegment | null;
  risk_band: RiskBand | null;
  last_message: string;
  history_summary: string;
  version: number;
  prompt_version: string;
  policy_version: string;
  context_version: string;
  autonomy_level: "full_auto" | "human_review" | "blocked";
  stale_after_hours: number;
  last_revalidated_at: string | null;
  agreement_expires_at: string | null;
  updated_at: string;
}

export interface WorkflowSummary {
  workflow_id: string;
  user_id: string;
  state: WorkflowStatusValue;
  outstanding_amount: number;
  negotiated_amount: number | null;
  turn_count: number;
  strike_count: number;
  loan_segment: LoanSegment | null;
  risk_band: RiskBand | null;
  updated_at: string;
}

// ─── Negotiation ──────────────────────────────────────────────────────────────

export interface NegotiationState {
  workflow_id: string;
  turn_count: number;
  prior_offers: number[];
  counter_offer_amount: number | null;
  negotiated_amount: number | null;
  outstanding_amount: number;
  strike_count: number;
}

// ─── Messages ─────────────────────────────────────────────────────────────────

export interface MessageLog {
  message_id: string;
  workflow_id: string;
  channel: ContactChannel | string;
  direction: "outbound" | "inbound";
  content: string;
  action: string;
  compliance_passed: number; // 1 = passed, 0 = flagged
  violations: string[];
  sent_at: string;
  delivered_at: string | null;
  read_at: string | null;
}

// ─── Decision Trace ───────────────────────────────────────────────────────────

export interface DecisionTrace extends BaseEntity {
  decision_id: string;
  workflow_id: string;
  event_id: string;
  llm_output: {
    intent: string;
    amount: number | null;
    confidence: number;
    contradictory: boolean;
    prompt_version: string;
    reasoning: string;
  };
  policy_result: {
    allowed: boolean;
    reason_code: string;
    next_action: string;
  };
  final_action: string;
  prompt_version: string;
  policy_version: string;
  model_name: string;
  confidence: number;
  tokens_used: number;
  cost_usd: number;
  checksum: string;
  is_llm_call: boolean;
  autonomy_level: "full_auto" | "human_review" | "blocked";
  critic_result: {
    flags_issue: boolean;
    intents: string[];
    dominant: string;
  };
  consistency_variance: number;
  failure_score: {
    severity: string;
    recoverability: string;
    cost_impact: string;
  };
  tool_compensation_applied: boolean;
}

// ─── Timeline ─────────────────────────────────────────────────────────────────

export interface Timeline {
  events: WorkflowEvent[];
  decisions: DecisionTrace[];
  state?: WorkflowStatusValue;
}

// ─── Feedback ─────────────────────────────────────────────────────────────────

export interface FeedbackSignal extends BaseEntity {
  id: number;
  workflow_id: string;
  decision_id: string | null;
  signal_type: "good_decision" | "bad_decision" | "operator_override" | "policy_gap";
  rating: number;
  notes: string;
}

export interface SubmitFeedbackRequest {
  workflow_id: string;
  signal_type: string;
  rating: number;
  notes: string;
}

// ─── Economics ────────────────────────────────────────────────────────────────

export interface EconomicsSummary {
  total_cost_usd: number;
  total_tokens: number;
  workflows_count: number;
  cost_per_workflow: number;
  cost_per_resolution: number;
  cost_per_failure: number;
  model_breakdown: Record<string, number>;
  llm_call_breakdown: {
    real: number;
    fallback: number;
  };
}

// ─── Business Metrics ─────────────────────────────────────────────────────────

export interface BusinessMetrics {
  total_workflows: number;
  resolved: number;
  escalated: number;
  halted: number;
  resolution_rate: number;
  escalation_rate: number;
  avg_turns_to_close: number;
  total_cost_usd: number;
  cost_per_resolved_workflow: number;
  compliance_violations: number;
  total_decisions: number;
}

// ─── Failures ─────────────────────────────────────────────────────────────────

export interface FailureSummary {
  total: number;
  by_type: Record<string, number>;
  recovery_success_rate: number;
}
