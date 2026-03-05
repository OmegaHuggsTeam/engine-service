"use client";

import useSWR from "swr";
import { swrFetcher } from "@/lib/gateway";
import type { AgentStatus } from "@/lib/gateway";
import type { ClusterHealth } from "@/lib/gateway";

export function useAgents() {
  const { data, error, isLoading, mutate } = useSWR<AgentStatus[]>(
    "/api/v1/agents",
    swrFetcher,
    { refreshInterval: 15000, dedupingInterval: 5000 },
  );
  return { agents: data ?? [], loading: isLoading, error, refresh: mutate };
}

export function useClusterHealth() {
  const { data, error, isLoading, mutate } = useSWR<ClusterHealth>(
    "/api/v1/cluster/health",
    swrFetcher,
    { refreshInterval: 30000, dedupingInterval: 5000 },
  );
  return {
    health: data ?? null,
    loading: isLoading,
    error,
    refresh: mutate,
  };
}

export function useUseCases() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/usecases",
    swrFetcher,
    { refreshInterval: 15000, dedupingInterval: 5000 },
  );
  return { usecases: data ?? [], loading: isLoading, error, refresh: mutate };
}

export function useRoadmap() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/usecases/roadmap",
    swrFetcher,
    { refreshInterval: 15000, dedupingInterval: 5000 },
  );
  return { roadmap: data ?? [], loading: isLoading, error, refresh: mutate };
}

export function useCoverage() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/usecases/coverage",
    swrFetcher,
    { refreshInterval: 15000, dedupingInterval: 5000 },
  );
  return { coverage: data ?? [], loading: isLoading, error, refresh: mutate };
}

export function useGaps() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/usecases/gaps",
    swrFetcher,
    { refreshInterval: 15000, dedupingInterval: 5000 },
  );
  return { gaps: data ?? [], loading: isLoading, error, refresh: mutate };
}

export function usePipelineStats() {
  const { data, error, isLoading, mutate } = useSWR(
    "/api/v1/pipeline/stats",
    swrFetcher,
    { refreshInterval: 10000, dedupingInterval: 5000 },
  );
  return {
    stats: data ?? null,
    loading: isLoading,
    error,
    refresh: mutate,
  };
}
