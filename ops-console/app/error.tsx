"use client";

interface ErrorPageProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function ErrorPage({ error, reset }: ErrorPageProps) {
  return (
    <div className="page-shell animate-in">
      <div className="card" style={{ maxWidth: 560, margin: "40px auto" }}>
        <div className="section-header">
          <div>
            <div className="h6">Server error</div>
            <h2 className="section-title">Failed to load this page</h2>
          </div>
          <span className="status-chip danger">Error</span>
        </div>
        <div className="subtle" style={{ marginBottom: 16, lineHeight: 1.6 }}>
          The page could not be rendered. This is a server-side error, not an empty state.
        </div>
        {error.digest && (
          <div className="subtle" style={{ fontFamily: "var(--font-mono)", fontSize: "0.8rem", marginBottom: 16 }}>
            Digest: {error.digest}
          </div>
        )}
        <button className="button" onClick={reset}>
          Try again
        </button>
      </div>
    </div>
  );
}
