import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const ArchitectureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const slideUp = spring({ frame: frame - 10, fps, from: 40, to: 0, durationInFrames: 30 });

  const nodes = [
    { title: "Twilio Webhook", sub: "Omnichannel Ingress", color: "#3b82f6" },
    { title: "FastAPI Engine", sub: "Async Event Processing", color: "#10b981" },
    { title: "Groq Llama-3", sub: "Sub-second Inference", color: "#f59e0b" },
    { title: "PostgreSQL", sub: "Immutable Audit Ledger", color: "#8b5cf6" },
  ];

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0B1121",
        justifyContent: "center",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        padding: 100,
        fontFamily: 'system-ui, -apple-system, sans-serif'
      }}
    >
      <h1
        style={{
          color: "#ffffff",
          fontSize: 64,
          fontWeight: 700,
          margin: 0,
          opacity: headerOpacity,
          transform: `translateY(${slideUp}px)`,
          textAlign: "center"
        }}
      >
        Built for <span style={{ color: '#10b981' }}>Scale</span>
      </h1>
      <h2 style={{
        color: "#9ca3af",
        fontSize: 32,
        fontWeight: 400,
        marginTop: 16,
        opacity: headerOpacity,
        textAlign: "center"
      }}>
        High-throughput asynchronous architecture.
      </h2>

      <div style={{
        marginTop: 80,
        display: 'flex',
        gap: 20,
        alignItems: 'center'
      }}>
        {nodes.map((n, i) => {
          const pop = spring({ frame: frame - 30 - (i * 15), fps, from: 0, to: 1, durationInFrames: 25 });
          return (
            <React.Fragment key={i}>
              <div style={{
                background: 'rgba(31, 41, 55, 0.4)',
                border: `1px solid ${n.color}`,
                borderRadius: 24,
                padding: "32px 40px",
                minWidth: 280,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                gap: 12,
                transform: `scale(${pop})`,
                opacity: pop,
                boxShadow: `0 20px 40px rgba(0,0,0,0.3)`
              }}>
                <div style={{ color: '#fff', fontSize: 28, fontWeight: 700, textAlign: 'center' }}>
                  {n.title}
                </div>
                <div style={{ color: '#9ca3af', fontSize: 18, textAlign: 'center' }}>
                  {n.sub}
                </div>
              </div>
              {i < nodes.length - 1 && (
                <div style={{ fontSize: 40, color: '#4b5563', opacity: pop }}>→</div>
              )}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};