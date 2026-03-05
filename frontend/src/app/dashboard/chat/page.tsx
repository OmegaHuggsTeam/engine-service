"use client";

import { OrchestratorChat } from "@/modules/ai/OrchestratorChat";
import { ErrorBoundary } from "@/components/ErrorBoundary";

export default function ChatPage() {
  return (
    <ErrorBoundary>
      <div
        className="rounded-xl overflow-hidden"
        style={{
          background: "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
          border: "1px solid var(--color-border)",
        }}
      >
        <div className="px-5 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            Neural Link Chat
          </h2>
          <p className="text-xs mt-0.5 font-mono text-[var(--color-text-muted)]">
            Orchestrator · Streaming AI
          </p>
        </div>
        <div className="p-5 h-[500px]">
          <OrchestratorChat />
        </div>
      </div>
    </ErrorBoundary>
  );
}
