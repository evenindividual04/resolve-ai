import React from "react";
import { useCurrentFrame, interpolate } from "remotion";

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();

  const titleOpacity = interpolate(frame, [0, 30], [0, 1]);
  const subtitleOpacity = interpolate(frame, [20, 50], [0, 1]);
  const urlOpacity = interpolate(frame, [40, 70], [0, 1]);

  return (
    <div
      style={{
        flex: 1,
        backgroundColor: "#0a0a0a",
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
          fontSize: 80,
          fontWeight: 800,
          margin: 0,
          opacity: titleOpacity,
        }}
      >
        Resolve AI
      </h1>
      <p
        style={{
          color: "#60a5fa",
          fontSize: 32,
          fontWeight: 400,
          marginTop: 20,
          opacity: subtitleOpacity,
        }}
      >
        Operate AI Workflows with Confidence
      </p>
      <p
        style={{
          color: "#9ca3af",
          fontSize: 24,
          marginTop: 40,
          opacity: urlOpacity,
        }}
      >
        github.com/resolve-ai
      </p>
    </div>
  );
};