const BASE =
  process.env.NEXT_PUBLIC_GATEWAY_URL || "http://localhost:8766";

/** SWR fetcher - uses relative URLs (rewritten to gateway via next.config) */
export const swrFetcher = (url: string) =>
  fetch(url).then((r) => {
    if (!r.ok) throw new Error(`${r.status}`);
    return r.json();
  });

export interface ServiceHealth {
  status: string;
  detail: string;
}

export interface ClusterHealth {
  timestamp: string;
  services: Record<string, ServiceHealth>;
  summary: { total: number; ok: number; fail: number; skip: number };
}

export interface AgentStatus {
  id: string;
  name: string;
  type: string;
  status: string;
  success_rate: number | null;
}

export async function fetchClusterHealth(): Promise<ClusterHealth> {
  const res = await fetch(`${BASE}/api/v1/cluster/health`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchAgents(): Promise<AgentStatus[]> {
  const res = await fetch(`${BASE}/api/v1/agents`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// CRM
// ---------------------------------------------------------------------------

import type {
  CrmLead,
  CrmFlow,
  CrmGraph,
  CrmStats,
  CrmLeadCreate,
  CrmLeadUpdate,
  CrmFlowCreate,
  CrmFlowUpdate,
  CrmInteractionCreate,
  CrmLeadScore,
} from "@/types/crm";

export async function fetchCrmLeads(): Promise<CrmLead[]> {
  const res = await fetch(`${BASE}/api/v1/crm/leads`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function createCrmLead(data: CrmLeadCreate): Promise<CrmLead> {
  const res = await fetch(`${BASE}/api/v1/crm/leads`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function updateCrmLead(
  leadId: string,
  data: CrmLeadUpdate,
): Promise<CrmLead> {
  const res = await fetch(`${BASE}/api/v1/crm/leads/${leadId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function deleteCrmLead(leadId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/crm/leads/${leadId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
}

export async function searchCrmLeads(query: string): Promise<CrmLead[]> {
  const res = await fetch(
    `${BASE}/api/v1/crm/leads/search?q=${encodeURIComponent(query)}`,
    { cache: "no-store" },
  );
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchLeadScore(leadId: string): Promise<CrmLeadScore> {
  const res = await fetch(`${BASE}/api/v1/crm/leads/${leadId}/score`, {
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchCrmGraph(): Promise<CrmGraph> {
  const res = await fetch(`${BASE}/api/v1/crm/graph`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchCrmFlows(): Promise<CrmFlow[]> {
  const res = await fetch(`${BASE}/api/v1/crm/flows`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function createCrmFlow(data: CrmFlowCreate): Promise<CrmFlow> {
  const res = await fetch(`${BASE}/api/v1/crm/flows`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function updateCrmFlow(
  flowId: string,
  data: CrmFlowUpdate,
): Promise<CrmFlow> {
  const res = await fetch(`${BASE}/api/v1/crm/flows/${flowId}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function deleteCrmFlow(flowId: string): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/crm/flows/${flowId}`, {
    method: "DELETE",
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
}

export async function recordCrmInteraction(
  data: CrmInteractionCreate,
): Promise<{ id: string }> {
  const res = await fetch(`${BASE}/api/v1/crm/interactions`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchCrmStats(): Promise<CrmStats> {
  const res = await fetch(`${BASE}/api/v1/crm/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

// ---------------------------------------------------------------------------
// KPI Metrics Intelligence
// ---------------------------------------------------------------------------

import type {
  ModelMetric,
  ModelHistory,
  ToolComparison,
  ToolReview,
  ToolReviewSubmit,
  CostQualityAnalysis,
  DailyAggregate,
  HeatmapEntry,
  KpiAnomaly,
  ModelRecommendation,
} from "@/types/kpi";

export async function fetchKpiModels(): Promise<ModelMetric[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/models`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiModelHistory(modelId: string): Promise<ModelHistory[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/models/${encodeURIComponent(modelId)}/history`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiTools(): Promise<ToolComparison[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/tools`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiToolHistory(toolName: string): Promise<ToolReview[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/tools/${encodeURIComponent(toolName)}/history`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function submitKpiToolReview(data: ToolReviewSubmit): Promise<ToolReview> {
  const res = await fetch(`${BASE}/api/v1/kpi/tools/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiCostQuality(): Promise<CostQualityAnalysis> {
  const res = await fetch(`${BASE}/api/v1/kpi/cost-quality`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiTrends(dimension: string = "model"): Promise<DailyAggregate[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/trends?dimension=${encodeURIComponent(dimension)}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiHeatmap(): Promise<HeatmapEntry[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/agents/heatmap`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiAnomalies(): Promise<KpiAnomaly[]> {
  const res = await fetch(`${BASE}/api/v1/kpi/anomalies`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchKpiRecommend(taskType: string = "", minQuality: number = 7.0): Promise<ModelRecommendation> {
  const params = new URLSearchParams();
  if (taskType) params.set("task_type", taskType);
  params.set("min_quality", String(minQuality));
  const res = await fetch(`${BASE}/api/v1/kpi/recommend?${params}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}

export async function fetchPipelineStats(): Promise<Record<string, unknown>> {
  const res = await fetch(`${BASE}/api/v1/pipeline/stats`, { cache: "no-store" });
  if (!res.ok) throw new Error(`Gateway error: ${res.status}`);
  return res.json();
}
