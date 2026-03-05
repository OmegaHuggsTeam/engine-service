"use client";

/**
 * ClusterHealth - Bunker Ops
 *
 * Monitoramento em tempo real do K8s, Gateway e Tailscale.
 */

import HealthPanel from "@/components/HealthPanel";

export default function ClusterHealth() {
  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        border: "1px solid #0f3460",
      }}
    >
      <div className="px-5 py-4 border-b" style={{ borderColor: "#0f3460" }}>
        <h2 className="text-lg font-semibold" style={{ color: "#d0d0e0" }}>
          Bunker Ops
        </h2>
        <p className="text-xs mt-0.5 font-mono" style={{ color: "#606070" }}>
          K8s · Gateway · Tailscale · ChromaDB · Neo4j · n8n
        </p>
      </div>
      <div className="p-5">
        <HealthPanel />
      </div>
    </div>
  );
}
