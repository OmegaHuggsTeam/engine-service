"""
KPI Intelligence — Neo4j Cypher queries for ModelMetric, ToolReview, RequestMetric, DailyAggregate.

Extracted from src/neural_link/graph/queries.py for migration to separate repo.
"""

# -- CRUD: ModelMetric
UPSERT_MODEL_METRIC = """
MERGE (mm:ModelMetric {id: $id})
SET mm.model_id = $model_id,
    mm.date = $date,
    mm.total_requests = coalesce(mm.total_requests, 0) + $requests_delta,
    mm.total_tokens_in = coalesce(mm.total_tokens_in, 0) + $tokens_in_delta,
    mm.total_tokens_out = coalesce(mm.total_tokens_out, 0) + $tokens_out_delta,
    mm.total_cost_usd = coalesce(mm.total_cost_usd, 0.0) + $cost_delta,
    mm.failure_count = coalesce(mm.failure_count, 0) + $failure_delta,
    mm.avg_quality_score = $avg_quality_score,
    mm.avg_latency_ms = $avg_latency_ms,
    mm.p50_latency_ms = $p50_latency_ms,
    mm.p95_latency_ms = $p95_latency_ms,
    mm.updated_at = datetime()
RETURN mm
"""

GET_MODEL_METRICS_LEADERBOARD = """
MATCH (mm:ModelMetric)
WITH mm.model_id AS model_id,
     sum(mm.total_requests) AS total_requests,
     sum(mm.total_tokens_in) + sum(mm.total_tokens_out) AS total_tokens,
     sum(mm.total_cost_usd) AS total_cost,
     avg(mm.avg_quality_score) AS avg_quality,
     avg(mm.avg_latency_ms) AS avg_latency,
     sum(mm.failure_count) AS failures
RETURN model_id, total_requests, total_tokens, total_cost, avg_quality,
       avg_latency, failures,
       CASE WHEN avg_quality > 0 THEN total_cost / avg_quality ELSE 999.0 END AS cost_per_quality
ORDER BY cost_per_quality ASC
"""

GET_MODEL_METRIC_HISTORY = """
MATCH (mm:ModelMetric {model_id: $model_id})
RETURN mm.date AS date, mm.total_requests AS total_requests,
       mm.total_tokens_in AS tokens_in, mm.total_tokens_out AS tokens_out,
       mm.total_cost_usd AS cost_usd, mm.avg_quality_score AS avg_quality,
       mm.avg_latency_ms AS avg_latency, mm.failure_count AS failures
ORDER BY mm.date DESC
LIMIT $limit
"""

# -- CRUD: ToolReview
UPSERT_TOOL_REVIEW = """
MERGE (tr:ToolReview {id: $id})
SET tr.tool_name = $tool_name,
    tr.sprint_date = $sprint_date,
    tr.score_correto = $score_correto,
    tr.score_completo = $score_completo,
    tr.score_qualidade = $score_qualidade,
    tr.nota_geral = $nota_geral,
    tr.deliverables_done = $deliverables_done,
    tr.deliverables_total = $deliverables_total,
    tr.issues_critical = $issues_critical,
    tr.issues_medium = $issues_medium,
    tr.issues_low = $issues_low,
    tr.reviewer = $reviewer,
    tr.notes = $notes,
    tr.created_at = coalesce(tr.created_at, datetime())
RETURN tr
"""

GET_TOOL_REVIEWS = """
MATCH (tr:ToolReview)
RETURN tr.id AS id, tr.tool_name AS tool_name, tr.sprint_date AS sprint_date,
       tr.score_correto AS score_correto, tr.score_completo AS score_completo,
       tr.score_qualidade AS score_qualidade, tr.nota_geral AS nota_geral,
       tr.deliverables_done AS deliverables_done, tr.deliverables_total AS deliverables_total,
       tr.issues_critical AS issues_critical, tr.issues_medium AS issues_medium,
       tr.issues_low AS issues_low, tr.reviewer AS reviewer, tr.notes AS notes
ORDER BY tr.sprint_date DESC
LIMIT $limit
"""

GET_TOOL_REVIEW_HISTORY = """
MATCH (tr:ToolReview {tool_name: $tool_name})
RETURN tr.id AS id, tr.sprint_date AS sprint_date,
       tr.score_correto AS score_correto, tr.score_completo AS score_completo,
       tr.score_qualidade AS score_qualidade, tr.nota_geral AS nota_geral,
       tr.deliverables_done AS deliverables_done, tr.deliverables_total AS deliverables_total,
       tr.issues_critical AS issues_critical, tr.issues_medium AS issues_medium,
       tr.issues_low AS issues_low, tr.reviewer AS reviewer, tr.notes AS notes
ORDER BY tr.sprint_date DESC
LIMIT $limit
"""

