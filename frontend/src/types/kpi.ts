// KPI Contract Types

export interface ModelMetric {
  model_id: string;
  total_requests: number;
  total_tokens: number;
  total_cost: number;
  avg_quality: number | null;
  avg_latency: number;
  failures: number;
  cost_per_quality: number;
}

export interface ModelHistory {
  date: string;
  total_requests: number;
  tokens_in: number;
  tokens_out: number;
  cost_usd: number;
  avg_quality: number | null;
  avg_latency: number;
  failures: number;
}

export interface ToolComparison {
  tool_name: string;
  review_count: number;
  avg_score: number;
  avg_correto: number;
  avg_completo: number;
  avg_qualidade: number;
  total_done: number;
  total_planned: number;
  total_critical: number;
}

export interface ToolReview {
  id: string;
  tool_name: string;
  sprint_date: string;
  score_correto: number;
  score_completo: number;
  score_qualidade: number;
  nota_geral: number;
  deliverables_done: number;
  deliverables_total: number;
  issues_critical: number;
  issues_medium: number;
  issues_low: number;
  reviewer: string;
  notes: string;
}

export interface ToolReviewSubmit {
  tool_name: string;
  sprint_date: string;
  score_correto: number;
  score_completo: number;
  score_qualidade: number;
  deliverables_done?: number;
  deliverables_total?: number;
  issues_critical?: number;
  issues_medium?: number;
  issues_low?: number;
  reviewer?: string;
  notes?: string;
}

export interface CostQualityEntry {
  model?: string;
  agent?: string;
  task_type?: string;
  total_cost: number;
  avg_quality: number;
  total_requests: number;
  cost_per_quality_point: number;
}

export interface CostQualityAnalysis {
  by_model: CostQualityEntry[];
  by_agent: CostQualityEntry[];
  by_task_type: CostQualityEntry[];
}

export interface DailyAggregate {
  date: string;
  dimension_type: string;
  dimension_value: string;
  total_requests: number;
  total_cost_usd: number;
  avg_quality: number | null;
  avg_latency_ms: number;
  cache_hit_rate: number;
  failure_rate: number;
}

export interface HeatmapEntry {
  agent: string;
  task_type: string;
  avg_quality: number;
  request_count: number;
}

export interface KpiAnomaly {
  type: string;
  dimension: string;
  value: string;
  severity: string;
  recent_avg?: number;
  historical_avg?: number;
  drop_pct?: number;
  recent_avg_ms?: number;
  historical_avg_ms?: number;
  increase_pct?: number;
}

export interface ModelRecommendation {
  model: string;
  avg_quality: number;
  total_cost: number;
  total_requests: number;
  cost_per_quality_point: number;
  reason: string;
}
