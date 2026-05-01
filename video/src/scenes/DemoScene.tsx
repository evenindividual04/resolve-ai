import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

const states = [
  { name: "init", color: "#6b7280" },
  { name: "contacted", color: "#3b82f6" },
  { name: "negotiating", color: "#f59e0b" },
  { name: "waiting_for_payment", color: "#8b5cf6" },
  { name: "resolved", color: "#10b981" },
  { name: "escalated", color: "#ef4444" },
];

export const DemoScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);

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
        Workflow Model
      </h1>
      <div
        style={{
          display: "flex",
          gap: 20,
          flexWrap: "wrap",
          justifyContent: "center",
        }}
      >
        {states.map((state, i) => {
          const delay = i * 10;
          const scale = spring({
            frame: frame - delay,
            fps,
            from: 0,
            to: 1,
            durationInFrames: 30,
          });
          const opacity = interpolate(frame, [delay, delay + 15], [0, 1]);
          return (
            <div
              key={state.name}
              style={{
                backgroundColor: state.color,
                padding: "20px 30px",
                borderRadius: 50,
                transform: `scale(${scale})`,
                opacity,
              }}
            >
              <span
                style={{
                  color: "#ffffff",
                  fontSize: 20,
                  fontWeight: 600,
                  textTransform: "capitalize",
                }}
              >
                {state.name.replace(/_/g, " ")}
              </span>
            </div>
          );
        })}
      </div>
    </div>
  );
};