import { fetchJson } from "../../components/api";

type FailureSummary = { total: number; by_type: Record<string, number>; recovery_success_rate: number };

export default async function IncidentsPage() {
  const summary = await fetchJson<FailureSummary>("/failures/summary").catch(() => ({ total: 0, by_type: {}, recovery_success_rate: 0 }));

  return (
    <div className="grid">
      <section className="card" style={{ gridColumn: "span 4" }}>
        <div className="h6">Failures</div>
        <div className="kpi">{summary.total}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 4" }}>
        <div className="h6">Recovery Rate</div>
        <div className="kpi">{(summary.recovery_success_rate * 100).toFixed(1)}%</div>
      </section>
      <section className="card" style={{ gridColumn: "span 12" }}>
        <div className="h6">Failure Taxonomy</div>
        {Object.entries(summary.by_type).map(([k, v]) => (
          <div className="row" key={k}><span>{k}</span><span>{v}</span></div>
        ))}
      </section>
    </div>
  );
}
