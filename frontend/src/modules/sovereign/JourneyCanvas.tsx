"use client";

/**
 * JourneyCanvas - GPS de Automação Neural Link
 *
 * Mapa visual dos fluxos n8n integrados aos agentes.
 * Cada nó: Trigger (Jitbit), Agent (SpecialistAgent), Sink (Neo4j, Telegram).
 * Status de pulsação: verde ativo, vermelho travado.
 * Integração: POST /api/v1/jitbit/error para mostrar onde o macro parou.
 */

import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
  MarkerType,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";

// Cores Bunker High-Tech (sincronizadas com HealthPanel e K8s Pods)
const COLORS = {
  trigger: "#e94560",
  agent: "#448aff",
  sink: "#00e676",
  error: "#e94560",
  health: "#00e676",
  border: "#0f3460",
  bg: "#1a1a2e",
  surface: "#0e1117",
};

type NodeType = "trigger" | "agent" | "sink";

interface JourneyNodeData extends Record<string, unknown> {
  label: string;
  type: NodeType;
  status: "active" | "error" | "idle";
  detail?: string;
}

// Pipeline principal: Jitbit -> SpecialistAgent -> Neo4j -> Telegram
const INITIAL_NODES: Node<JourneyNodeData>[] = [
  {
    id: "jitbit",
    type: "input",
    position: { x: 80, y: 200 },
    data: {
      label: "Macro Jitbit",
      type: "trigger",
      status: "active",
      detail: "Trigger de automação",
    },
    style: {
      background: COLORS.bg,
      color: "#d0d0e0",
      border: `2px solid ${COLORS.trigger}`,
      borderRadius: "10px",
      padding: "14px 18px",
      fontSize: "13px",
      fontWeight: 600,
    },
  },
  {
    id: "specialist",
    type: "default",
    position: { x: 320, y: 200 },
    data: {
      label: "SpecialistAgent",
      type: "agent",
      status: "active",
      detail: "Análise e enriquecimento",
    },
    style: {
      background: COLORS.bg,
      color: "#d0d0e0",
      border: `2px solid ${COLORS.agent}`,
      borderRadius: "10px",
      padding: "14px 18px",
      fontSize: "13px",
      fontWeight: 600,
    },
  },
  {
    id: "neo4j",
    type: "default",
    position: { x: 560, y: 120 },
    data: {
      label: "Neo4j",
      type: "sink",
      status: "active",
      detail: "Grafo de conhecimento",
    },
    style: {
      background: COLORS.bg,
      color: "#d0d0e0",
      border: `2px solid ${COLORS.sink}`,
      borderRadius: "10px",
      padding: "14px 18px",
      fontSize: "13px",
      fontWeight: 600,
    },
  },
  {
    id: "telegram",
    type: "output",
    position: { x: 560, y: 280 },
    data: {
      label: "Telegram",
      type: "sink",
      status: "active",
      detail: "Notificações",
    },
    style: {
      background: COLORS.bg,
      color: "#d0d0e0",
      border: `2px solid ${COLORS.sink}`,
      borderRadius: "10px",
      padding: "14px 18px",
      fontSize: "13px",
      fontWeight: 600,
    },
  },
];

const INITIAL_EDGES: Edge[] = [
  {
    id: "e-jitbit-specialist",
    source: "jitbit",
    target: "specialist",
    animated: true,
    style: { stroke: COLORS.trigger, strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.trigger },
  },
  {
    id: "e-specialist-neo4j",
    source: "specialist",
    target: "neo4j",
    animated: true,
    style: { stroke: COLORS.agent, strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.agent },
  },
  {
    id: "e-specialist-telegram",
    source: "specialist",
    target: "telegram",
    animated: true,
    style: { stroke: COLORS.agent, strokeWidth: 2 },
    markerEnd: { type: MarkerType.ArrowClosed, color: COLORS.agent },
  },
];

const BASE = process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8766";
const WS_BASE = process.env.NEXT_PUBLIC_GATEWAY_WS_URL || "ws://localhost:8766";

function applyJitbitError(
  setNodes: React.Dispatch<React.SetStateAction<Node<JourneyNodeData>[]>>,
  error: { step: string; line?: number; error?: string } | null,
) {
  if (error) {
    setNodes((nds) =>
      nds.map((n) => {
        if (n.id === "jitbit") {
          return {
            ...n,
            style: {
              ...n.style,
              border: `2px solid ${COLORS.error}`,
              boxShadow: "0 0 12px rgba(233,69,96,0.4)",
            },
            data: { ...n.data, status: "error" as const },
          };
        }
        return n;
      }),
    );
  } else {
    setNodes((nds) =>
      nds.map((n) =>
        n.id === "jitbit"
          ? {
              ...n,
              style: {
                ...n.style,
                border: `2px solid ${COLORS.trigger}`,
                boxShadow: "none",
              },
              data: { ...n.data, status: "active" as const },
            }
          : n,
      ),
    );
  }
}

