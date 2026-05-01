import { fetchJson } from "../../components/api";

type Econ = {
  total_cost_usd: number;
  total_tokens: number;
  workflows_count: number;
  cost_per_workflow: number;
};

export default async function EconomicsPage() {
  const econ = await fetchJson<Econ>("/economics/summary").catch(
    () => ({ total_cost_usd: 0, total_tokens: 0, workflows_count: 0, cost_per_workflow: 0 }),
  );

  return (
    <div className="grid">
      <section className="card" style={{ gridColumn: "span 3" }}>
        <div className="h6">Total Cost</div>
        <div className="kpi">${econ.total_cost_usd.toFixed(4)}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 3" }}>
        <div className="h6">Total Tokens</div>
        <div className="kpi">{econ.total_tokens}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 3" }}>
        <div className="h6">Workflows</div>
        <div className="kpi">{econ.workflows_count}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 3" }}>
        <div className="h6">Cost / Workflow</div>
        <div className="kpi">${econ.cost_per_workflow.toFixed(4)}</div>
      </section>
    </div>
  );
}
