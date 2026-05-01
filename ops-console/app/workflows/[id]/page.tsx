import { fetchJson } from "../../../components/api";

type Timeline = {
  events: Array<{ event_id: string; event_type: string; occurred_at: string }>;
  decisions: Array<{ decision_id: string; final_action: string; reason_code?: string; created_at: string }>;
};

export default async function WorkflowPage({ params }: { params: { id: string } }) {
  const timeline = await fetchJson<Timeline>(`/workflows/${params.id}/timeline`).catch(() => ({ events: [], decisions: [] }));

  return (
    <div className="grid">
      <section className="card" style={{ gridColumn: "span 12" }}>
        <div className="h6">Workflow Timeline: {params.id}</div>
        {timeline.events.map((e) => (
          <div className="row" key={e.event_id}>
            <span>{e.event_type}</span>
            <span>{e.occurred_at}</span>
          </div>
        ))}
      </section>
      <section className="card" style={{ gridColumn: "span 12" }}>
        <div className="h6">Decision Trace</div>
        {timeline.decisions.map((d) => (
          <div className="row" key={d.decision_id}>
            <span>{d.final_action}</span>
            <span>{d.created_at}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
