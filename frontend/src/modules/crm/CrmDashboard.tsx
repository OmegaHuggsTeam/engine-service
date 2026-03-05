"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { motion, AnimatePresence } from "framer-motion";
import LeadTable from "./LeadTable";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

const LeadGraph = dynamic(() => import("./LeadGraph"), {
  ssr: false,
  loading: () => <LoadingSkeleton />,
});
const FlowCanvas = dynamic(() => import("./FlowCanvas"), {
  ssr: false,
  loading: () => <LoadingSkeleton />,
});
import { useCrmStats } from "./hooks/useCrmApi";

type Tab = "graph" | "canvas" | "table";

const TAB_ITEMS: { key: Tab; label: string }[] = [
  { key: "graph", label: "Lead Graph" },
  { key: "canvas", label: "Flow Canvas" },
  { key: "table", label: "Lead Table" },
];

export default function CrmDashboard() {
  const [tab, setTab] = useState<Tab>("graph");
  const { stats } = useCrmStats();

  return (
    <div
      className="rounded-xl overflow-hidden flex flex-col h-[calc(100vh-140px)] min-h-[600px] shadow-2xl"
      style={{
        background: "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      {/* Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between px-6 py-4 gap-4 border-b border-[var(--color-border)] shrink-0 bg-black/10">
        <div>
          <h2 className="text-xl font-bold text-[var(--color-text)] tracking-wider uppercase mb-1">
            CRM Console
          </h2>
          <div className="flex gap-x-4 gap-y-1 text-xs font-mono text-[var(--color-text-muted)] flex-wrap opacity-80">
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[var(--color-primary)] shadow-[0_0_5px_var(--color-primary)]"></span> {stats.total_leads} leads</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[var(--color-accent)] shadow-[0_0_5px_var(--color-accent)]"></span> {stats.total_flows} flows</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[var(--color-warning)] shadow-[0_0_5px_var(--color-warning)]"></span> {stats.total_interactions} int.</span>
            <span className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-[var(--color-success)] shadow-[0_0_5px_var(--color-success)]"></span> avg trust {stats.avg_trust.toFixed(2)}</span>
          </div>
        </div>

        {/* Tab switcher */}
        <div className="flex gap-1 bg-[var(--color-bg)] p-1 rounded-xl border border-[var(--color-border)]/50 shadow-inner">
          {TAB_ITEMS.map(({ key, label }) => (
            <button
              key={key}
              onClick={() => setTab(key)}
              className={`relative text-xs px-5 py-2 rounded-lg font-mono transition-colors font-semibold tracking-wider ${tab === key
                  ? "text-[var(--color-text)]"
                  : "text-[var(--color-text-muted)] hover:text-[var(--color-text-secondary)]"
                }`}
            >
              {tab === key && (
                <motion.div
                  layoutId="dash-tab-indicator"
                  className="absolute inset-0 bg-[var(--color-surface-alt)] border border-[var(--color-border)] rounded-lg shadow-md"
                  initial={false}
                  transition={{ type: "spring", bounce: 0.15, duration: 0.5 }}
                />
              )}
              <span className="relative z-10">{label}</span>
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="relative flex-1 p-6 overflow-hidden">
        <AnimatePresence mode="wait">
          <motion.div
            key={tab}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -20 }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="w-full h-full"
          >
            {tab === "graph" && <LeadGraph />}
            {tab === "canvas" && <FlowCanvas />}
            {tab === "table" && <LeadTable />}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
