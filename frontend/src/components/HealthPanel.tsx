"use client";

import { memo } from "react";
import { useClusterHealth } from "@/modules/sovereign/hooks/useSovereignApi";

const STATUS_COLORS: Record<string, string> = {
  "[OK]": "var(--color-success)",
  "[FAIL]": "var(--color-error)",
  "[SKIP]": "var(--color-text-muted)",
};

const STATUS_LABELS: Record<string, string> = {
  "[OK]": "OK",
  "[FAIL]": "FAIL",
  "[SKIP]": "SKIP",
};

function HealthPanelComponent() {
  const { health, loading, error, refresh } = useClusterHealth();

  return (
    <div
      className="rounded-xl p-6"
      style={{
        background: "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-[var(--color-text)]">
          Cluster Health
        </h2>
        <button
          onClick={() => refresh()}
          disabled={loading}
          className="text-sm px-3 py-1 rounded-lg transition-colors bg-[var(--color-surface-alt)] text-[var(--color-text-secondary)] disabled:opacity-60"
        >
          {loading ? "..." : "Refresh"}
        </button>
      </div>

      {error && (
        <div className="rounded-lg p-3 mb-4 text-sm font-mono bg-[var(--color-error)]/15 text-[var(--color-error)]">
          Gateway unreachable: {error instanceof Error ? error.message : String(error)}
        </div>
      )}

      {health && (
        <>
          <div className="flex gap-4 mb-4">
            {[
              { label: "OK", value: health.summary.ok, color: "var(--color-success)" },
              { label: "FAIL", value: health.summary.fail, color: "var(--color-error)" },
              { label: "SKIP", value: health.summary.skip, color: "var(--color-text-muted)" },
            ].map(({ label, value, color }) => (
              <div key={label} className="text-center">
                <div className="text-2xl font-bold font-mono" style={{ color }}>
                  {value}
                </div>
                <div className="text-xs text-[var(--color-text-secondary)]">
                  {label}
                </div>
              </div>
            ))}
          </div>

          <div className="space-y-2">
            {Object.entries(health.services).map(([name, svc]) => (
              <div
                key={name}
                className="flex items-center justify-between rounded-lg px-4 py-3 bg-[var(--color-bg)]"
              >
                <div className="flex items-center gap-3">
                  <div
                    className="w-2.5 h-2.5 rounded-full"
                    style={{
                      backgroundColor: STATUS_COLORS[svc.status] || "var(--color-text-muted)",
                    }}
                  />
                  <span className="font-medium text-[var(--color-text)]">{name}</span>
                </div>
                <div className="flex items-center gap-3">
                  <span
                    className="text-xs font-mono px-2 py-0.5 rounded"
                    style={{
                      background: `${STATUS_COLORS[svc.status] || "var(--color-text-muted)"}22`,
                      color: STATUS_COLORS[svc.status] || "var(--color-text-muted)",
                    }}
                  >
                    {STATUS_LABELS[svc.status] || svc.status}
                  </span>
                  <span className="text-xs font-mono text-[var(--color-text-muted)]">
                    {svc.detail}
                  </span>
                </div>
              </div>
            ))}
          </div>

          <div className="text-xs mt-3 font-mono text-[var(--color-text-muted)]">
            Last check: {health.timestamp.slice(0, 19)}
          </div>
        </>
      )}
    </div>
  );
}

export default memo(HealthPanelComponent);
