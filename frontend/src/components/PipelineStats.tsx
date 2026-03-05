"use client";

import Link from "next/link";
import { usePipelineStats } from "@/modules/sovereign/hooks/useSovereignApi";

function formatPercent(val: unknown): string {
  if (typeof val === "number") return `${(val * 100).toFixed(1)}%`;
  if (typeof val === "string" && val.endsWith("%")) return val;
  return String(val ?? "-");
}

export function PipelineStats() {
  const { stats, loading, error } = usePipelineStats();

  if (loading) {
    return (
      <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-24" />
    );
  }

  if (error) {
    return (
      <div className="rounded-lg p-3 text-sm text-[var(--color-error)]">
        Failed to load pipeline stats
      </div>
    );
  }

  const s = stats as Record<string, unknown> | null;
  if (!s) {
    return (
      <div className="rounded-lg p-3 text-sm text-[var(--color-text-muted)]">
        No pipeline stats available
      </div>
    );
  }

  const layerDist = (s.layer_distribution ?? s.layer_dist ?? s.layers) as
    | Record<string, number>
    | undefined;
  const layerEntries = layerDist
    ? Object.entries(layerDist)
    : [];

  return (
    <div
      className="rounded-xl p-4"
      style={{
        background:
          "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      <h3 className="text-sm font-semibold text-[var(--color-text)] mb-3">
        Pipeline Stats
        <Link href="/dashboard/kpi" className="text-xs text-[var(--color-accent)] hover:underline ml-2">View KPI Dashboard →</Link>
      </h3>
      <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3 text-sm">
        <div>
          <div className="text-[var(--color-text-muted)] text-xs">
            Total requests
          </div>
          <div className="font-mono text-[var(--color-text)]">
            {String(s.total_requests ?? s.requests ?? "-")}
          </div>
        </div>
        <div>
          <div className="text-[var(--color-text-muted)] text-xs">
            Cache hit rate
          </div>
          <div className="font-mono text-[var(--color-text)]">
            {formatPercent(s.cache_hit_rate ?? s.cache_rate)}
          </div>
        </div>
        <div>
          <div className="text-[var(--color-text-muted)] text-xs">
            Avg tokens/req
          </div>
          <div className="font-mono text-[var(--color-text)]">
            {String(s.avg_tokens ?? s.tokens_per_request ?? "-")}
          </div>
        </div>
        <div>
          <div className="text-[var(--color-text-muted)] text-xs">
            Avg cost ($)
          </div>
          <div className="font-mono text-[var(--color-text)]">
            {typeof s.avg_cost === "number"
              ? s.avg_cost.toFixed(4)
              : String(s.avg_cost ?? "-")}
          </div>
        </div>
        <div>
          <div className="text-[var(--color-text-muted)] text-xs">
            Eval skip rate
          </div>
          <div className="font-mono text-[var(--color-text)]">
            {formatPercent(s.eval_skip_rate ?? s.evaluation_skip_rate ?? s.skip_rate)}
          </div>
        </div>
      </div>
      {layerEntries.length > 0 && (
        <div className="mt-4">
          <div className="text-[var(--color-text-muted)] text-xs mb-2">
            Layer distribution
          </div>
          <div className="flex gap-2 items-end h-16">
            {layerEntries.map(([name, val]) => {
              const maxVal = Math.max(
                ...layerEntries.map(([, v]) => Number(v) || 0),
                1
              );
              const pct = (Number(val) / maxVal) * 100;
              const barHeight = Math.max(4, (pct / 100) * 48);
              return (
                <div
                  key={name}
                  className="flex-1 flex flex-col items-center gap-1 min-w-0"
                >
                  <div
                    className="w-full bg-[var(--color-accent)]/40 rounded-t"
                    style={{ height: barHeight }}
                  />
                  <span className="text-[10px] font-mono text-[var(--color-text-muted)] truncate w-full text-center">
                    {name}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
