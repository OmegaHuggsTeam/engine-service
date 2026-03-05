"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ModelLeaderboard } from "./ModelLeaderboard";
import { ToolComparison } from "./ToolComparison";
import { AgentHeatmap } from "./AgentHeatmap";
import { CostTrends } from "./CostTrends";
import { AnomalyAlerts } from "./AnomalyAlerts";

const TABS = [
  { id: "models", label: "Models" },
  { id: "tools", label: "Tools" },
  { id: "agents", label: "Agents" },
  { id: "trends", label: "Trends" },
  { id: "anomalies", label: "Anomalies" },
] as const;

type TabId = (typeof TABS)[number]["id"];

export function KpiDashboard() {
  const [activeTab, setActiveTab] = useState<TabId>("models");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-[var(--color-text)]">
          KPI Intelligence
        </h1>
        <p className="text-sm text-[var(--color-text-muted)] mt-1">
          Model benchmarks, tool scorecards, cost-quality analysis
        </p>
      </div>

      <div className="flex gap-1 overflow-x-auto pb-1">
        {TABS.map(({ id, label }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors whitespace-nowrap ${
              activeTab === id
                ? "bg-[var(--color-accent)] text-white"
                : "bg-[var(--color-surface)] text-[var(--color-text-muted)] hover:text-[var(--color-text)]"
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <AnimatePresence mode="wait">
        <motion.div
          key={activeTab}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
        >
          {activeTab === "models" && <ModelLeaderboard />}
          {activeTab === "tools" && <ToolComparison />}
          {activeTab === "agents" && <AgentHeatmap />}
          {activeTab === "trends" && <CostTrends />}
          {activeTab === "anomalies" && <AnomalyAlerts />}
        </motion.div>
      </AnimatePresence>
    </div>
  );
}