export default function JourneyCanvas() {
  const [nodes, setNodes, onNodesChange] = useNodesState(INITIAL_NODES);
  const [edges, setEdges, onEdgesChange] = useEdgesState(INITIAL_EDGES);
  const [jitbitError, setJitbitError] = useState<{
    step: string;
    line?: number;
    error?: string;
  } | null>(null);
  const [deployLoading, setDeployLoading] = useState(false);

  // WebSocket: sincronia visual quando heal conclui ou erro chega
  useEffect(() => {
    const url = `${WS_BASE}/api/v1/ws/journey-events`;
    let ws: WebSocket | null = null;
    const connect = () => {
      try {
        ws = new WebSocket(url);
        ws.onmessage = (ev) => {
          try {
            const msg = JSON.parse(ev.data);
            if (msg.type === "heal_completed") {
              setJitbitError(null);
              applyJitbitError(setNodes, null);
            } else if (msg.type === "jitbit_error" && msg.payload) {
              const err = {
                step: msg.payload.step || "",
                line: msg.payload.line,
                error: msg.payload.error,
              };
              setJitbitError(err);
              applyJitbitError(setNodes, err);
            }
          } catch {
            // ignore parse errors
          }
        };
      } catch {
        // WebSocket indisponível
      }
    };
    connect();
    return () => {
      ws?.close();
    };
  }, [setNodes]);

  // Poll jitbit status (fallback quando WS desconectado)
  useEffect(() => {
    const check = async () => {
      try {
        const res = await fetch(`${BASE}/api/v1/jitbit/status`, {
          cache: "no-store",
        });
        if (res.ok) {
          const data = await res.json();
          if (data.last_error) {
            setJitbitError(data.last_error);
            applyJitbitError(setNodes, data.last_error);
          } else {
            setJitbitError(null);
            applyJitbitError(setNodes, null);
          }
        }
      } catch {
        // Endpoint indisponível
      }
    };
    check();
    const interval = setInterval(check, 10000);
    return () => clearInterval(interval);
  }, [setNodes]);

  const handleDeployHealing = useCallback(async () => {
    setDeployLoading(true);
    try {
      const res = await fetch(`${BASE}/api/v1/jitbit/heal`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action: "restart" }),
      });
      if (res.ok) {
        setJitbitError(null);
        setNodes((nds) =>
          nds.map((n) =>
            n.id === "jitbit"
              ? {
                  ...n,
                  style: { ...n.style, border: `2px solid ${COLORS.trigger}` },
                  data: { ...n.data, status: "active" as const },
                }
              : n,
          ),
        );
      }
    } catch {
      // Fallback: apenas reset visual
      setJitbitError(null);
      setNodes((nds) =>
        nds.map((n) =>
          n.id === "jitbit"
            ? {
                ...n,
                style: { ...n.style, border: `2px solid ${COLORS.trigger}` },
                data: { ...n.data, status: "active" as const },
              }
            : n,
        ),
      );
    } finally {
      setDeployLoading(false);
    }
  }, [setNodes]);

  return (
    <div
      className="rounded-xl overflow-hidden"
      style={{
        background: "linear-gradient(135deg, #1a1a2e 0%, #16213e 100%)",
        border: "1px solid #0f3460",
      }}
    >
      <div className="flex items-center justify-between px-5 py-4 border-b" style={{ borderColor: "#0f3460" }}>
        <div>
          <h2 className="text-lg font-semibold" style={{ color: "#d0d0e0" }}>
            Jornadas
          </h2>
          <p className="text-xs mt-0.5 font-mono" style={{ color: "#606070" }}>
            GPS de Automação · Lead Detectado → SpecialistAgent → Neo4j → Telegram
          </p>
        </div>
        <div className="flex gap-2">
          {jitbitError && (
            <button
              onClick={handleDeployHealing}
              disabled={deployLoading}
              className="text-xs px-4 py-2 rounded-lg font-mono font-medium transition-all"
              style={{
                background: "rgba(0, 230, 118, 0.2)",
                color: "#00e676",
                border: "1px solid #00e67644",
              }}
            >
              {deployLoading ? "..." : "🚀 Auto-Healing"}
            </button>
          )}
        </div>
      </div>

      {jitbitError && (
        <div
          className="mx-5 mt-3 px-4 py-3 rounded-lg text-sm font-mono"
          style={{
            background: "rgba(233, 69, 96, 0.15)",
            color: "#e94560",
            border: "1px solid rgba(233,69,96,0.4)",
          }}
        >
          Macro parou em: {jitbitError.step}
          {jitbitError.line != null && ` (linha ${jitbitError.line})`}
          {jitbitError.error && ` — ${jitbitError.error}`}
        </div>
      )}

      <div className="h-[420px] p-2">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          fitView
          proOptions={{ hideAttribution: true }}
          colorMode="dark"
          style={{ background: "#0d0d1a" }}
        >
          <Background color="#1a1a2e" gap={20} />
          <Controls
            style={{ background: "#1a1a2e", border: "1px solid #0f3460" }}
          />
        </ReactFlow>
      </div>
    </div>
  );
}
