interface ProgressBarProps {
  value: number;     // 0–1 fraction
  variant?: "ok" | "warn" | "danger" | "info";
  label?: string;
  showPercent?: boolean;
}

export function ProgressBar({ value, variant, label, showPercent = true }: ProgressBarProps) {
  const pct = Math.round(Math.min(1, Math.max(0, value)) * 100);
  const autoVariant = variant ?? (pct >= 70 ? "ok" : pct >= 50 ? "warn" : "danger");

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 6, width: "100%" }}>
      {(label || showPercent) && (
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          {label && <span className="h6">{label}</span>}
          {showPercent && (
            <span className="subtle" style={{ fontSize: "0.88rem", fontFamily: "var(--font-mono)" }}>
              {pct}%
            </span>
          )}
        </div>
      )}
      <div className="progress-track">
        <div
          className={`progress-fill ${autoVariant}`}
          style={{ width: `${pct}%` }}
          role="progressbar"
          aria-valuenow={pct}
          aria-valuemin={0}
          aria-valuemax={100}
          aria-label={label ?? "Progress"}
        />
      </div>
    </div>
  );
}
