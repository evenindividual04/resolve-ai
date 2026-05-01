export function LoadingSkeleton() {
  return (
    <div className="page-shell animate-in">
      <section className="hero">
        <div className="hero-card" style={{ minHeight: 220 }}>
          <div style={{
            height: 12, width: "40%", borderRadius: 8,
            background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s infinite",
            marginBottom: 16
          }} />
          <div style={{
            height: 48, width: "75%", borderRadius: 8,
            background: "linear-gradient(90deg, rgba(255,255,255,0.04) 25%, rgba(255,255,255,0.08) 50%, rgba(255,255,255,0.04) 75%)",
            backgroundSize: "200% 100%",
            animation: "shimmer 1.5s infinite",
          }} />
        </div>
        <aside className="card shell-panel">
          <div className="panel-grid">
            {[1, 2, 3].map(i => (
              <div key={i} className="metric-card" style={{ minHeight: 72 }}>
                <div style={{
                  height: 8, width: "50%", borderRadius: 6, marginBottom: 12,
                  background: "rgba(255,255,255,0.05)",
                  animation: "shimmer 1.5s infinite",
                  backgroundSize: "200% 100%",
                }} />
                <div style={{
                  height: 28, width: "60%", borderRadius: 6,
                  background: "rgba(255,255,255,0.05)",
                  animation: "shimmer 1.5s infinite",
                  backgroundSize: "200% 100%",
                }} />
              </div>
            ))}
          </div>
        </aside>
      </section>
    </div>
  );
}

export default function Loading() {
  return <LoadingSkeleton />;
}
