"use client";

import { useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import type { AgentStatus } from "@/lib/gateway";

const TYPE_COLORS: Record<string, string> = {
  domain: "var(--color-success)",
  operator: "var(--color-accent)",
  specialist: "var(--color-primary)",
};

// Mock data generator for extra details
function getMockDetails(id: string, type: string) {
  const caps = type === "domain" ? ["Data Entity", "Validation", "Graph Sync"]
    : type === "operator" ? ["Task Routing", "API Call", "Retry Logic"]
      : ["NLP", "Reasoning", "Classification"];
  const tasks = ["Processed lead data", "Synced Neo4j nodes", "Evaluated trust score"];
  const history = [80, 85, 90, 88, 92, 95];
  return { capabilities: caps, recent_tasks: tasks, history };
}

function getStatusColor(status: string) {
  if (status === "active" || status === "running") return "var(--color-success)";
  if (status === "error" || status === "failed") return "var(--color-error)";
  return "var(--color-text-muted)";
}

function getRateColor(rate: number) {
  if (rate >= 0.8) return "var(--color-success)";
  if (rate >= 0.5) return "var(--color-warning)";
  return "var(--color-error)";
}

const containerVariants = {
  hidden: { opacity: 0 },
  show: {
    opacity: 1,
    transition: { staggerChildren: 0.05 },
  },
};

const itemVariants = {
  hidden: { opacity: 0, y: 10 },
  show: { opacity: 1, y: 0, transition: { duration: 0.3 } },
};

function AgentCard({ agent, onExpand, isExpanded }: { agent: AgentStatus, onExpand: () => void, isExpanded: boolean }) {
  const details = getMockDetails(agent.id, agent.type);
  const color = TYPE_COLORS[agent.type] || "var(--color-text-muted)";
  const statusColor = getStatusColor(agent.status);
  const rate = agent.success_rate ?? 0;
  const rateColor = getRateColor(rate);

  return (
    <motion.div
      variants={itemVariants}
      layout
      onClick={onExpand}
      className="rounded-lg p-4 cursor-pointer relative overflow-hidden flex flex-col transition-all duration-300"
      style={{
        background: "var(--color-bg)",
        border: `1px solid var(--color-border)`,
        boxShadow: `0 0 0 0 ${color}`,
      }}
      whileHover={{
        borderColor: color,
        boxShadow: `0 0 15px -5px ${color}`,
      }}
    >
      <div className="flex items-start justify-between mb-2">
        <div className="flex items-center gap-2">
          {/* Status Indicator */}
          <div className="relative flex h-2.5 w-2.5 items-center justify-center">
            {(agent.status === "active" || agent.status === "running") && (
              <span className="absolute inline-flex h-full w-full animate-ping rounded-full opacity-75" style={{ backgroundColor: statusColor }}></span>
            )}
            <span className="relative inline-flex rounded-full h-2 w-2" style={{ backgroundColor: statusColor }}></span>
          </div>
          <span className="text-sm font-semibold text-[var(--color-text)] truncate max-w-[120px]" title={agent.name}>{agent.name}</span>
        </div>
        {(agent.success_rate !== null) && (
          <span className="text-xs font-mono" style={{ color: rateColor }}>
            {(rate * 100).toFixed(0)}%
          </span>
        )}
      </div>

      <div className="flex flex-wrap gap-1 mt-1 mb-3">
        {details.capabilities.slice(0, 3).map((cap, i) => (
          <span key={i} className="text-[10px] px-1.5 py-0.5 rounded font-mono border" style={{ color: "var(--color-text-secondary)", borderColor: "var(--color-border)", background: "var(--color-surface)" }}>
            {cap}
          </span>
        ))}
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {isExpanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="overflow-hidden mt-1 pt-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-secondary)]"
          >
            <div className="mb-2">
              <strong className="text-[var(--color-text)]">All Capabilities:</strong>
              <div className="flex flex-wrap gap-1 mt-1">
                {details.capabilities.map((c, i) => <span key={i} className="bg-[var(--color-surface-alt)] px-1 rounded">{c}</span>)}
              </div>
            </div>
            <div className="mb-2">
              <strong className="text-[var(--color-text)]">Recent Tasks:</strong>
              <ul className="list-disc pl-4 mt-1 space-y-0.5">
                {details.recent_tasks.map((t, i) => <li key={i}>{t}</li>)}
              </ul>
            </div>
            <div>
              <strong className="text-[var(--color-text)]">Success History:</strong>
              <div className="flex items-end gap-1 mt-1 h-8">
                {details.history.map((h, i) => (
                  <div key={i} className="w-4 bg-[var(--color-border)] rounded-t" style={{ height: `${h}%`, background: getRateColor(h / 100) }} title={`${h}%`} />
                ))}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Progress Bar */}
      <div className="absolute bottom-0 left-0 right-0 h-1 bg-[var(--color-surface)]">
        <div className="h-full transition-all duration-1000" style={{ width: `${rate * 100}%`, backgroundColor: rateColor }} />
      </div>
    </motion.div>
  );
}

export default function AgentGrid() {
  const [agents, setAgents] = useState<AgentStatus[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [expandedId, setExpandedId] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/v1/agents")
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json();
      })
      .then(setAgents)
      .catch((e) => setError(e.message));
  }, []);

  if (error) {
    return (
      <div className="rounded-xl p-6 bg-[var(--color-surface)] border border-[var(--color-border)]">
        <h2 className="text-lg font-semibold mb-3">Agent Health</h2>
        <div className="text-sm font-mono text-[var(--color-error)]">{error}</div>
      </div>
    );
  }

  const grouped = {
    domain: agents.filter((a) => a.type === "domain"),
    operator: agents.filter((a) => a.type === "operator"),
    specialist: agents.filter((a) => a.type === "specialist"),
  };

  return (
    <div
      className="rounded-xl p-6"
      style={{
        background: "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
        border: "1px solid var(--color-border)",
      }}
    >
      <h2 className="text-xl font-bold mb-6 text-[var(--color-text)] flex items-center gap-2">
        Agent Health
        <span className="text-sm font-mono px-2 py-0.5 rounded-full bg-[var(--color-bg)] border border-[var(--color-border)] text-[var(--color-text-secondary)]">
          {agents.length} Total
        </span>
      </h2>

      {(["domain", "operator", "specialist"] as const).map((type) => {
        const typeAgents = grouped[type];
        if (typeAgents.length === 0) return null;
        const color = TYPE_COLORS[type];

        return (
          <div key={type} className="mb-8 last:mb-0">
            {/* Group Header */}
            <div className="flex items-center gap-3 mb-4">
              <span
                className="text-xs font-bold uppercase tracking-wider px-2.5 py-1 rounded-full border"
                style={{ color, borderColor: color, backgroundColor: `${color}15` }}
              >
                {type} ({typeAgents.length})
              </span>
              <div className="flex-1 h-px bg-[var(--color-border)] opacity-50" />
            </div>

            <motion.div
              variants={containerVariants}
              initial="hidden"
              animate="show"
              className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4"
            >
              {typeAgents.map((agent) => (
                <AgentCard
                  key={agent.id}
                  agent={agent}
                  isExpanded={expandedId === agent.id}
                  onExpand={() => setExpandedId(expandedId === agent.id ? null : agent.id)}
                />
              ))}
            </motion.div>
          </div>
        );
      })}
    </div>
  );
}
