import { fetchJson } from "../../components/api";
import { BorrowerCard } from "../../components/BorrowerCard";
import { EmptyState } from "../../components/EmptyState";
import { StatusBadge } from "../../components/StatusBadge";
import Link from "next/link";
import type { BorrowerProfile } from "../../types";

export const revalidate = 60;

export default async function BorrowersPage() {
  let borrowers: BorrowerProfile[] = [];
  let loadError = false;

  try {
    borrowers = await fetchJson<BorrowerProfile[]>("/borrowers");
  } catch {
    loadError = true;
  }

  const dnc = borrowers.filter((b) => b.dnc_flag);
  const legal = borrowers.filter((b) => b.legal_flag);
  const critical = borrowers.filter((b) => b.risk_band === "critical");
  const highDpd = borrowers.filter((b) => b.dpd > 90);

  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card">
          <div className="eyebrow">
            <span className="status-chip info">Borrower intelligence</span>
            Profile database
          </div>
          <h1 className="hero-title">
            Know who you&apos;re negotiating with before sending the first message.
          </h1>
          <p className="hero-copy">
            DNC and legal flags are shown first. Risk band, loan segment, DPD, and preferred channel are surfaced for every borrower.
          </p>
        </div>

        <aside className="card shell-panel">
          <div>
            <div className="h6">Risk snapshot</div>
            <div className="hero-meta">Aggregate risk and compliance posture.</div>
          </div>
          {loadError ? (
            <div className="subtle">Borrower data unavailable — API not responding.</div>
          ) : (
            <div className="panel-grid">
              <div className="metric-card">
                <span className="metric-label h6">DNC flagged</span>
                <div className="metric-value" style={{ color: dnc.length > 0 ? "var(--halted)" : "var(--ok)" }}>{dnc.length}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Legal referred</span>
                <div className="metric-value" style={{ color: legal.length > 0 ? "var(--warn)" : "var(--ok)" }}>{legal.length}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">Critical risk</span>
                <div className="metric-value" style={{ color: critical.length > 0 ? "var(--danger)" : "var(--ok)" }}>{critical.length}</div>
              </div>
              <div className="metric-card">
                <span className="metric-label h6">DPD &gt; 90</span>
                <div className="metric-value" style={{ color: highDpd.length > 0 ? "var(--danger)" : "var(--ok)" }}>{highDpd.length}</div>
              </div>
            </div>
          )}
        </aside>
      </section>

      <section className="grid">
        <article className="card split-12 stack">
          <div className="section-header">
            <div>
              <div className="h6">Borrower profiles</div>
              <h2 className="section-title">Full portfolio</h2>
            </div>
            <span className="subtle">{borrowers.length} records</span>
          </div>

          {loadError ? (
            <div className="subtle">Borrower list could not be loaded.</div>
          ) : borrowers.length === 0 ? (
            <EmptyState icon="○" title="No borrower profiles" message="No profiles have been loaded into the system yet." />
          ) : (
            <div className="card-stack">
              {borrowers.map((b) => (
                <div
                  key={b.user_id}
                  className={`list-item ${b.dnc_flag ? "borrower-dnc-row" : b.legal_flag ? "borrower-legal-row" : ""}`}
                  style={{ display: "block", padding: "14px 0" }}
                >
                  <div style={{ display: "flex", flexDirection: "row", justifyContent: "space-between", marginBottom: 10 }}>
                    <Link
                      href={`/workflows?search=${b.user_id}`}
                      style={{ fontFamily: "var(--font-mono)", fontSize: "0.88rem" }}
                    >
                      {b.user_id}
                    </Link>
                    <StatusBadge variant={b.dnc_flag ? "halted" : b.legal_flag ? "warn" : "ok"}>
                      {b.dnc_flag ? "DNC" : b.legal_flag ? "Legal" : "Active"}
                    </StatusBadge>
                  </div>
                  <BorrowerCard profile={b} />
                </div>
              ))}
            </div>
          )}
        </article>
      </section>
    </div>
  );
}
