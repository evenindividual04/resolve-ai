import { fetchJson } from "../../components/api";
import { FeedbackForm } from "../../components/feedback-form";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import type { FeedbackSignal } from "../../types";
import { formatDate } from "../../components/utils";

export const revalidate = 60;

type SignalType = "good_decision" | "bad_decision" | "operator_override" | "policy_gap";

const SIGNAL_ICONS: Record<SignalType, { icon: string; color: string }> = {
  good_decision:    { icon: "✓", color: "var(--ok)" },
  bad_decision:     { icon: "✕", color: "var(--danger)" },
  operator_override:{ icon: "↻", color: "var(--info)" },
  policy_gap:       { icon: "△", color: "var(--warn)" },
};

export default async function FeedbackPage() {
  let rows: FeedbackSignal[] = [];
  let loadError = false;

  try {
    rows = await fetchJson<FeedbackSignal[]>("/feedback");
  } catch {
    loadError = true;
  }

  const total = rows.length;
  const good = rows.filter((r) => r.signal_type === "good_decision").length;
  const needsReview = rows.filter((r) => r.signal_type !== "good_decision").length;

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip ok">Learning loop</span>
            Feedback center
          </div>
          <h1 className="hero-title">Capture operator judgment as actionable signal.</h1>
          <p className="hero-copy">
            Submit a signal, review history, and understand whether the system is getting better or accumulating friction.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Signal summary</div>
            <div className="hero-meta">Latest feedback payload in compact form.</div>
          </div>
          {loadError ? (
            <div className="subtle">Feedback metrics unavailable.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">Signals</span>
                <div className="metric-value">{total}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Positive</span>
                <div className="metric-value" style={{ color: "var(--ok)" }}>{good}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Needs review</span>
                <div className="metric-value" style={{ color: needsReview > 0 ? "var(--warn)" : "var(--ok)" }}>{needsReview}</div>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="grid">
        {loadError && (
          <article className="card split-12">
            <div className="section-header">
              <div>
                <div className="h6">Data unavailable</div>
                <h2 className="section-title">Feedback history failed to load</h2>
              </div>
            </div>
            <div className="subtle">Submission is still available, but history cannot be trusted until the API responds.</div>
          </article>
        )}

        <div className={`card ${loadError ? "split-12" : "split-5"}`}>
          <FeedbackForm />
        </div>

        <section className={loadError ? "card split-12 stack" : "card split-7 stack"}>
          <div className="section-header">
            <div>
              <div className="h6">Recent signals</div>
              <h2 className="section-title">Operator feedback history</h2>
            </div>
            <span className="subtle">{Math.min(rows.length, 30)} shown</span>
          </div>

          <div className="card-stack">
            {loadError ? (
              <div className="subtle">History unavailable.</div>
            ) : rows.length === 0 ? (
              <EmptyState icon="○" title="No signals yet" message="Submit your first feedback signal using the form." />
            ) : (
              rows.slice(0, 30).map((r, idx) => {
                const signalMeta = SIGNAL_ICONS[r.signal_type as SignalType] ?? { icon: "○", color: "var(--muted)" };
                return (
                  <div className="list-item" key={`${r.workflow_id}-${idx}`}>
                    <div style={{ display: "flex", flexDirection: "row", gap: 10, alignItems: "flex-start" }}>
                      <span
                        className="signal-icon"
                        style={{ color: signalMeta.color, marginTop: 2 }}
                        aria-hidden="true"
                      >
                        {signalMeta.icon}
                      </span>
                      <div>
                        <div>{r.workflow_id}</div>
                        <div className="subtle">{r.signal_type.replace(/_/g, " ")}</div>
                        {r.notes && <div className="subtle" style={{ fontSize: "0.82rem" }}>{r.notes}</div>}
                      </div>
                    </div>
                    <div className="stack align-end gap-2">
                      <StatusBadge variant={r.rating >= 4 ? "ok" : r.rating >= 3 ? "warn" : "danger"}>
                        {r.rating}/5
                      </StatusBadge>
                      <span className="subtle" style={{ fontSize: "0.78rem" }}>{formatDate(r.created_at)}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </section>
      </section>
    </div>
  );
}
