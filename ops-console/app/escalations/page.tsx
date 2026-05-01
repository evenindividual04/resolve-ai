import Link from "next/link";
import { fetchJson } from "../../components/api";
import { EscalationActions } from "../../components/escalation-actions";
import { StatusBadge } from "../../components/StatusBadge";
import { EmptyState } from "../../components/EmptyState";
import type { Escalation } from "../../types";
import { timeAgo } from "../../components/utils";

export const revalidate = 30;

export default async function EscalationsPage() {
  let escalations: Escalation[] = [];
  let loadError = false;

  try {
    escalations = await fetchJson<Escalation[]>("/escalations");
  } catch {
    loadError = true;
  }

  // Fixed: P1 = highest priority, P2 = high — was incorrectly filtering >= 4
  const open = escalations.filter((e) => e.status !== "closed");
  const breached = escalations.filter((e) => e.sla_breached);
  const critical = escalations.filter((e) => e.priority <= 2);

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip warn">Queue pressure</span>
            Escalation workbench
          </div>
          <h1 className="hero-title">
            Triage the highest-risk work first.
          </h1>
          <p className="hero-copy">
            P1 and P2 items are marked with a coloured left border for fast scanning. Work top to bottom — breached SLAs are already dangerous.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Queue summary</div>
            <div className="hero-meta">Snapshot from the latest fetch.</div>
          </div>
          {loadError ? (
            <div className="subtle">Queue metrics unavailable — API not responding.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">Open</span>
                <div className="metric-value">{open.length}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">SLA breached</span>
                <div className="metric-value" style={{ color: breached.length > 0 ? "var(--danger)" : "var(--ok)" }}>
                  {breached.length}
                </div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">P1–P2</span>
                <div className="metric-value" style={{ color: critical.length > 0 ? "var(--warn)" : "var(--ok)" }}>
                  {critical.length}
                </div>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="grid">
        {loadError ? (
          <article className="card split-12">
            <div className="section-header">
              <div>
                <div className="h6">Data unavailable</div>
                <h2 className="section-title">Escalation queue failed to load</h2>
              </div>
            </div>
            <div className="subtle">This is an API or network failure, not an empty queue.</div>
          </article>
        ) : (
          <>
            <article className="card split-8">
              <div className="section-header">
                <div>
                  <div className="h6">Active queue</div>
                  <h2 className="section-title">Escalation stream</h2>
                </div>
                <span className="subtle">{escalations.length} records</span>
              </div>

              <div className="card-stack">
                {escalations.length === 0 ? (
                  <EmptyState icon="✓" title="Queue clear" message="No escalations right now." />
                ) : (
                  escalations.map((e) => (
                    <section
                      key={e.escalation_id}
                      className={`card escalation-card ${e.priority <= 1 ? "priority-1" : e.priority <= 2 ? "priority-2" : "priority-neutral"}`}
                    >
                      <div className="section-header">
                        <div>
                          <Link href={`/workflows/${e.workflow_id}`}>{e.workflow_id}</Link>
                          <div className="subtle">{e.reason}</div>
                        </div>
                        <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: 6 }}>
                          <StatusBadge variant={e.sla_breached ? "danger" : e.priority <= 2 ? "warn" : "ok"}>
                            P{e.priority} · {e.status}
                          </StatusBadge>
                          <span className="subtle" style={{ fontSize: "0.78rem" }}>
                            +{e.sla_age_minutes}m · {timeAgo(e.created_at)}
                          </span>
                        </div>
                      </div>
                      <EscalationActions escalationId={e.escalation_id} initialStatus={e.status} />
                    </section>
                  ))
                )}
              </div>
            </article>

            <aside className="card split-4 stack">
              <div>
                <div className="h6">Operator guidance</div>
                <h2 className="section-title">Review patterns</h2>
              </div>
              <div className="stack subtle">
                <div>1. Work P1 first — red border = SLA critical.</div>
                <div>2. Write enough notes for the next operator to understand without re-opening the trace.</div>
                <div>3. Use the workflow link to inspect the full decision path.</div>
                <div>4. HALTED workflows require compliance team routing — do not contact the borrower.</div>
              </div>
            </aside>
          </>
        )}
      </section>
    </div>
  );
}
