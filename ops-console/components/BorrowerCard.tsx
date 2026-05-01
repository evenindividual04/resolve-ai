import type { BorrowerProfile } from "../types";

interface BorrowerCardProps {
  profile: BorrowerProfile;
}

function dpd_variant(dpd: number): string {
  if (dpd > 90) return "danger";
  if (dpd > 30) return "warn";
  return "ok";
}

const CHANNEL_EMOJI: Record<string, string> = {
  whatsapp: "💬",
  sms: "📱",
  email: "✉",
  voice: "📞",
};

export function BorrowerCard({ profile }: BorrowerCardProps) {
  return (
    <div className="stack" style={{ gap: 14 }}>
      {/* DNC / Legal flags — shown first, most important */}
      {(!!profile.dnc_flag || !!profile.legal_flag) && (
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          {!!profile.dnc_flag && (
            <span className="status-chip halted" style={{ fontWeight: 700 }}>
              ⊘ DNC — No Contact
            </span>
          )}
          {!!profile.legal_flag && (
            <span className="status-chip warn" style={{ fontWeight: 700 }}>
              ⚖ Legal Escalation
            </span>
          )}
        </div>
      )}

      {/* Risk band + segment */}
      <div style={{ display: "flex", gap: 8, flexWrap: "wrap", alignItems: "center" }}>
        <span className={`status-chip risk-band-${profile.risk_band}`} style={{ textTransform: "uppercase", letterSpacing: "0.08em" }}>
          {profile.risk_band}
        </span>
        <span className="status-chip info">
          {profile.loan_segment.replace(/_/g, " ")}
        </span>
        <span className="subtle" style={{ fontSize: "0.85rem" }}>
          {CHANNEL_EMOJI[profile.preferred_channel] ?? "📡"} {profile.preferred_channel}
        </span>
        <span className="subtle" style={{ fontSize: "0.85rem" }}>
          {profile.language} · {profile.timezone}
        </span>
      </div>

      {/* DPD + stats */}
      <div className="panel-grid" style={{ gridTemplateColumns: "repeat(3, 1fr)" }}>
        <div className="metric-card">
          <span className="metric-label h6">DPD</span>
          <div className={`metric-value status-chip ${dpd_variant(profile.dpd)}`} style={{ border: "none", padding: 0, fontSize: "1.4rem", background: "transparent" }}>
            {profile.dpd}d
          </div>
        </div>
        <div className="metric-card">
          <span className="metric-label h6">Prior defaults</span>
          <div className="metric-value" style={{ fontSize: "1.4rem" }}>{profile.prior_defaults}</div>
        </div>
        <div className="metric-card">
          <span className="metric-label h6">Contact attempts</span>
          <div className="metric-value" style={{ fontSize: "1.4rem" }}>{profile.contact_attempts}</div>
        </div>
      </div>

      {profile.notes && (
        <div className="subtle" style={{ fontSize: "0.86rem", fontStyle: "italic", lineHeight: 1.5 }}>
          "{profile.notes}"
        </div>
      )}
    </div>
  );
}
