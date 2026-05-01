import { fetchJson } from "../../components/api";
import { WorkflowsClient } from "./WorkflowsClient";
import type { WorkflowSummary } from "../../types";

export const revalidate = 30;

export default async function WorkflowsPage() {
  let workflows: WorkflowSummary[] = [];
  let loadError = false;

  try {
    workflows = await fetchJson<WorkflowSummary[]>("/workflows");
  } catch {
    loadError = true;
  }

  const total = workflows.length;
  const resolved = workflows.filter((w) => w.state === "resolved").length;
  const halted = workflows.filter((w) => w.state === "halted").length;
  const active = workflows.filter((w) => ["negotiating", "contacted", "waiting_for_payment"].includes(w.state)).length;

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip info">Workflow browser</span>
            All workflows
          </div>
          <h1 className="hero-title">
            Browse, filter, and inspect every active negotiation.
          </h1>
          <p className="hero-copy">
            Filter by state or risk band, search by workflow or borrower ID, and drill into any workflow&apos;s full decision trace.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Portfolio snapshot</div>
            <div className="hero-meta">Aggregate counts across all workflow records.</div>
          </div>
          {loadError ? (
            <div className="subtle">Workflow list unavailable — API not responding.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">Total</span>
                <div className="metric-value">{total}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Active</span>
                <div className="metric-value" style={{ color: "var(--info)" }}>{active}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Resolved</span>
                <div className="metric-value" style={{ color: "var(--ok)" }}>{resolved}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Halted</span>
                <div className="metric-value" style={{ color: halted > 0 ? "var(--halted)" : "var(--ok)" }}>{halted}</div>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="grid">
        <article className="card split-12 stack">
          <div className="section-header">
            <div>
              <div className="h6">All workflows</div>
              <h2 className="section-title">Negotiation pipeline</h2>
            </div>
          </div>
          {loadError ? (
            <div className="subtle">
              Workflow list could not be loaded. This is an API or network failure.
            </div>
          ) : (
            <WorkflowsClient workflows={workflows} />
          )}
        </article>
      </section>
    </div>
  );
}