GET_TOOL_COMPARISON = """
MATCH (tr:ToolReview)
WITH tr.tool_name AS tool_name,
     count(tr) AS review_count,
     avg(tr.nota_geral) AS avg_score,
     avg(tr.score_correto) AS avg_correto,
     avg(tr.score_completo) AS avg_completo,
     avg(tr.score_qualidade) AS avg_qualidade,
     sum(tr.deliverables_done) AS total_done,
     sum(tr.deliverables_total) AS total_planned,
     sum(tr.issues_critical) AS total_critical
RETURN tool_name, review_count, avg_score, avg_correto, avg_completo,
       avg_qualidade, total_done, total_planned, total_critical
ORDER BY avg_score DESC
"""

# -- CRUD: RequestMetric
UPSERT_REQUEST_METRIC = """
CREATE (rm:RequestMetric {id: $id})
SET rm.session_id = $session_id,
    rm.model_used = $model_used,
    rm.task_type = $task_type,
    rm.agent_used = $agent_used,
    rm.input_tokens = $input_tokens,
    rm.output_tokens = $output_tokens,
    rm.cost_usd = $cost_usd,
    rm.latency_ms = $latency_ms,
    rm.quality_score = $quality_score,
    rm.layer_reached = $layer_reached,
    rm.cache_hit = $cache_hit,
    rm.evaluation_skipped = $evaluation_skipped,
    rm.created_at = $created_at
RETURN rm
"""

GET_REQUEST_METRICS_BY_DATE = """
MATCH (rm:RequestMetric)
WHERE rm.created_at >= $start_date AND rm.created_at <= $end_date
RETURN rm.id AS id, rm.session_id AS session_id, rm.model_used AS model_used,
       rm.task_type AS task_type, rm.agent_used AS agent_used,
       rm.input_tokens AS input_tokens, rm.output_tokens AS output_tokens,
       rm.cost_usd AS cost_usd, rm.latency_ms AS latency_ms,
       rm.quality_score AS quality_score, rm.layer_reached AS layer_reached,
       rm.cache_hit AS cache_hit, rm.created_at AS created_at
ORDER BY rm.created_at DESC
LIMIT $limit
"""

# -- CRUD: DailyAggregate
UPSERT_DAILY_AGGREGATE = """
MERGE (da:DailyAggregate {id: $id})
SET da.date = $date,
    da.dimension_type = $dimension_type,
    da.dimension_value = $dimension_value,
    da.total_requests = $total_requests,
    da.total_cost_usd = $total_cost_usd,
    da.avg_quality = $avg_quality,
    da.avg_latency_ms = $avg_latency_ms,
    da.cache_hit_rate = $cache_hit_rate,
    da.failure_rate = $failure_rate,
    da.updated_at = datetime()
RETURN da
"""

GET_DAILY_AGGREGATES = """
MATCH (da:DailyAggregate)
WHERE da.dimension_type = $dimension_type
RETURN da.date AS date, da.dimension_type AS dimension_type,
       da.dimension_value AS dimension_value,
       da.total_requests AS total_requests, da.total_cost_usd AS total_cost_usd,
       da.avg_quality AS avg_quality, da.avg_latency_ms AS avg_latency_ms,
       da.cache_hit_rate AS cache_hit_rate, da.failure_rate AS failure_rate
ORDER BY da.date DESC
LIMIT $limit
"""

GET_DAILY_AGGREGATES_BY_VALUE = """
MATCH (da:DailyAggregate)
WHERE da.dimension_type = $dimension_type AND da.dimension_value = $dimension_value
RETURN da.date AS date, da.total_requests AS total_requests,
       da.total_cost_usd AS total_cost_usd, da.avg_quality AS avg_quality,
       da.avg_latency_ms AS avg_latency_ms, da.cache_hit_rate AS cache_hit_rate,
       da.failure_rate AS failure_rate
ORDER BY da.date DESC
LIMIT $limit
"""

# -- KPI Queries
GET_COST_PER_QUALITY_BY_MODEL = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
WITH rm.model_used AS model,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN model, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""

GET_COST_PER_QUALITY_BY_AGENT = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
  AND rm.agent_used IS NOT NULL
WITH rm.agent_used AS agent,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN agent, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""

GET_COST_PER_QUALITY_BY_TASK_TYPE = """
MATCH (rm:RequestMetric)
WHERE rm.quality_score IS NOT NULL AND rm.quality_score > 0
WITH rm.task_type AS task_type,
     sum(rm.cost_usd) AS total_cost,
     avg(rm.quality_score) AS avg_quality,
     count(rm) AS total_requests
RETURN task_type, total_cost, avg_quality, total_requests,
       total_cost / avg_quality AS cost_per_quality_point
ORDER BY cost_per_quality_point ASC
"""
