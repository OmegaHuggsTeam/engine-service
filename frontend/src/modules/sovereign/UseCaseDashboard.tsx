"use client";

import { useState } from "react";
import {
  useUseCases,
  useRoadmap,
  useCoverage,
  useGaps,
} from "./hooks/useSovereignApi";

type Tab = "roadmap" | "coverage" | "gaps";

const TAB_ITEMS: { key: Tab; label: string }[] = [
  { key: "roadmap", label: "Roadmap" },
  { key: "coverage", label: "Coverage" },
  { key: "gaps", label: "Gaps" },
];

export function UseCaseDashboard() {
  const [tab, setTab] = useState<Tab>("roadmap");
  const { usecases, loading: loadingUsecases } = useUseCases();
  const { roadmap, loading: loadingRoadmap } = useRoadmap();
  const { coverage, loading: loadingCoverage } = useCoverage();
  const { gaps, loading: loadingGaps } = useGaps();

  const loading =
    tab === "roadmap"
      ? loadingRoadmap
      : tab === "coverage"
        ? loadingCoverage
        : loadingGaps;

  const roadmapData = Array.isArray(roadmap) ? roadmap : [];
  const coverageData = Array.isArray(coverage) ? coverage : [];
  const gapsData = Array.isArray(gaps) ? gaps : [];

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background:
          "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      <div className="px-5 py-4 border-b border-[var(--color-border)] flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            UseCase Dashboard
          </h2>
          <p className="text-xs mt-0.5 font-mono text-[var(--color-text-muted)]">
            Roadmap · Coverage · Gaps
          </p>
        </div>
        <div className="flex gap-1">
          {TAB_ITEMS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`text-xs px-3 py-1.5 rounded-lg font-mono transition-colors ${
                tab === key
                  ? "bg-[var(--color-surface-alt)] text-[var(--color-accent)] border border-[var(--color-border)]"
                  : "bg-transparent text-[var(--color-text-muted)] border border-transparent"
              }`}
            >
              {label}
            </button>
          ))}
        </div>
      </div>
      <div className="p-5">
        {loading ? (
          <div className="animate-pulse bg-[var(--color-surface-alt)] rounded-lg h-64" />
        ) : (
          <>
            {tab === "roadmap" && (
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b border-[var(--color-border)]">
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        ID
                      </th>
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        Name
                      </th>
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        Domain
                      </th>
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        Priority
                      </th>
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        Status
                      </th>
                      <th className="text-left py-2 px-3 text-[var(--color-text-muted)]">
                        Agents
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {roadmapData.map((row: Record<string, unknown>, i: number) => (
                      <tr
                        key={i}
                        className="border-b border-[var(--color-border)]/50"
                      >
                        <td className="py-2 px-3 text-[var(--color-text)] font-mono">
                          {String(row.id ?? row.ID ?? "-")}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text)]">
                          {String(row.name ?? row.Name ?? "-")}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text)]">
                          {String(row.domain ?? row.Domain ?? "-")}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text)]">
                          {String(row.priority ?? row.Priority ?? "-")}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text)]">
                          {String(row.status ?? row.Status ?? "-")}
                        </td>
                        <td className="py-2 px-3 text-[var(--color-text-muted)]">
                          {Array.isArray(row.agents)
                            ? row.agents.join(", ")
                            : String(row.agents ?? "-")}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                {roadmapData.length === 0 && (
                  <p className="py-8 text-center text-[var(--color-text-muted)]">
                    No roadmap data
                  </p>
                )}
              </div>
            )}
            {tab === "coverage" && (
              <div className="overflow-x-auto">
                <p className="text-sm text-[var(--color-text-muted)] mb-4">
                  Agents × UseCases matrix
                </p>
                {Array.isArray(coverageData) && coverageData.length > 0 ? (
                  <pre className="text-xs font-mono text-[var(--color-text)] overflow-auto max-h-80 p-3 bg-[var(--color-bg)] rounded-lg">
                    {JSON.stringify(coverageData, null, 2)}
                  </pre>
                ) : (
                  <p className="py-8 text-center text-[var(--color-text-muted)]">
                    No coverage data
                  </p>
                )}
              </div>
            )}
            {tab === "gaps" && (
              <div>
                <p className="text-sm text-[var(--color-text-muted)] mb-4">
                  Skills without assigned agents
                </p>
                {gapsData.length > 0 ? (
                  <ul className="space-y-2">
                    {gapsData.map((gap: string | Record<string, unknown>, i: number) => (
                      <li
                        key={i}
                        className="px-3 py-2 rounded-lg bg-[var(--color-bg)] text-[var(--color-text)] text-sm"
                      >
                        {typeof gap === "string" ? gap : JSON.stringify(gap)}
                      </li>
                    ))}
                  </ul>
                ) : (
                  <p className="py-8 text-center text-[var(--color-text-muted)]">
                    No gaps
                  </p>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
