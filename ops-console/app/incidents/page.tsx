import { fetchJson } from "../../components/api";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import type { FailureSummary } from "../../types";

export const revalidate = 120;

export default async function IncidentsPage() {
  let summary: FailureSummary = { total: 0, by_type: {}, recovery_success_rate: 0 };
  let loadError = false;

  try {
    summary = await fetchJson<FailureSummary>("/failures/summary");
  } catch {
    loadError = true;
  }

  const failures = Object.entries(summary.by_type).sort((a, b) => b[1] - a[1]);
  const dominant = failures[0];
  const total = failures.reduce((sum, [, n]) => sum + n, 0);

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip danger">Incident review</span>
            Failure triage
          </div>
          <h1 className="hero-title">Spot the dominant failure mode. Verify recovery is holding.</h1>
          <p className="hero-copy">
            The incidents view emphasises recovery quality, taxonomy density, and the exception type that deserves the most attention.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Recovery snapshot</div>
            <div className="hero-meta">Summary metrics from the latest failure payload.</div>
          </div>
          {loadError ? (
            <div className="subtle">Failure metrics unavailable — API not responding.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">Failures</span>
                <div className="metric-value" style={{ color: summary.total > 0 ? "var(--danger)" : "var(--ok)" }}>
                  {summary.total}
                </div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Recovered</span>
                <div className="metric-value" style={{ color: summary.recovery_success_rate >= 0.8 ? "var(--ok)" : "var(--warn)" }}>
                  {(summary.recovery_success_rate * 100).toFixed(1)}%
                </div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Top type</span>
                <div className="metric-value" style={{ fontSize: "1rem" }}>{dominant ? dominant[0] : "—"}</div>
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
                <h2 className="section-title">Failure summary failed to load</h2>
              </div>
            </div>
            <div className="subtle">This is an API failure, not a legitimate zero-failure state.</div>
          </article>
        ) : (
          <>
            <article className="card split-7 stack">
              <div className="section-header">
                <div>
                  <div className="h6">Failure taxonomy</div>
                  <h2 className="section-title">What is breaking</h2>
                </div>
                <span className="subtle">{failures.length} types</span>
              </div>

              <div className="card-stack">
                {failures.length === 0 ? (
                  <EmptyState icon="✓" title="No failures recorded" message="Clean slate — no failure types in the current window." />
                ) : (
                  failures.map(([kind, count]) => {
                    const share = total > 0 ? Math.round((count / total) * 100) : 0;
                    return (
                      <div className="list-item" key={kind}>
                        <div>
                          <div style={{ fontFamily: "var(--font-mono)", fontSize: "0.88rem" }}>{kind}</div>
                          <div className="subtle">
                            {share}% share of failure volume
                          </div>
                        </div>
                        <StatusBadge variant={kind === dominant?.[0] ? "danger" : "warn"}>
                          {count}
                        </StatusBadge>
                      </div>
                    );
                  })
                )}
              </div>
            </article>

            <aside className="card split-5 stack">
              <div>
                <div className="h6">Operational reading</div>
                <h2 className="section-title">Response guidance</h2>
              </div>
              <div className="stack subtle">
                <div>1. If recovery falls while one failure type dominates, focus on that path first.</div>
                <div>2. If the taxonomy is broad, the problem is systemic — not a single bad transition.</div>
                <div>3. Use the workflow detail view to reconstruct the timeline behind a failure cluster.</div>
                <div>4. Recovery rate below 80% is a production incident threshold.</div>
              </div>
            </aside>
          </>
        )}
      </section>
    </div>
  );
}
