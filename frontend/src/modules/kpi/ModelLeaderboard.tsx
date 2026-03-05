"use client";

import { useKpiModels } from "./hooks/useKpiApi";

export function ModelLeaderboard() {
  const { models, loading, error } = useKpiModels();

  if (loading) return <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-48" />;
  if (error) return <div className="text-sm text-[var(--color-error)]">Failed to load model data</div>;
  if (!models.length) return <div className="text-sm text-[var(--color-text-muted)]">No model metrics yet. Process some requests to see data.</div>;

  return (
    <div className="rounded-xl border border-[var(--color-border)] overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-[var(--color-surface-alt)] text-[var(--color-text-muted)]">
            <th className="text-left px-4 py-3 font-medium">Model</th>
            <th className="text-right px-4 py-3 font-medium">Requests</th>
            <th className="text-right px-4 py-3 font-medium">Tokens</th>
            <th className="text-right px-4 py-3 font-medium">Cost ($)</th>
            <th className="text-right px-4 py-3 font-medium">Avg Quality</th>
            <th className="text-right px-4 py-3 font-medium">Avg Latency</th>
            <th className="text-right px-4 py-3 font-medium">$/Quality Pt</th>
            <th className="text-right px-4 py-3 font-medium">Failures</th>
          </tr>
        </thead>
        <tbody>
          {models.map((m, i) => (
            <tr
              key={m.model_id}
              className={`border-t border-[var(--color-border)] ${
                i === 0 ? "bg-green-500/5" : ""
              } hover:bg-[var(--color-surface-alt)] transition-colors`}
            >
              <td className="px-4 py-3 font-mono font-medium text-[var(--color-text)]">
                {i === 0 && <span className="mr-1" title="Best ROI">*</span>}
                {m.model_id}
              </td>
              <td className="px-4 py-3 text-right font-mono">{m.total_requests}</td>
              <td className="px-4 py-3 text-right font-mono">{m.total_tokens?.toLocaleString()}</td>
              <td className="px-4 py-3 text-right font-mono">${m.total_cost?.toFixed(4)}</td>
              <td className="px-4 py-3 text-right font-mono">{m.avg_quality?.toFixed(1) ?? "-"}</td>
              <td className="px-4 py-3 text-right font-mono">{m.avg_latency?.toFixed(0)}ms</td>
              <td className="px-4 py-3 text-right font-mono font-bold">${m.cost_per_quality?.toFixed(4)}</td>
              <td className="px-4 py-3 text-right font-mono text-[var(--color-error)]">{m.failures || 0}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
