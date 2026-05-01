import Link from "next/link";
import { fetchJson } from "../../components/api";
import { EscalationActions } from "../../components/escalation-actions";

type Esc = {
  escalation_id: string;
  workflow_id: string;
  reason: string;
  priority: number;
  status: string;
  sla_breached: boolean;
  sla_age_minutes: number;
};

export default async function EscalationsPage() {
  const escalations = await fetchJson<Esc[]>("/escalations").catch(() => []);

  return (
    <div className="card">
      <div className="h6">Escalation Workbench</div>
      {escalations.map((e) => (
        <div key={e.escalation_id} style={{ marginBottom: 12, borderBottom: "1px solid #cfd6d8", paddingBottom: 10 }}>
          <div className="row">
            <span>
              <Link href={`/workflows/${e.workflow_id}`}>{e.workflow_id}</Link> - {e.reason}
            </span>
            <span className={`badge ${e.sla_breached ? "danger" : "warn"}`}>
              P{e.priority} {e.status} +{e.sla_age_minutes}m
            </span>
          </div>
          <EscalationActions escalationId={e.escalation_id} />
        </div>
      ))}
    </div>
  );
}
