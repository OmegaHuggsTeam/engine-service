"use client";

import useSWR from "swr";
import { swrFetcher } from "@/lib/gateway";
import type {
  ModelMetric,
  ToolComparison,
  CostQualityAnalysis,
  DailyAggregate,
  HeatmapEntry,
  KpiAnomaly,
} from "@/types/kpi";

const SWR_OPTS = { refreshInterval: 15000, dedupingInterval: 5000 };

export function useKpiModels() {
  const { data, error, isLoading } = useSWR<ModelMetric[]>(
    "/api/v1/kpi/models",
    swrFetcher,
    SWR_OPTS,
  );
  return { models: data ?? [], loading: isLoading, error };
}

export function useKpiTools() {
  const { data, error, isLoading } = useSWR<ToolComparison[]>(
    "/api/v1/kpi/tools",
    swrFetcher,
    SWR_OPTS,
  );
  return { tools: data ?? [], loading: isLoading, error };
}

export function useKpiCostQuality() {
  const { data, error, isLoading } = useSWR<CostQualityAnalysis>(
    "/api/v1/kpi/cost-quality",
    swrFetcher,
    SWR_OPTS,
  );
  return { analysis: data ?? { by_model: [], by_agent: [], by_task_type: [] }, loading: isLoading, error };
}

export function useKpiTrends(dimension: string = "model") {
  const { data, error, isLoading } = useSWR<DailyAggregate[]>(
    `/api/v1/kpi/trends?dimension=${dimension}`,
    swrFetcher,
    SWR_OPTS,
  );
  return { trends: data ?? [], loading: isLoading, error };
}

export function useKpiHeatmap() {
  const { data, error, isLoading } = useSWR<HeatmapEntry[]>(
    "/api/v1/kpi/agents/heatmap",
    swrFetcher,
    SWR_OPTS,
  );
  return { heatmap: data ?? [], loading: isLoading, error };
}

export function useKpiAnomalies() {
  const { data, error, isLoading } = useSWR<KpiAnomaly[]>(
    "/api/v1/kpi/anomalies",
    swrFetcher,
    SWR_OPTS,
  );
  return { anomalies: data ?? [], loading: isLoading, error };
}
