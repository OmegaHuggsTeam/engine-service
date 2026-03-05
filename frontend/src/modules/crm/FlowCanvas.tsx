"use client";

import { useCallback, useEffect, useState } from "react";
import {
  ReactFlow,
  Background,
  Controls,
  addEdge,
  useNodesState,
  useEdgesState,
  Handle,
  Position,
  type Node,
  type Edge,
  type Connection,
  type NodeProps
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { useCrmFlows } from "./hooks/useCrmApi";
import type { CrmFlow, CrmFlowCreate } from "@/types/crm";

// Obsidian Slate dark overrides
const proOptions = { hideAttribution: true };
const rfStyle = {
  background: "var(--color-bg)",
};

const CustomNode = ({ data }: NodeProps) => {
  const statusColor = data.status === 'active' ? 'var(--color-success)' : data.status === 'paused' ? 'var(--color-warning)' : 'var(--color-text-muted)';
  return (
    <div className="bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl p-3 min-w-[200px] shadow-md relative group transition-colors hover:border-[var(--color-accent)]">
      <Handle type="target" position={Position.Left} className="w-2 h-2 !bg-[var(--color-accent)] !border-[var(--color-bg)]" />

      {/* Lead Count Badge */}
      <div className="absolute -top-3 -right-3 w-6 h-6 bg-[var(--color-primary)] text-white text-[10px] rounded-full flex items-center justify-center font-bold border-[3px] border-[var(--color-bg)] shadow z-10">
        {Number(data.lead_count) || 0}
      </div>

      <div className="flex justify-between items-center mb-1.5 gap-2">
        <span className="font-bold text-[var(--color-text)] text-sm truncate">{String(data.label)}</span>
        <span className="text-[9px] uppercase px-1.5 py-0.5 rounded border font-mono tracking-wider shrink-0"
          style={{ color: statusColor, borderColor: statusColor, background: `${statusColor}15` }}>
          {String(data.status || 'draft')}
        </span>
      </div>
      <div className="text-[10px] text-[var(--color-text-secondary)] opacity-80 line-clamp-2 leading-relaxed">
        {String(data.objective || 'No objective set')}
      </div>

      <Handle type="source" position={Position.Right} className="w-2 h-2 !bg-[var(--color-accent)] !border-[var(--color-bg)]" />
    </div>
  );
};

const nodeTypes = { custom: CustomNode };

function flowToNode(flow: CrmFlow, index: number): Node {
  return {
    id: flow.id,
    type: 'custom',
    position: { x: 100 + index * 260, y: 100 + (index % 2) * 140 },
    data: {
      label: flow.name,
      status: flow.status,
      objective: flow.objective,
      lead_count: flow.lead_count,
    },
  };
}

export default function FlowCanvas() {
  const { flows, loading, refresh, create } = useCrmFlows();
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [showCreate, setShowCreate] = useState(false);
  const [snapGrid, setSnapGrid] = useState(true);
  const [menu, setMenu] = useState<{ id: string; top: number; left: number } | null>(null);
  const [isMobile, setIsMobile] = useState(false);

  const [newFlow, setNewFlow] = useState<CrmFlowCreate>({
    name: "",
    objective: "",
  });

  useEffect(() => {
    setIsMobile(window.innerWidth < 768);
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Sync flows → nodes
  useEffect(() => {
    setNodes(flows.map((f, i) => flowToNode(f, i)));
    // We can also create synthetic edges between sequential flows for demo
    const syntheticEdges: Edge[] = [];
    for (let i = 0; i < flows.length - 1; i++) {
      syntheticEdges.push({
        id: `e-${flows[i].id}-${flows[i + 1].id}`,
        source: flows[i].id,
        target: flows[i + 1].id,
        label: 'TRANSITION_TO',
        style: { stroke: "var(--color-accent)", strokeDasharray: "4 4" },
        animated: true,
        className: 'hover-edge-label', // managed by css
      });
    }
    setEdges(syntheticEdges);
  }, [flows, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) =>
        addEdge(
          {
            ...connection,
            label: 'CUSTOM_RELATION',
            style: { stroke: "var(--color-accent)", strokeDasharray: "6 3" },
            animated: true,
            className: 'hover-edge-label',
          },
          eds,
        ),
      );
    },
    [setEdges],
  );

  const handleCreate = async () => {
    if (!newFlow.name.trim()) return;
    await create(newFlow);
    setNewFlow({ name: "", objective: "" });
    setShowCreate(false);
  };

  const onNodeContextMenu = useCallback(
    (event: React.MouseEvent, node: Node) => {
      event.preventDefault();
      setMenu({
        id: node.id,
        top: event.clientY,
        left: event.clientX,
      });
    },
    [],
  );

  const onPaneClick = useCallback(() => setMenu(null), []);

  return (
    <div className="relative h-full min-h-[500px] w-full rounded-xl border border-[var(--color-border)] overflow-hidden">
      {/* Edge Hover CSS injection */}
      <style dangerouslySetInnerHTML={{
        __html: `
        .hover-edge-label .react-flow__edge-textbg { fill: var(--color-bg); rx: 4; ry: 4; }
        .hover-edge-label .react-flow__edge-text { fill: var(--color-text-secondary); opacity: 0; transition: opacity 0.2s; font-family: monospace; font-size: 10px; pointer-events: none; }
        .react-flow__edge:hover .react-flow__edge-text { opacity: 1; }
      `}} />

      {/* Toolbar */}
      <div className="absolute top-4 left-4 z-10 flex gap-2">
        <button
          onClick={() => setShowCreate(!showCreate)}
          className="text-xs px-4 py-2 rounded-lg font-mono transition-colors hover:brightness-110 shadow-lg"
          style={{
            background: "var(--color-surface)",
            color: "var(--color-accent)",
            border: "1px solid var(--color-accent)",
          }}
        >
          + New Flow
        </button>
        <button
          onClick={() => setSnapGrid(!snapGrid)}
          className={`text-xs px-4 py-2 rounded-lg font-mono transition-colors shadow-lg ${snapGrid ? '' : 'opacity-60'}`}
          style={{
            background: "var(--color-surface)",
            color: "var(--color-text)",
            border: "1px solid var(--color-border)",
          }}
        >
          {snapGrid ? 'Grid Snap ON' : 'Grid Snap OFF'}
        </button>
        <button
          onClick={refresh}
          className="text-xs px-4 py-2 rounded-lg font-mono transition-colors hover:bg-[var(--color-surface-alt)] shadow-lg"
          style={{
            background: "var(--color-surface)",
            color: "var(--color-text-secondary)",
            border: "1px solid var(--color-border)",
          }}
        >
          Refresh
        </button>
      </div>

      {/* Create form */}
      {showCreate && (
        <div
          className="absolute top-16 left-4 z-20 p-4 rounded-xl shadow-2xl"
          style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)" }}
        >
          <input
            className="block w-[250px] mb-3 px-3 py-2 rounded-lg text-sm transition-colors focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
            style={{ background: "var(--color-bg)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
            placeholder="Flow name"
            value={newFlow.name}
            onChange={(e) => setNewFlow({ ...newFlow, name: e.target.value })}
          />
          <input
            className="block w-[250px] mb-4 px-3 py-2 rounded-lg text-sm transition-colors focus:ring-1 focus:ring-[var(--color-accent)] focus:outline-none"
            style={{ background: "var(--color-bg)", color: "var(--color-text)", border: "1px solid var(--color-border)" }}
            placeholder="Objective"
            value={newFlow.objective}
            onChange={(e) =>
              setNewFlow({ ...newFlow, objective: e.target.value })
            }
          />
          <button
            onClick={handleCreate}
            className="text-sm px-4 py-2 rounded-lg w-full font-medium transition-colors hover:brightness-110"
            style={{ background: "var(--color-success)", color: "var(--color-bg)" }}
          >
            Create Flow
          </button>
        </div>
      )}

      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/50 z-10 backdrop-blur-sm">
          <span className="text-sm font-mono text-[var(--color-text-muted)] animate-pulse">
            Loading flows...
          </span>
        </div>
      )}

      {/* Context Menu */}
      {menu && (
        <div
          style={{ top: menu.top, left: menu.left }}
          className="fixed z-50 bg-[var(--color-surface)] border border-[var(--color-border)] rounded-lg shadow-2xl flex flex-col min-w-[160px] overflow-hidden text-sm"
          onClick={onPaneClick}
        >
          <button className="px-4 py-2.5 text-left hover:bg-[var(--color-surface-alt)] text-[var(--color-text)] transition-colors border-b border-[var(--color-border)]/50">Edit Flow Configuration</button>
          <button className="px-4 py-2.5 text-left hover:bg-[var(--color-surface-alt)] text-[var(--color-text)] transition-colors border-b border-[var(--color-border)]/50">View Registered Leads</button>
          <button className="px-4 py-2.5 text-left hover:bg-[var(--color-surface-alt)] text-[var(--color-accent)] font-medium transition-colors border-b border-[var(--color-border)]/50 text-xs tracking-wider uppercase">Deploy to n8n ✨</button>
          <button className="px-4 py-2.5 text-left hover:bg-[var(--color-error)]/20 text-[var(--color-error)] transition-colors -my-px font-medium">Delete Context</button>
        </div>
      )}

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeContextMenu={onNodeContextMenu}
        onPaneClick={onPaneClick}
        proOptions={proOptions}
        colorMode="dark"
        style={rfStyle}
        fitView
        snapToGrid={snapGrid}
        snapGrid={[20, 20]}
        nodesDraggable={!isMobile}
        zoomOnScroll={!isMobile}
        panOnDrag={!isMobile} // Disable map drag on mobile
      >
        <Background color="var(--color-text-muted)" gap={20} size={1} />
        {/* Floating Controls with standard +/- and Fit View */}
        <Controls
          style={{ background: "var(--color-surface)", border: "1px solid var(--color-border)", borderRadius: "8px", overflow: "hidden", display: "flex", flexDirection: "column" }}
          showInteractive={false} // hide lock button
        />
      </ReactFlow>
    </div>
  );
}
