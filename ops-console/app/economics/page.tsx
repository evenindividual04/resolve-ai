import { fetchJson } from "../../components/api";
import { EmptyState } from "../../components/EmptyState";
import type { EconomicsSummary } from "../../types";

export const revalidate = 120;

export default async function EconomicsPage() {
  let econ: EconomicsSummary = {
    total_cost_usd: 0,
    total_tokens: 0,
    workflows_count: 0,
    cost_per_workflow: 0,
    cost_per_resolution: 0,
    cost_per_failure: 0,
    model_breakdown: {},
    llm_call_breakdown: { real: 0, fallback: 0 },
  };
  let loadError = false;

  try {
    econ = await fetchJson<EconomicsSummary>("/economics/summary");
  } catch {
    loadError = true;
  }

  const tokensPerWorkflow = econ.workflows_count > 0 ? Math.round(econ.total_tokens / econ.workflows_count) : 0;

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip info">Economic posture</span>
            Cost visibility
          </div>
          <h1 className="hero-title">Make model spend and workflow throughput visible at the same time.</h1>
          <p className="hero-copy">
            What it costs, how much work is flowing, and where efficiency is trending.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Efficiency snapshot</div>
            <div className="hero-meta">High-level cost signals from the latest summary.</div>
          </div>
          {loadError ? (
            <div className="subtle">Economics metrics unavailable — API not responding.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">Total cost</span>
                <div className="metric-value">${econ.total_cost_usd.toFixed(4)}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Cost / workflow</span>
                <div className="metric-value">${econ.cost_per_workflow.toFixed(4)}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Tokens / workflow</span>
                <div className="metric-value">{tokensPerWorkflow.toLocaleString()}</div>
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
                <h2 className="section-title">Economics summary failed to load</h2>
              </div>
            </div>
            <div className="subtle">The metrics are not a valid empty state — they require a live economics response.</div>
          </article>
        ) : (
          <>
            <article className="card split-6 stack">
              <div className="section-header">
                <div>
                  <div className="h6">Core metrics</div>
                  <h2 className="section-title">Operational spend</h2>
                </div>
              </div>
              <div className="card-stack">
                <div className="metric-card">
                  <span className="metric-label h6">Workflows</span>
                  <div className="metric-value">{econ.workflows_count.toLocaleString()}</div>
                  <div className="metric-meta">Processed in the current reporting window.</div>
                </div>
                <div className="metric-card">
                  <span className="metric-label h6">Tokens consumed</span>
                  <div className="metric-value">{econ.total_tokens.toLocaleString()}</div>
                  <div className="metric-meta">Useful for comparing traffic spikes against cost pressure.</div>
                </div>
              </div>
            </article>

            <article className="card split-6 stack">
              <div>
                <div className="h6">LLM call routing</div>
                <h2 className="section-title">Provider usage</h2>
              </div>
              <div className="card-stack">
                <div className="metric-card">
                  <span className="metric-label h6">Real LLM calls</span>
                  <div className="metric-value">{econ.llm_call_breakdown?.real ?? 0}</div>
                  <div className="metric-meta">External provider hits (Groq/Cerebras/Gemini).</div>
                </div>
                <div className="metric-card">
                  <span className="metric-label h6">Fallback calls</span>
                  <div className="metric-value">{econ.llm_call_breakdown?.fallback ?? 0}</div>
                  <div className="metric-meta">Deterministic extraction (no API key/timeout).</div>
                </div>
                <div className="metric-card">
                  <span className="metric-label h6">Models used</span>
                  <div className="stack mt-2">
                    {Object.entries(econ.model_breakdown || {}).length === 0 ? (
                      <EmptyState icon="—" title="No model data" />
                    ) : (
                      Object.entries(econ.model_breakdown || {}).map(([model, cost]) => (
                        <div key={model} className="subtle">{model}: ${cost.toFixed(4)}</div>
                      ))
                    )}
                  </div>
                </div>
              </div>
            </article>

            <aside className="card split-6 stack">
              <div>
                <div className="h6">What to watch</div>
                <h2 className="section-title">Cost interpretation</h2>
              </div>
              <div className="stack subtle">
                <div>1. Cost per workflow should fall as policy gating removes unnecessary model calls.</div>
                <div>2. Tokens per workflow is a proxy for chain length and retry pressure.</div>
                <div>3. If spend rises without more workflows, investigate provider routing.</div>
                <div>4. High fallback counts may indicate API key or availability issues.</div>
              </div>
            </aside>
          </>
        )}
      </section>
    </div>
  );
}
