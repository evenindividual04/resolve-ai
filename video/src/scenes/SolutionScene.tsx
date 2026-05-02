import React from "react";
import { useCurrentFrame, interpolate, spring, useVideoConfig } from "remotion";

export const SolutionScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const headerOpacity = interpolate(frame, [0, 20], [0, 1]);
  const slideUp = spring({ frame: frame - 10, fps, from: 40, to: 0, durationInFrames: 30 });
  
  const codePop = spring({ frame: frame - 30, fps, from: 0, to: 1, durationInFrames: 25 });
  const blockAlertPop = spring({ frame: frame - 90, fps, from: 0, to: 1, durationInFrames: 20 });

  const pythonCode = `class LegalThreatPolicy(PolicyGuardrail):
    def evaluate(self, event: Event, context: Context) -> PolicyResult:
        if event.intent == "refusal_legal":
            return PolicyResult(
                passed=False,
                violation_type="legal_escalation_required",
                recommended_action=WorkflowAction.HALT
            )
        return PolicyResult(passed=True)`;

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
        <span style={{ color: '#60a5fa' }}>Hardcoded Guardrails</span> &gt; Probabilistic LLMs
      </h1>
      <h2 style={{
        color: "#9ca3af",
        fontSize: 32,
        fontWeight: 400,
        marginTop: 16,
        opacity: headerOpacity,
        textAlign: "center"
      }}>
        Intercept unsafe actions before they execute.
      </h2>

      <div style={{ marginTop: 60, position: 'relative' }}>
        {/* Code Editor */}
        <div style={{
          backgroundColor: '#111827',
          border: '1px solid #374151',
          padding: 40,
          borderRadius: 16,
          opacity: codePop,
          transform: `scale(${codePop})`,
          boxShadow: '0 20px 40px rgba(0,0,0,0.4)',
          minWidth: 800
        }}>
          <div style={{ display: 'flex', gap: 8, marginBottom: 24 }}>
            <div style={{ width: 12, height: 12, borderRadius: 6, background: '#ef4444' }} />
            <div style={{ width: 12, height: 12, borderRadius: 6, background: '#eab308' }} />
            <div style={{ width: 12, height: 12, borderRadius: 6, background: '#22c55e' }} />
            <span style={{ marginLeft: 16, color: '#6b7280', fontSize: 14, fontFamily: 'monospace' }}>policy_engine.py</span>
          </div>
          <pre style={{ margin: 0, color: '#e5e7eb', fontSize: 22, fontFamily: 'monospace', lineHeight: 1.6 }}>
            <span style={{ color: '#c678dd' }}>class</span> <span style={{ color: '#e5c07b' }}>LegalThreatPolicy</span>(PolicyGuardrail):{'\n'}
            {'    '}<span style={{ color: '#c678dd' }}>def</span> <span style={{ color: '#61afef' }}>evaluate</span>(self, event, context):{'\n'}
            {'        '}<span style={{ color: '#c678dd' }}>if</span> event.intent == <span style={{ color: '#98c379' }}>"refusal_legal"</span>:{'\n'}
            {'            '}<span style={{ color: '#c678dd' }}>return</span> PolicyResult({'\n'}
            {'                '}passed=<span style={{ color: '#d19a66' }}>False</span>,{'\n'}
            {'                '}action=<span style={{ color: '#e5c07b' }}>WorkflowAction</span>.HALT{'\n'}
            {'            '}){'\n'}
            {'        '}<span style={{ color: '#c678dd' }}>return</span> PolicyResult(passed=<span style={{ color: '#d19a66' }}>True</span>)
          </pre>
        </div>

        {/* Intercept Alert */}
        <div style={{
          position: 'absolute',
          bottom: -40,
          right: -40,
          background: '#7f1d1d',
          border: '2px solid #ef4444',
          padding: '16px 32px',
          borderRadius: 99,
          color: '#fff',
          fontSize: 24,
          fontWeight: 700,
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          opacity: blockAlertPop,
          transform: `scale(${blockAlertPop}) rotate(-5deg)`,
          boxShadow: '0 10px 30px rgba(239,68,68,0.3)'
        }}>
          <span>⛔</span> ACTION HALTED
        </div>
      </div>
    </div>
  );
};