"use client";

/**
 * AgentSpecs - Agent Lab
 *
 * Biblioteca de Skills (Antigravity) e edição da "DNA" dos agentes.
 */

import { useAgents } from "./hooks/useSovereignApi";

const TYPE_COLORS: Record<string, string> = {
  domain: "var(--color-primary)",
  operator: "var(--color-accent)",
  specialist: "var(--color-success)",
};

export default function AgentSpecs() {
  const { agents, loading } = useAgents();

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div className="px-5 py-4 border-b border-[var(--color-border)]">
        <h2 className="text-lg font-semibold text-[var(--color-text)]">
          Agent Lab
        </h2>
        <p className="text-xs mt-0.5 font-mono text-[var(--color-text-muted)]">
          Biblioteca de Skills · {agents.length} Agentes · DNA editável
        </p>
      </div>
      <div className="p-5">
        {loading ? (
          <div className="flex items-center justify-center h-48 text-[var(--color-text-muted)] animate-pulse">
            Carregando agentes...
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {agents.map((a) => (
              <div
                key={a.id}
                className="rounded-lg px-4 py-3 bg-[var(--color-bg)] border border-[var(--color-border)]"
                style={{
                  borderColor: TYPE_COLORS[a.type] || "var(--color-border)",
                }}
              >
                <div className="flex items-center justify-between">
                  <span className="font-medium text-[var(--color-text)]">
                    {a.name}
                  </span>
                  <span
                    className="text-xs px-2 py-0.5 rounded font-mono"
                    style={{
                      background: `${TYPE_COLORS[a.type] || "var(--color-text-muted)"}22`,
                      color: TYPE_COLORS[a.type] || "var(--color-text-muted)",
                    }}
                  >
                    {a.type}
                  </span>
                </div>
                <div className="flex gap-2 mt-2 text-xs font-mono text-[var(--color-text-muted)]">
                  <span>{a.status}</span>
                  {a.success_rate != null && (
                    <span className="text-[var(--color-success)]">
                      {(a.success_rate * 100).toFixed(0)}% success
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
