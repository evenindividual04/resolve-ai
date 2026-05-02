import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const ProblemScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const slideUp = spring({ frame: frame - 10, fps, from: 40, to: 0, durationInFrames: 30 });

  const bubblePop = spring({ frame: frame - 30, fps, from: 0, to: 1, durationInFrames: 20 });
  const arrowOpacity = interpolate(frame, [70, 90], [0, 1]);
  const jsonPop = spring({ frame: frame - 100, fps, from: 0, to: 1, durationInFrames: 25 });

  const jsonString = `{
  "intent": "refusal_hardship",
  "agreed_amount": null,
  "confidence_score": 0.94,
  "requires_escalation": true
}`;

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
        Unstructured Chaos <span style={{ color: '#4b5563' }}>→</span> <span style={{ color: '#60a5fa' }}>Deterministic State</span>
      </h1>
      <h2 style={{
        color: "#9ca3af",
        fontSize: 32,
        fontWeight: 400,
        marginTop: 16,
        opacity: headerOpacity,
      }}>
        Extracting actionable intent from hostile edges.
      </h2>

      <div style={{
        marginTop: 80,
        display: 'flex',
        alignItems: 'center',
        gap: 60
      }}>
        {/* Unstructured SMS */}
        <div style={{
          backgroundColor: '#374151',
          padding: "24px 32px",
          borderRadius: 24,
          borderBottomLeftRadius: 4,
          color: '#fff',
          fontSize: 28,
          maxWidth: 400,
          opacity: bubblePop,
          transform: `scale(${bubblePop})`,
          boxShadow: '0 4px 12px rgba(0,0,0,0.2)'
        }}>
          "I lost my job last week, stop texting me! I'll have my lawyer call you!"
        </div>

        {/* Transition */}
        <div style={{ fontSize: 60, color: '#4b5563', opacity: arrowOpacity }}>
          →
        </div>

        {/* Structured JSON */}
        <div style={{
          backgroundColor: '#111827',
          border: '1px solid #374151',
          padding: 32,
          borderRadius: 16,
          opacity: jsonPop,
          transform: `scale(${jsonPop})`,
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)'
        }}>
          <pre style={{ margin: 0, color: '#a78bfa', fontSize: 24, fontFamily: 'monospace', lineHeight: 1.5 }}>
            {jsonString}
          </pre>
        </div>
      </div>
    </div>
  );
};