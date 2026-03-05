"use client";

import { useKpiAnomalies } from "./hooks/useKpiApi";

function severityBadge(s: string) {
  if (s === "high") return "bg-red-500/20 text-red-400 border-red-500/30";
  if (s === "medium") return "bg-yellow-500/20 text-yellow-400 border-yellow-500/30";
  return "bg-blue-500/20 text-blue-400 border-blue-500/30";
}

export function AnomalyAlerts() {
  const { anomalies, loading, error } = useKpiAnomalies();

  if (loading) return <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-32" />;
  if (error) return <div className="text-sm text-[var(--color-error)]">Failed to load anomalies</div>;
  if (!anomalies.length) {
    return (
      <div className="rounded-xl border border-green-500/20 bg-green-500/5 p-6 text-center">
        <div className="text-lg font-semibold text-green-400">All Clear</div>
        <div className="text-sm text-[var(--color-text-muted)] mt-1">
          No regressions detected in the monitoring window.
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {anomalies.map((a, i) => (
        <div
          key={i}
          className="rounded-xl border border-[var(--color-border)] p-4 bg-[var(--color-surface)]"
        >
          <div className="flex items-start justify-between">
            <div>
              <div className="flex items-center gap-2 mb-1">
                <span
                  className={`px-2 py-0.5 rounded-full text-xs border ${severityBadge(a.severity)}`}
                >
                  {a.severity}
                </span>
                <span className="text-sm font-medium text-[var(--color-text)]">
                  {a.type.replace(/_/g, " ")}
                </span>
              </div>
              <div className="text-xs text-[var(--color-text-muted)]">
                {a.dimension}: <span className="font-mono">{a.value}</span>
              </div>
            </div>
          </div>

          <div className="mt-2 flex gap-4 text-xs font-mono">
            {a.type === "quality_regression" && (
              <>
                <span>Recent: {a.recent_avg?.toFixed(1)}</span>
                <span>Historical: {a.historical_avg?.toFixed(1)}</span>
                <span className="text-[var(--color-error)]">-{a.drop_pct?.toFixed(1)}%</span>
              </>
            )}
            {a.type === "latency_regression" && (
              <>
                <span>Recent: {a.recent_avg_ms?.toFixed(0)}ms</span>
                <span>Historical: {a.historical_avg_ms?.toFixed(0)}ms</span>
                <span className="text-[var(--color-error)]">+{a.increase_pct?.toFixed(1)}%</span>
              </>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
