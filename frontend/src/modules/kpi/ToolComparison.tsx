"use client";

import { useKpiTools } from "./hooks/useKpiApi";

const TOOL_COLORS: Record<string, string> = {
  kiro: "#22c55e",
  cursor: "#3b82f6",
  anti_gravity: "#a855f7",
  claude_code: "#f59e0b",
};

export function ToolComparison() {
  const { tools, loading, error } = useKpiTools();

  if (loading) return <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-48" />;
  if (error) return <div className="text-sm text-[var(--color-error)]">Failed to load tool data</div>;
  if (!tools.length) return <div className="text-sm text-[var(--color-text-muted)]">No tool reviews yet. Submit reviews to see comparison.</div>;

  const maxScore = Math.max(...tools.map((t) => t.avg_score || 0), 1);

  return (
    <div className="space-y-4">
      {tools.map((t) => (
        <div
          key={t.tool_name}
          className="rounded-xl border border-[var(--color-border)] p-4 bg-[var(--color-surface)]"
        >
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-3">
              <div
                className="w-3 h-3 rounded-full"
                style={{ background: TOOL_COLORS[t.tool_name] || "#888" }}
              />
              <span className="font-semibold text-[var(--color-text)] capitalize">
                {t.tool_name.replace(/_/g, " ")}
              </span>
              <span className="text-xs text-[var(--color-text-muted)]">
                {t.review_count} reviews
              </span>
            </div>
            <span className="text-2xl font-bold font-mono text-[var(--color-text)]">
              {t.avg_score?.toFixed(1)}
            </span>
          </div>

          <div className="grid grid-cols-3 gap-4 text-xs">
            {[
              { label: "Correto (40%)", value: t.avg_correto },
              { label: "Completo (30%)", value: t.avg_completo },
              { label: "Qualidade (30%)", value: t.avg_qualidade },
            ].map(({ label, value }) => (
              <div key={label}>
                <div className="text-[var(--color-text-muted)] mb-1">{label}</div>
                <div className="h-2 bg-[var(--color-surface-alt)] rounded-full overflow-hidden">
                  <div
                    className="h-full rounded-full transition-all"
                    style={{
                      width: `${value}%`,
                      background: TOOL_COLORS[t.tool_name] || "#888",
                    }}
                  />
                </div>
                <div className="font-mono mt-0.5">{value?.toFixed(1)}</div>
              </div>
            ))}
          </div>

          <div className="flex gap-4 mt-3 text-xs text-[var(--color-text-muted)]">
            <span>Done: {t.total_done}/{t.total_planned}</span>
            {t.total_critical > 0 && (
              <span className="text-[var(--color-error)]">Critical: {t.total_critical}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
