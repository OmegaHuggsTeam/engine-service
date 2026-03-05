"use client";

import { Component, type ReactNode } from "react";

export class ErrorBoundary extends Component<
  { children: ReactNode; fallback?: ReactNode },
  { hasError: boolean }
> {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  render() {
    if (this.state.hasError) {
      return (
        this.props.fallback || (
          <div className="p-4 text-[var(--color-error)]">
            Something went wrong.
          </div>
        )
      );
    }
    return this.props.children;
  }
}
