"use client";

import React, { Component, ReactNode } from "react";

interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

interface ErrorBoundaryProps {
  children: ReactNode;
  fallback?: React.ComponentType<{ error: Error; resetError: () => void }>;
}

export class ErrorBoundary extends Component<ErrorBoundaryProps, ErrorBoundaryState> {
  constructor(props: ErrorBoundaryProps) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    console.error("Uncaught client error:", error, errorInfo);
  }

  resetError = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError && this.state.error && this.props.fallback) {
      const FallbackComponent = this.props.fallback;
      return <FallbackComponent error={this.state.error} resetError={this.resetError} />;
    }

    if (this.state.hasError && this.state.error) {
      return (
        <div className="card split-12" style={{ margin: "40px auto", maxWidth: "600px" }}>
          <div className="section-header">
            <div>
              <div className="h6">Client error</div>
              <h2 className="section-title">An unexpected error occurred</h2>
            </div>
          </div>
          <div className="subtle text-center">
            A client-side error occurred. Try resetting this component or reload the page.
          </div>
          <div className="flex-center mt-4">
            <button className="button" onClick={this.resetError}>
              Try again
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}
