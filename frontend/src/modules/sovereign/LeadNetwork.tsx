"use client";

/**
 * LeadNetwork - Grafo Neo4j (Leads, Redes Sociais, Conexões)
 *
 * Visualiza o grafo de conhecimento do Neural Link CRM.
 */

import LeadGraph from "@/modules/crm/LeadGraph";
import { PipelineStats } from "@/components/PipelineStats";

export default function LeadNetwork() {
  return (
    <div className="space-y-4">
      <PipelineStats />
      <div
        className="rounded-xl overflow-hidden"
        style={{
          background:
            "linear-gradient(135deg, var(--color-surface) 0%, var(--color-surface-alt) 100%)",
          border: "1px solid var(--color-border)",
        }}
      >
        <div className="px-5 py-4 border-b border-[var(--color-border)]">
          <h2 className="text-lg font-semibold text-[var(--color-text)]">
            Neural Link (CRM)
          </h2>
          <p className="text-xs mt-0.5 font-mono text-[var(--color-text-muted)]">
            Grafo Neo4j · Leads, Redes Sociais, Conexões
          </p>
        </div>
        <div className="p-5 min-h-[400px]">
          <LeadGraph />
        </div>
      </div>
    </div>
  );
}
