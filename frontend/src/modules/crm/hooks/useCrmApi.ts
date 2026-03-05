"use client";

import useSWR from "swr";
import { useCallback } from "react";
import type {
  CrmLead,
  CrmFlow,
  CrmGraph,
  CrmStats,
  CrmLeadCreate,
  CrmFlowCreate,
  CrmInteractionCreate,
} from "@/types/crm";
import { swrFetcher } from "@/lib/gateway";
import {
  createCrmLead as createCrmLeadApi,
  createCrmFlow,
  recordCrmInteraction,
} from "@/lib/gateway";

export function useCrmLeads() {
  const { data, error, isLoading, mutate } = useSWR<CrmLead[]>(
    "/api/v1/crm/leads",
    swrFetcher,
    {
      refreshInterval: 15000,
      dedupingInterval: 5000,
    },
  );

  const refresh = useCallback(() => mutate(), [mutate]);

  const create = useCallback(
    async (createData: CrmLeadCreate) => {
      await createCrmLeadApi(createData);
      await mutate();
    },
    [mutate],
  );

  return {
    leads: data ?? [],
    loading: isLoading,
    error,
    refresh,
    create,
  };
}

export function useCrmFlows() {
  const { data, error, isLoading, mutate } = useSWR<CrmFlow[]>(
    "/api/v1/crm/flows",
    swrFetcher,
    {
      refreshInterval: 15000,
      dedupingInterval: 5000,
    },
  );

  const refresh = useCallback(() => mutate(), [mutate]);

  const create = useCallback(
    async (createData: CrmFlowCreate) => {
      await createCrmFlow(createData);
      await mutate();
    },
    [mutate],
  );

  return {
    flows: data ?? [],
    loading: isLoading,
    error,
    refresh,
    create,
  };
}

export function useCrmGraph() {
  const { data, error, isLoading, mutate } = useSWR<CrmGraph>(
    "/api/v1/crm/graph",
    swrFetcher,
    {
      refreshInterval: 15000,
      dedupingInterval: 5000,
    },
  );

  const refresh = useCallback(() => mutate(), [mutate]);

  return {
    graph: data ?? { nodes: [], edges: [] },
    loading: isLoading,
    error,
    refresh,
  };
}

export function useCrmStats() {
  const { data, error, isLoading, mutate } = useSWR<CrmStats>(
    "/api/v1/crm/stats",
    swrFetcher,
    {
      refreshInterval: 15000,
      dedupingInterval: 5000,
    },
  );

  const refresh = useCallback(() => mutate(), [mutate]);

  return {
    stats: data ?? {
      total_leads: 0,
      total_flows: 0,
      total_interactions: 0,
      avg_trust: 0,
    },
    loading: isLoading,
    error,
    refresh,
  };
}

export function useCrmInteraction() {
  const record = useCallback(async (data: CrmInteractionCreate) => {
    await recordCrmInteraction(data);
  }, []);

  return { record };
}
