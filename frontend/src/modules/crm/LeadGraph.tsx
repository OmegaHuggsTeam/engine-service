"use client";

import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { useCrmGraph } from "./hooks/useCrmApi";
import { useCrmWebSocket } from "./hooks/useCrmWebSocket";
import type { CrmGraphNode } from "@/types/crm";

function trustColor(trust: number): string {
  if (trust >= 0.7) return "var(--color-success)";
  if (trust >= 0.3) return "var(--color-warning)";
  return "var(--color-error)";
}

const NODE_COLORS: Record<string, string> = {
  lead: "var(--color-primary)",
  flow: "var(--color-accent)",
  agent: "var(--color-success)",
  interaction: "var(--color-warning)",
};

function nodeColor(node: CrmGraphNode): string {
  if (node.type === "lead") {
    const trust = (node.properties?.trust as number) ?? 0.5;
    return trustColor(trust);
  }
  return NODE_COLORS[node.type] ?? "var(--color-text-muted)";
}

const EDGE_STYLES: Record<string, string> = {
  INTERACTED_WITH: "solid",
  PART_OF_FLOW: "dashed",
  BY_AGENT: "dotted",
  FOR_LEAD: "solid",
};

export default function LeadGraph() {
  const svgRef = useRef<SVGSVGElement>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const { graph, loading, refresh } = useCrmGraph();
  const { events } = useCrmWebSocket();
  const [hovered, setHovered] = useState<{ node: CrmGraphNode; x: number; y: number } | null>(null);

  useEffect(() => {
    if (events.length > 0) refresh();
  }, [events.length, refresh]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    const svgElement = svgRef.current;
    const containerElement = containerRef.current;
    if (!svgElement || !containerElement || graph.nodes.length === 0) return;

    const isMobile = window.innerWidth < 768;
    const width = containerElement.clientWidth || 600;
    const height = containerElement.clientHeight || 400;

    const sel = d3.select(svgElement);
    sel.selectAll("*").remove();

    // SVG Filters for Glow Effect
    const defs = sel.append("defs");
    Object.entries(NODE_COLORS).forEach(([type, _]) => {
      const filter = defs.append("filter").attr("id", `glow-${type}`);
      filter.append("feGaussianBlur").attr("stdDeviation", "4").attr("result", "coloredBlur");
      const feMerge = filter.append("feMerge");
      feMerge.append("feMergeNode").attr("in", "coloredBlur");
      feMerge.append("feMergeNode").attr("in", "SourceGraphic");
    });

    const g = sel.append("g");
    const zoom = d3.zoom<SVGSVGElement, unknown>().on("zoom", (e) => {
      g.attr("transform", e.transform);
    });
    sel.call(zoom as any);

    type SimNode = CrmGraphNode & d3.SimulationNodeDatum;
    type SimLink = { source: string; target: string; type: string; weight: number };

    const nodes: SimNode[] = graph.nodes.map((n) => ({ ...n }));
    const links: SimLink[] = graph.edges.map((e) => ({
      source: e.source,
      target: e.target,
      type: e.type,
      weight: (e.properties?.count as number) || 1
    }));

    const simulation = d3
      .forceSimulation<SimNode>(nodes)
      .force("link", d3.forceLink<SimNode, SimLink>(links).id((d) => d.id).distance(80))
      .force("charge", d3.forceManyBody().strength(-200))
      .force("center", d3.forceCenter(width / 2, height / 2));

    if (isMobile) {
      simulation.stop();
      simulation.tick(300); // Compute static layout on mobile
    }

    // Hull groups for flow clusters
    const hullG = g.append("g").attr("class", "hulls");

    // Edges with variable weight
    const link = g
      .selectAll<SVGLineElement, SimLink>("line")
      .data(links)
      .join("line")
      .attr("stroke", "var(--color-border)")
      .attr("stroke-width", d => Math.min(d.weight * 0.5 + 1, 6))
      .attr("stroke-dasharray", (d) => {
        const style = EDGE_STYLES[d.type] ?? "solid";
        if (style === "dashed") return "6 3";
        if (style === "dotted") return "2 2";
        return "none";
      });

    // Nodes with pulsing animation on load
    const node = g
      .selectAll<SVGCircleElement, SimNode>("circle")
      .data(nodes)
      .join("circle")
      .attr("r", 0)
      .attr("fill", (d) => nodeColor(d))
      .attr("stroke", "var(--color-bg)")
      .attr("stroke-width", 2)
      .attr("filter", d => d.type !== 'lead' ? `url(#glow-${d.type})` : null)
      .style("cursor", "pointer")
      .on("mouseover", (e, d) => {
        setHovered({ node: d, x: e.clientX, y: e.clientY });
      })
      .on("mouseout", () => setHovered(null));

    node.transition()
      .duration(700)
      .ease(d3.easeElastic)
      .attr("r", (d) => (d.type === "flow" ? 14 : 9));

    if (!isMobile) {
      node.call(
        d3.drag<SVGCircleElement, SimNode>()
          .on("start", (e, d) => {
            if (!e.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x; d.fy = d.y;
          })
          .on("drag", (e, d) => { d.fx = e.x; d.fy = e.y; })
          .on("end", (e, d) => {
            if (!e.active) simulation.alphaTarget(0);
            d.fx = null; d.fy = null;
          }) as any
      );
    } else {
      // Apply static positions
      node.attr("cx", d => d.x!).attr("cy", d => d.y!);
      link.attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y).attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
    }

    const label = g
      .selectAll<SVGTextElement, SimNode>("text")
      .data(nodes)
      .join("text")
      .text((d) => d.label || d.id)
      .attr("font-size", "10px")
      .attr("font-family", "var(--font-mono)")
      .attr("fill", "var(--color-text-muted)")
      .attr("dx", 16)
      .attr("dy", 4)
      .attr("pointer-events", "none");

    if (!isMobile) {
      simulation.on("tick", () => {
        link
          .attr("x1", (d: any) => d.source.x).attr("y1", (d: any) => d.source.y)
          .attr("x2", (d: any) => d.target.x).attr("y2", (d: any) => d.target.y);
        node.attr("cx", (d) => d.x!).attr("cy", (d) => d.y!);
        label.attr("x", (d) => d.x!).attr("y", (d) => d.y!);

        // Update soft flow clusters
        const flows = nodes.filter(n => n.type === 'flow');
        const hullData = flows.filter(f => f.x && f.y);
        hullG.selectAll("circle.hull-bg")
          .data(hullData)
          .join("circle")
          .attr("class", "hull-bg")
          .attr("cx", d => d.x!)
          .attr("cy", d => d.y!)
          .attr("r", 40)
          .attr("fill", "var(--color-accent)")
          .attr("opacity", 0.05)
          .attr("pointer-events", "none");
      });
    }

    return () => { simulation.stop(); };
  }, [graph, events]);

  return (
    <div ref={containerRef} className="relative h-full min-h-[500px] w-full bg-[var(--color-bg)] rounded-xl border border-[var(--color-border)] overflow-hidden">
      {loading && (
        <div className="absolute inset-0 flex items-center justify-center bg-black/60 z-10 backdrop-blur-sm">
          <span className="text-sm font-mono text-[var(--color-accent)] animate-pulse">
            Analyzing Network Vectors...
          </span>
        </div>
      )}

      {/* Main Graph SVG */}
      <svg ref={svgRef} className="w-full h-full" />

      {/* Legend */}
      <div className="absolute top-4 left-4 bg-[var(--color-surface)]/80 backdrop-blur border border-[var(--color-border)] rounded-lg p-3 pointer-events-none shadow-lg">
        <div className="text-[11px] uppercase tracking-widest font-bold mb-2 text-[var(--color-text)] opacity-80">Network Topography</div>
        <div className="space-y-1.5 font-mono text-[10px] text-[var(--color-text-secondary)]">
          <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[var(--color-primary)] shadow-[0_0_8px_var(--color-primary)]"></div> Lead Nodes</div>
          <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[var(--color-accent)] shadow-[0_0_8px_var(--color-accent)]"></div> Flow Logic</div>
          <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[var(--color-success)] shadow-[0_0_8px_var(--color-success)]"></div> AI Agents</div>
          <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full bg-[var(--color-warning)] shadow-[0_0_8px_var(--color-warning)]"></div> Interactions</div>
        </div>
      </div>

      {/* Mini-map */}
      <div className="hidden sm:block absolute bottom-4 right-4 w-32 h-24 bg-[var(--color-surface)]/90 backdrop-blur border border-[var(--color-border)] rounded-lg pointer-events-none overflow-hidden shadow-xl">
        <div className="absolute inset-0 flex items-center justify-center opacity-40 mix-blend-screen">
          {graph.nodes.length > 0 && (
            <svg viewBox="0 0 100 100" className="w-full h-full scale-[2] relative">
              {graph.nodes.map((n, i) => (
                // Just purely random scatter for minimap UX effect since fetching true bound coords requires state sharing
                <circle key={n.id} cx={50 + (i % 5) * 10 - 20} cy={50 + (i % 4) * 10 - 15} r={2} fill={nodeColor(n)} />
              ))}
            </svg>
          )}
        </div>
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[40px] h-[30px] border border-[var(--color-accent)] opacity-60 rounded pointer-events-none"></div>
      </div>

      {/* Hover Tooltip */}
      {hovered && (
        <div
          className="fixed z-50 p-4 rounded-xl text-xs bg-[var(--color-surface-alt)] border border-[var(--color-accent)] text-[var(--color-text)] shadow-2xl pointer-events-none"
          style={{ left: hovered.x + 15, top: hovered.y + 15, width: 220 }}
        >
          <div className="font-bold mb-1 truncate text-sm" style={{ color: nodeColor(hovered.node) }}>{hovered.node.label || hovered.node.id}</div>
          <div className="font-mono text-[10px] text-[var(--color-text-muted)] uppercase tracking-wider mb-3 border-b border-[var(--color-border)] pb-2">{hovered.node.type}</div>

          <div className="space-y-1.5 font-mono text-[10px]">
            {Object.entries(hovered.node.properties).map(([k, v]) => {
              if (k === 'trust') {
                return (
                  <div key={k} className="flex justify-between items-center bg-black/20 px-2 py-1 rounded">
                    <span className="text-[var(--color-text-muted)] opacity-80">Trust Score</span>
                    <span className="font-bold text-[12px]" style={{ color: trustColor(Number(v)) }}>{Number(v).toFixed(2)}</span>
                  </div>
                );
              }
              return (
                <div key={k} className="flex justify-between w-full items-center">
                  <span className="text-[var(--color-text-muted)] truncate max-w-[90px] opacity-80 capitalize">{k}</span>
                  <span className="truncate max-w-[100px] text-right text-[var(--color-text-secondary)]">{String(v)}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
