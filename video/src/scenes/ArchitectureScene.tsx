import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const ArchitectureScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const boxDelay = 15;

  const box1Scale = spring({
    frame: frame - boxDelay,
    fps,
    from: 0,
    to: 1,
    durationInFrames: 30,
  });
  const box2Scale = spring({
    frame: frame - boxDelay - 15,
    fps,
    from: 0,
    to: 1,
    durationInFrames: 30,
  });
  const box3Scale = spring({
    frame: frame - boxDelay - 30,
    fps,
    from: 0,
    to: 1,
    durationInFrames: 30,
  });

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#111827",
        justifyContent: "center",
        alignItems: "center",
        display: "flex",
        flexDirection: "column",
        padding: 100,
      }}
    >
      <h1
        style={{
          color: "#ffffff",
          fontSize: 64,
          fontWeight: 700,
          margin: 0,
          opacity: headerOpacity,
          marginBottom: 60,
        }}
      >
        Architecture
      </h1>
      <div
        style={{
          display: "flex",
          gap: 40,
          alignItems: "center",
        }}
      >
        <div
          style={{
            backgroundColor: "#1e40af",
            padding: 30,
            borderRadius: 12,
            transform: `scale(${box1Scale})`,
            minWidth: 280,
          }}
        >
          <h3 style={{ color: "#fff", margin: 0, fontSize: 24, marginBottom: 10 }}>
            API Layer
          </h3>
          <p style={{ color: "#bfdbfe", margin: 0, fontSize: 18 }}>
            FastAPI for event ingestion and workflow queries
          </p>
        </div>
        <div style={{ color: "#60a5fa", fontSize: 48 }}>→</div>
        <div
          style={{
            backgroundColor: "#047857",
            padding: 30,
            borderRadius: 12,
            transform: `scale(${box2Scale})`,
            minWidth: 280,
          }}
        >
          <h3 style={{ color: "#fff", margin: 0, fontSize: 24, marginBottom: 10 }}>
            Workflow Core
          </h3>
          <p style={{ color: "#bbf7d0", margin: 0, fontSize: 18 }}>
            Deterministic orchestration with strict state transitions
          </p>
        </div>
        <div style={{ color: "#60a5fa", fontSize: 48 }}>→</div>
        <div
          style={{
            backgroundColor: "#92400e",
            padding: 30,
            borderRadius: 12,
            transform: `scale(${box3Scale})`,
            minWidth: 280,
          }}
        >
          <h3 style={{ color: "#fff", margin: 0, fontSize: 24, marginBottom: 10 }}>
            Operator Console
          </h3>
          <p style={{ color: "#fcd3ae", margin: 0, fontSize: 18 }}>
            Next.js console for triage and review
          </p>
        </div>
      </div>
    </div>
  );
};