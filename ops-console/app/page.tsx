import Link from "next/link";
import { fetchJson } from "../components/api";

type Esc = { escalation_id: string; workflow_id: string; priority: number; status: string; sla_breached: boolean };

export default async function DashboardPage() {
  const escalations = await fetchJson<Esc[]>("/escalations").catch(() => []);
  const open = escalations.filter((e) => e.status !== "closed");
  const breached = escalations.filter((e) => e.sla_breached);

  return (
    <div className="grid">
      <section className="card" style={{ gridColumn: "span 4" }}>
        <div className="h6">Open Escalations</div>
        <div className="kpi">{open.length}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 4" }}>
        <div className="h6">SLA Breaches</div>
        <div className="kpi">{breached.length}</div>
      </section>
      <section className="card" style={{ gridColumn: "span 4" }}>
        <div className="h6">Views</div>
        <div><Link href="/escalations">Escalation Workbench</Link></div>
        <div><Link href="/economics">Economics</Link></div>
        <div><Link href="/feedback">Feedback Loop</Link></div>
      </section>
      <section className="card" style={{ gridColumn: "span 12" }}>
        <div className="h6">Recent Escalations</div>
        {escalations.slice(0, 20).map((e) => (
          <div className="row" key={e.escalation_id}>
            <span><Link href={`/workflows/${e.workflow_id}`}>{e.workflow_id}</Link></span>
            <span className={`badge ${e.sla_breached ? "danger" : "ok"}`}>{e.status}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
