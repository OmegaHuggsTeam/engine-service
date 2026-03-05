"use client";

import { useState } from "react";
import { useKpiTrends, useKpiCostQuality } from "./hooks/useKpiApi";

export function CostTrends() {
  const [dimension, setDimension] = useState("model");
  const { trends, loading: trendsLoading } = useKpiTrends(dimension);
  const { analysis, loading: cqLoading } = useKpiCostQuality();

  const loading = trendsLoading || cqLoading;

  if (loading) return <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-48" />;

  return (
    <div className="space-y-6">
      {/* Cost-Quality Summary */}
      {analysis.by_model.length > 0 && (
        <div className="rounded-xl border border-[var(--color-border)] p-4">
          <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">$/Quality Point by Model</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
            {analysis.by_model.map((m) => (
              <div key={m.model} className="bg-[var(--color-surface-alt)] rounded-lg p-3">
                <div className="font-mono text-xs text-[var(--color-text)] font-medium">{m.model}</div>
                <div className="mt-1 text-2xl font-bold font-mono text-[var(--color-text)]">
                  ${m.cost_per_quality_point?.toFixed(4)}
                </div>
                <div className="text-xs text-[var(--color-text-muted)] mt-1">
                  {m.total_requests} requests | quality: {m.avg_quality?.toFixed(1)}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Daily Trends */}
      <div className="rounded-xl border border-[var(--color-border)] p-4">
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-sm font-semibold text-[var(--color-text)]">Daily Trends</h3>
          <div className="flex gap-1">
            {["model", "agent", "task_type"].map((d) => (
              <button
                key={d}
                onClick={() => setDimension(d)}
                className={`px-3 py-1 rounded text-xs ${
                  dimension === d
                    ? "bg-[var(--color-accent)] text-white"
                    : "bg-[var(--color-surface-alt)] text-[var(--color-text-muted)]"
                }`}
              >
                {d.replace("_", " ")}
              </button>
            ))}
          </div>
        </div>

        {!trends.length ? (
          <div className="text-sm text-[var(--color-text-muted)]">No trend data available.</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr className="text-[var(--color-text-muted)]">
                  <th className="text-left px-2 py-1">Date</th>
                  <th className="text-left px-2 py-1">Value</th>
                  <th className="text-right px-2 py-1">Requests</th>
                  <th className="text-right px-2 py-1">Cost</th>
                  <th className="text-right px-2 py-1">Quality</th>
                  <th className="text-right px-2 py-1">Latency</th>
                  <th className="text-right px-2 py-1">Cache %</th>
                </tr>
              </thead>
              <tbody>
                {trends.slice(0, 30).map((t, i) => (
                  <tr key={i} className="border-t border-[var(--color-border)]">
                    <td className="px-2 py-1.5 font-mono">{t.date}</td>
                    <td className="px-2 py-1.5 font-mono">{t.dimension_value}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{t.total_requests}</td>
                    <td className="px-2 py-1.5 text-right font-mono">${t.total_cost_usd?.toFixed(4)}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{t.avg_quality?.toFixed(1) ?? "-"}</td>
                    <td className="px-2 py-1.5 text-right font-mono">{t.avg_latency_ms?.toFixed(0)}ms</td>
                    <td className="px-2 py-1.5 text-right font-mono">{(t.cache_hit_rate * 100).toFixed(1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
