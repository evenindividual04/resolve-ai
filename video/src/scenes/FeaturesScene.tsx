import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

const features = [
  "Deterministic workflow state machine with strict transitions",
  "Decision traces with costs, confidence, and replay checksums",
  "Replay engine for auditability and consistency verification",
  "Multi-provider LLM routing (Groq, Cerebras, Gemini)",
  "Redis Streams queue mode for asynchronous execution",
  "Escalation management with SLA metadata",
  "Feedback-driven learning pipelines",
  "Adversarial evaluation harness",
];

export const FeaturesScene: React.FC = () => {
  const frame = useCurrentFrame();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const itemOpacity = interpolate(frame, [30, 40], [0, 1]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0a0a0a",
        justifyContent: "center",
        alignItems: "flex-start",
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
          marginBottom: 40,
        }}
      >
        Key Features
      </h1>
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(2, 1fr)",
          gap: 20,
          opacity: itemOpacity,
        }}
      >
        {features.map((feature, i) => {
          const itemY = interpolate(frame, [25 + i * 5, 45 + i * 5], [30, 0]);
          return (
            <div
              key={i}
              style={{
                display: "flex",
                alignItems: "flex-start",
                transform: `translateY(${itemY}px)`,
              }}
            >
              <span style={{ color: "#60a5fa", fontSize: 20, marginRight: 12 }}>▸</span>
              <span style={{ color: "#e5e7eb", fontSize: 20 }}>{feature}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
};