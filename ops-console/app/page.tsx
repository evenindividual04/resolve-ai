import Link from "next/link";
import { fetchJson } from "../components/api";
import { ProgressBar } from "../components/ProgressBar";
import { EmptyState } from "../components/EmptyState";
import { StatusBadge, workflowStateVariant } from "../components/StatusBadge";
import type { BusinessMetrics, Escalation } from "../types";
import { timeAgo } from "../components/utils";

export const revalidate = 60;

function MetricKPI({ label, value, sub, variant }: { label: string; value: string | number; sub?: string; variant?: "ok" | "warn" | "danger" | "info" | "halted" }) {
  const color = variant ? `var(--${variant})` : "var(--ink)";
  return (
    <div className="metric-card">
      <span className="metric-label h6">{label}</span>
      <div className="metric-value" style={{ color }}>{value}</div>
      {sub && <div className="metric-meta">{sub}</div>}
    </div>
  );
}

export default async function DashboardPage() {
  let metrics: BusinessMetrics | null = null;
  let escalations: Escalation[] = [];
  let metricsError = false;
  let escError = false;

  const [metricsResult, escResult] = await Promise.allSettled([
    fetchJson<BusinessMetrics>("/metrics/business", { revalidate: 60 }),
    fetchJson<Escalation[]>("/escalations", { revalidate: 30 }),
  ]);

  if (metricsResult.status === "fulfilled") metrics = metricsResult.value;
  else metricsError = true;

  if (escResult.status === "fulfilled") escalations = escResult.value;
  else escError = true;

  const resolutionRate = metrics?.resolution_rate ?? 0;
  const rateVariant = resolutionRate >= 0.7 ? "ok" : resolutionRate >= 0.5 ? "warn" : "danger";
  const recentEscalations = escalations.slice(0, 8);

  return (
    <div className="page-shell animate-in">
      {/* ── Hero ─────────────────────────────────────────────────────────── */}
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip ok">Live operations</span>
            Collections Intelligence Console
          </div>
          <h1 className="hero-title">
            AI-native debt recovery at scale.
          </h1>
          <p className="hero-copy">
            Monitor negotiation workflows, triage escalations, inspect model decisions, and feed the learning loop — all in one operator surface.
          </p>
          <div className="hero-actions">
            <Link href="/escalations" className="button">Open escalation queue</Link>
            <Link href="/workflows" className="button secondary">Browse workflows</Link>
          </div>
        </div>

        {/* Business KPI panel */}
        <aside className="card shell-panel">
          <div>
            <div className="h6">Business posture</div>
            <div className="hero-meta">Platform-wide recovery and compliance signals.</div>
          </div>

          {metricsError ? (
            <div className="subtle">Business metrics unavailable — API not responding.</div>
          ) : metrics ? (
            <>
              <div style={{ marginBottom: 4 }}>
                <ProgressBar
                  value={resolutionRate}
                  label="Resolution rate"
                  variant={rateVariant}
                />
              </div>
              <div className="panel-grid">
                <MetricKPI
                  label="Resolved"
                  value={metrics.resolved}
                  sub={`of ${metrics.total_workflows} workflows`}
                  variant={rateVariant}
                />
                <MetricKPI
                  label="Avg turns"
                  value={metrics.avg_turns_to_close.toFixed(1)}
                  sub="turns to close"
                  variant={metrics.avg_turns_to_close > 6 ? "warn" : "ok"}
                />
                <MetricKPI
                  label="Compliance flags"
                  value={metrics.compliance_violations}
                  sub="outbound violations"
                  variant={metrics.compliance_violations > 0 ? "danger" : "ok"}
                />
                <MetricKPI
                  label="DNC halts"
                  value={metrics.halted}
                  sub="workflows halted"
                  variant={metrics.halted > 0 ? "halted" : "ok"}
                />
                <MetricKPI
                  label="Cost / resolved"
                  value={`$${metrics.cost_per_resolved_workflow.toFixed(4)}`}
                  sub="per closed workflow"
                />
                <MetricKPI
                  label="Decisions"
                  value={metrics.total_decisions.toLocaleString()}
                  sub="total AI decisions"
                  variant="info"
                />
              </div>
            </>
          ) : null}
        </aside>
      </section>

      {/* ── Content grid ─────────────────────────────────────────────────── */}
      <section className="grid">
        {/* Escalation queue preview */}
        <article className="card split-8">
          <div className="section-header">
            <div>
              <div className="h6">Recent escalations</div>
              <h2 className="section-title">Queue pressure</h2>
            </div>
            <Link href="/escalations">Open workbench →</Link>
          </div>

          <div className="card-stack">
            {escError ? (
              <div className="subtle">Escalation feed unavailable.</div>
            ) : recentEscalations.length === 0 ? (
              <EmptyState icon="✓" title="Queue clear" message="No open escalations right now." />
            ) : (
              recentEscalations.map((e) => (
                <div
                  key={e.escalation_id}
                  className={`list-item ${e.priority <= 1 ? "priority-1" : e.priority <= 2 ? "priority-2" : "priority-neutral"}`}
                >
                  <div>
                    <div>
                      <Link href={`/workflows/${e.workflow_id}`}>{e.workflow_id}</Link>
                    </div>
                    <div className="subtle">{e.reason}</div>
                  </div>
                  <StatusBadge variant={e.sla_breached ? "danger" : e.priority <= 2 ? "warn" : "ok"}>
                    P{e.priority} · {e.status}
                  </StatusBadge>
                </div>
              ))
            )}
          </div>
        </article>

        {/* Quick paths */}
        <aside className="card split-4">
          <div className="section-header">
            <div>
              <div className="h6">Quick paths</div>
              <h2 className="section-title">Direct entry</h2>
            </div>
          </div>
          <div className="card-stack">
            <Link href="/escalations">Escalation queue</Link>
            <Link href="/workflows">Workflow browser</Link>
            <Link href="/borrowers">Borrower intelligence</Link>
            <Link href="/economics">Economics &amp; burn rate</Link>
            <Link href="/feedback">Learning loop &amp; feedback</Link>
            <Link href="/incidents">Incident taxonomy</Link>
          </div>
        </aside>
      </section>
    </div>
  );
}
