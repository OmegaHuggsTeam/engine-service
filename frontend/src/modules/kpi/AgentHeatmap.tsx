"use client";

import { useKpiHeatmap } from "./hooks/useKpiApi";

function qualityColor(q: number): string {
  if (q >= 8) return "bg-green-500/30 text-green-400";
  if (q >= 6) return "bg-yellow-500/20 text-yellow-400";
  if (q >= 4) return "bg-orange-500/20 text-orange-400";
  return "bg-red-500/20 text-red-400";
}

export function AgentHeatmap() {
  const { heatmap, loading, error } = useKpiHeatmap();

  if (loading) return <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-48" />;
  if (error) return <div className="text-sm text-[var(--color-error)]">Failed to load heatmap data</div>;
  if (!heatmap.length) return <div className="text-sm text-[var(--color-text-muted)]">No agent performance data yet.</div>;

  // Build matrix
  const agents = [...new Set(heatmap.map((h) => h.agent))].sort();
  const taskTypes = [...new Set(heatmap.map((h) => h.task_type))].sort();
  const lookup = new Map(heatmap.map((h) => [`${h.agent}:${h.task_type}`, h]));

  return (
    <div className="rounded-xl border border-[var(--color-border)] overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[var(--color-surface-alt)]">
            <th className="text-left px-3 py-2 font-medium text-[var(--color-text-muted)]">Agent</th>
            {taskTypes.map((tt) => (
              <th key={tt} className="text-center px-3 py-2 font-medium text-[var(--color-text-muted)] text-xs">
                {tt}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {agents.map((agent) => (
            <tr key={agent} className="border-t border-[var(--color-border)]">
              <td className="px-3 py-2 font-mono text-xs text-[var(--color-text)]">{agent}</td>
              {taskTypes.map((tt) => {
                const entry = lookup.get(`${agent}:${tt}`);
                if (!entry) return <td key={tt} className="px-3 py-2 text-center text-[var(--color-text-muted)]">-</td>;
                return (
                  <td key={tt} className="px-3 py-2 text-center">
                    <span
                      className={`inline-block px-2 py-1 rounded font-mono text-xs ${qualityColor(entry.avg_quality)}`}
                      title={`${entry.request_count} requests`}
                    >
                      {entry.avg_quality.toFixed(1)}
                    </span>
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
