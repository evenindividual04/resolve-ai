import { fetchJson } from "../../../components/api";
import { HaltedBanner } from "../../../components/HaltedBanner";
import { NegotiationPanel } from "../../../components/NegotiationPanel";
import { MessageLogPanel } from "../../../components/MessageLogPanel";
import { BorrowerCard } from "../../../components/BorrowerCard";
import { StatusBadge, workflowStateVariant, eventTypeVariant } from "../../../components/StatusBadge";
import { EmptyState } from "../../../components/EmptyState";
import { formatDate } from "../../../components/utils";
import type { Timeline, NegotiationState, MessageLog, BorrowerProfile } from "../../../types";

export const revalidate = 15;

export default async function WorkflowPage({ params }: { params: { id: string } }) {
  const id = params.id;

  const [traceResult, negotiationResult, messagesResult, borrowerResult] = await Promise.allSettled([
    fetchJson<Timeline>(`/workflows/${id}/trace`),
    fetchJson<NegotiationState>(`/workflows/${id}/negotiation`),
    fetchJson<MessageLog[]>(`/workflows/${id}/messages`),
    fetchJson<BorrowerProfile>(`/borrowers/${id}`),
  ]);

  const trace = traceResult.status === "fulfilled" ? traceResult.value : null;
  const negotiation = negotiationResult.status === "fulfilled" ? negotiationResult.value : null;
  const messages = messagesResult.status === "fulfilled" ? messagesResult.value : null;
  const borrower = borrowerResult.status === "fulfilled" ? borrowerResult.value : null;

  const isHalted = trace?.state === "halted";
  const lastDecision = trace?.decisions?.[trace.decisions.length - 1];
  const haltReason = isHalted ? (lastDecision?.policy_result?.reason_code ?? "") : "";

  return (
    <div className="page-shell animate-in">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero-card" style={isHalted ? { borderColor: "rgba(192, 132, 252, 0.35)" } : {}}>
          <div className="eyebrow">
            <StatusBadge variant={trace?.state ? workflowStateVariant(trace.state) : "info"}>
              {trace?.state ?? "Workflow trace"}
            </StatusBadge>
            {id}
          </div>
          <h1 className="hero-title">Inspect the event stream and decision ledger.</h1>
          <p className="hero-copy">
            What happened, when it happened, and what the system decided. Every decision is auditable from this view.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Trace summary</div>
            <div className="hero-meta">Snapshot of the selected workflow.</div>
          </div>
          <div className="panel-grid">
            <div className="metric-card">
              <span className="metric-label h6">Events</span>
              <div className="metric-value">{trace?.events?.length ?? "—"}</div>
            </div>
            <div className="metric-card">
              <span className="metric-label h6">Decisions</span>
              <div className="metric-value">{trace?.decisions?.length ?? "—"}</div>
            </div>
            <div className="metric-card">
              <span className="metric-label h6">Real LLM</span>
              <div className="metric-value">
                {trace?.decisions?.filter((d) => d.is_llm_call).length ?? "—"}
              </div>
              <div className="metric-meta">External model calls</div>
            </div>
          </div>
        </aside>
      </section>

      {/* ── HALTED banner ─────────────────────────────────────────────────── */}
      {isHalted && <HaltedBanner reason={haltReason} />}

      {/* ── Content grid ─────────────────────────────────────────────────── */}
      <section className="grid">
        {!trace ? (
          <article className="card split-12">
            <div className="section-header">
              <div>
                <div className="h6">Data unavailable</div>
                <h2 className="section-title">Workflow trace failed to load</h2>
              </div>
            </div>
            <div className="subtle">The trace view requires a live workflow timeline API response.</div>
          </article>
        ) : (
          <>
            {/* Event timeline */}
            <article className="card split-7 stack">
              <div className="section-header">
                <div>
                  <div className="h6">Event timeline</div>
                  <h2 className="section-title">What happened</h2>
                </div>
                <span className="subtle">{trace.events.length} events</span>
              </div>

              <div className="card-stack">
                {trace.events.length === 0 ? (
                  <EmptyState icon="○" title="No events" message="No events recorded for this workflow yet." />
                ) : (
                  trace.events.map((e) => (
                    <div className="timeline-row" key={e.event_id}>
                      <div>
                        <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.88rem" }}>
                          {e.event_type}
                        </div>
                        <div className="subtle" style={{ fontSize: "0.82rem" }}>
                          {formatDate(e.occurred_at)}
                        </div>
                      </div>
                      <StatusBadge variant={eventTypeVariant(e.event_type, e.payload as Record<string, unknown>)}>
                        {e.event_type.replace(/_/g, " ")}
                      </StatusBadge>
                    </div>
                  ))
                )}
              </div>
            </article>

            {/* Decision ledger */}
            <aside className="card split-5 stack">
              <div className="section-header">
                <div>
                  <div className="h6">Decision ledger</div>
                  <h2 className="section-title">Why it happened</h2>
                </div>
              </div>

              <div className="card-stack">
                {trace.decisions.length === 0 ? (
                  <EmptyState icon="○" title="No decisions" message="No decisions recorded yet." />
                ) : (
                  trace.decisions.map((d) => (
                    <div className="timeline-row" key={d.decision_id}>
                      <div>
                        <div>
                          {d.final_action.replace(/_/g, " ")}{" "}
                          <span className="subtle" style={{ fontFamily: "var(--font-mono)", fontSize: "0.82rem" }}>
                            ({d.model_name || "fallback"})
                          </span>
                        </div>
                        <div className="subtle" style={{ fontSize: "0.82rem" }}>
                          {d.policy_result?.reason_code ?? "No reason code"} ·{" "}
                          {d.is_llm_call ? "real LLM" : "fallback"} ·{" "}
                          {(d.confidence * 100).toFixed(0)}% confidence
                        </div>
                        <div className="subtle" style={{ fontSize: "0.78rem" }}>
                          {formatDate(d.created_at)}
                        </div>
                      </div>
                      <StatusBadge variant={d.confidence >= 0.8 ? "ok" : d.confidence >= 0.6 ? "warn" : "danger"}>
                        {(d.confidence * 100).toFixed(0)}%
                      </StatusBadge>
                    </div>
                  ))
                )}
              </div>
            </aside>

            {/* Negotiation panel */}
            {negotiation && (
              <article className="card split-6 stack">
                <div className="section-header">
                  <div>
                    <div className="h6">Negotiation state</div>
                    <h2 className="section-title">Deal dynamics</h2>
                  </div>
                </div>
                <NegotiationPanel negotiation={negotiation} />
              </article>
            )}

            {/* Message log */}
            {messages && (
              <article className="card split-6 stack">
                <div className="section-header">
                  <div>
                    <div className="h6">Outbound messages</div>
                    <h2 className="section-title">What was sent</h2>
                  </div>
                  <span className="subtle">{messages.length} messages</span>
                </div>
                <MessageLogPanel messages={messages} />
              </article>
            )}

            {/* Borrower profile */}
            {borrower && (
              <article className="card split-12 stack">
                <div className="section-header">
                  <div>
                    <div className="h6">Borrower profile</div>
                    <h2 className="section-title">Who this is</h2>
                  </div>
                </div>
                <BorrowerCard profile={borrower} />
              </article>
            )}
          </>
        )}
      </section>
    </div>
  );
}
