"use client";

import { useState } from "react";
import AgentSpecs from "@/modules/sovereign/AgentSpecs";
import { UseCaseDashboard } from "@/modules/sovereign/UseCaseDashboard";
import { ErrorBoundary } from "@/components/ErrorBoundary";

type Tab = "agents" | "usecases";

export default function AgentLabPage() {
  const [tab, setTab] = useState<Tab>("agents");

  return (
    <ErrorBoundary>
      <div className="space-y-4">
        <div className="flex gap-2">
          <button
            onClick={() => setTab("agents")}
            className={`text-sm px-3 py-1.5 rounded-lg font-mono ${
              tab === "agents"
                ? "bg-[var(--color-surface-alt)] text-[var(--color-accent)]"
                : "text-[var(--color-text-muted)]"
            }`}
          >
            Agent Lab
          </button>
          <button
            onClick={() => setTab("usecases")}
            className={`text-sm px-3 py-1.5 rounded-lg font-mono ${
              tab === "usecases"
                ? "bg-[var(--color-surface-alt)] text-[var(--color-accent)]"
                : "text-[var(--color-text-muted)]"
            }`}
          >
            UseCases
          </button>
        </div>
        {tab === "agents" && <AgentSpecs />}
        {tab === "usecases" && <UseCaseDashboard />}
      </div>
    </ErrorBoundary>
  );
}
