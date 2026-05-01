export default function Loading() {
  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card" style={{ minHeight: 180 }}>
          {[["40%", 10], ["70%", 44], ["90%", 16]].map(([w, h], i) => (
            <div key={i} style={{
              height: h as number, width: w as string, borderRadius: 8, marginBottom: 14,
              background: "rgba(255,255,255,0.04)",
              backgroundImage: "linear-gradient(90deg, transparent 25%, rgba(255,255,255,0.06) 50%, transparent 75%)",
              backgroundSize: "200% 100%",
              animation: "shimmer 1.5s infinite",
            }} />
          ))}
        </div>
        <aside className="card shell-panel">
          <div className="panel-grid">
            {[1, 2, 3].map(i => (
              <div key={i} className="metric-card" style={{ minHeight: 72 }}>
                <div style={{ height: 8, width: "50%", borderRadius: 6, marginBottom: 12, background: "rgba(255,255,255,0.05)", animation: "shimmer 1.5s infinite", backgroundSize: "200% 100%" }} />
                <div style={{ height: 28, width: "60%", borderRadius: 6, background: "rgba(255,255,255,0.05)", animation: "shimmer 1.5s infinite", backgroundSize: "200% 100%" }} />
              </div>
            ))}
          </div>
        </aside>
      </section>
    </div>
  );
}
