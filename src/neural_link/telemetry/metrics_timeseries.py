"""
MetricsTimeSeries — Time-series persistence and aggregation for KPI Intelligence.

Flushes CostTracker RequestCostProfile objects to :RequestMetric nodes.
Aggregates daily into :DailyAggregate nodes by model, agent, and task_type.
Detects regressions (quality drops >20%, failure rate rises >50%).
"""

import logging
import threading
from collections import defaultdict
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


class MetricsTimeSeries:
    """
    Buffer-based time-series persistence.
    Accepts RequestCostProfile objects, flushes to Neo4j :RequestMetric,
    and periodically rolls up into :DailyAggregate.
    """

    def __init__(self, graph_manager=None, flush_threshold: int = 20):
        self._graph = graph_manager
        self._buffer: list[dict] = []  # list of request_metric_params dicts
        self._lock = threading.Lock()
        self._flush_threshold = flush_threshold

    def enqueue(self, profile: Any, task_type: str = "unknown", agent_used: str = "", quality_score: float | None = None) -> None:
        """
        Convert a RequestCostProfile to metric params and buffer it.
        Auto-flushes when threshold is reached.
        """
        if not hasattr(profile, "to_request_metric_params"):
            logger.debug("MetricsTimeSeries: profile missing to_request_metric_params")
            return

        params = profile.to_request_metric_params(
            task_type=task_type,
            agent_used=agent_used,
            quality_score=quality_score,
        )

        with self._lock:
            self._buffer.append(params)
            if len(self._buffer) >= self._flush_threshold:
                self._flush_locked()

    def flush(self) -> int:
        """Flush buffered metrics to Neo4j. Returns count flushed."""
        with self._lock:
            return self._flush_locked()

    def _flush_locked(self) -> int:
        """Flush while lock is held."""
        if not self._buffer:
            return 0

        records = list(self._buffer)
        self._buffer.clear()

        if not self._graph:
            logger.debug("MetricsTimeSeries: no graph, discarding %d records", len(records))
            return 0

        flushed = 0
        for params in records:
            try:
                from ..graph import queries as q
                self._graph.execute_write(q.UPSERT_REQUEST_METRIC, params)
                flushed += 1
            except Exception as e:
                logger.warning("MetricsTimeSeries flush failed: %s", e)

        return flushed

    def aggregate_daily(self, target_date: str | None = None) -> int:
        """
        Roll up :RequestMetric data into :DailyAggregate by model, agent, task_type.
        Returns number of aggregates created/updated.
        """
        if not self._graph:
            return 0

        day = target_date or date.today().isoformat()

        try:
            from ..graph import queries as q
            # Read all request metrics for the day
            rows = self._graph.execute_read(q.GET_REQUEST_METRICS_BY_DATE, {
                "start_date": f"{day}T00:00:00",
                "end_date": f"{day}T23:59:59",
                "limit": 10000,
            })
        except Exception as e:
            logger.warning("MetricsTimeSeries.aggregate_daily read failed: %s", e)
            return 0

        if not rows:
            return 0

        count = 0
        # Aggregate by each dimension
        for dim_type, dim_key in [("model", "model_used"), ("agent", "agent_used"), ("task_type", "task_type")]:
            buckets: dict[str, list[dict]] = defaultdict(list)
            for row in rows:
                val = row.get(dim_key)
                if val:
                    buckets[val].append(row)

            for dim_value, bucket_rows in buckets.items():
                agg = self._compute_aggregate(day, dim_type, dim_value, bucket_rows)
                try:
                    from ..graph import queries as q
                    self._graph.execute_write(q.UPSERT_DAILY_AGGREGATE, agg)
                    count += 1
                except Exception as e:
                    logger.warning("Aggregate write failed for %s/%s: %s", dim_type, dim_value, e)

        return count

    @staticmethod
    def _compute_aggregate(day: str, dim_type: str, dim_value: str, rows: list[dict]) -> dict:
        """Compute a single DailyAggregate from request metric rows."""
        total = len(rows)
        total_cost = sum(r.get("cost_usd", 0) or 0 for r in rows)
        qualities = [r["quality_score"] for r in rows if r.get("quality_score") is not None]
        latencies = [r["latency_ms"] for r in rows if r.get("latency_ms") is not None and r["latency_ms"] > 0]
        cache_hits = sum(1 for r in rows if r.get("cache_hit"))

        return {
            "id": f"da_{dim_type}_{dim_value}_{day}",
            "date": day,
            "dimension_type": dim_type,
            "dimension_value": dim_value,
            "total_requests": total,
            "total_cost_usd": round(total_cost, 8),
            "avg_quality": round(sum(qualities) / len(qualities), 2) if qualities else None,
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else 0.0,
            "cache_hit_rate": round(cache_hits / total, 3) if total else 0.0,
            "failure_rate": 0.0,  # Failures tracked separately in ModelBenchmark
        }

    def get_trends(self, dimension_type: str = "model", limit: int = 90) -> list[dict]:
        """Get daily aggregate trends for a dimension type."""
        if not self._graph:
            return []
        try:
            from ..graph import queries as q
            return self._graph.execute_read(
                q.GET_DAILY_AGGREGATES, {"dimension_type": dimension_type, "limit": limit}
            )
        except Exception as e:
            logger.warning("MetricsTimeSeries.get_trends failed: %s", e)
            return []

    def get_value_trends(self, dimension_type: str, dimension_value: str, limit: int = 30) -> list[dict]:
        """Get daily trends for a specific dimension value."""
        if not self._graph:
            return []
        try:
            from ..graph import queries as q
            return self._graph.execute_read(
                q.GET_DAILY_AGGREGATES_BY_VALUE,
                {"dimension_type": dimension_type, "dimension_value": dimension_value, "limit": limit},
            )
        except Exception as e:
            logger.warning("MetricsTimeSeries.get_value_trends failed: %s", e)
            return []

    def detect_anomalies(self, window_days: int = 7) -> list[dict]:
        """
        Detect regressions by comparing recent aggregates to historical baseline.
        Flags: quality drops >20%, latency increases >50%.
        """
        if not self._graph:
            return []

        anomalies = []
        try:
            from ..graph import queries as q
            # Get recent and historical aggregates for models
            rows = self._graph.execute_read(
                q.GET_DAILY_AGGREGATES, {"dimension_type": "model", "limit": window_days * 10}
            )
        except Exception as e:
            logger.warning("MetricsTimeSeries.detect_anomalies failed: %s", e)
            return []

        if not rows:
            return []

        # Group by dimension_value
        by_value: dict[str, list[dict]] = defaultdict(list)
        for row in rows:
            by_value[row.get("dimension_value", "")].append(row)

        for dim_val, value_rows in by_value.items():
            if len(value_rows) < 2:
                continue

            # Sort by date desc
            sorted_rows = sorted(value_rows, key=lambda r: r.get("date", ""), reverse=True)
            recent = sorted_rows[:window_days]
            historical = sorted_rows[window_days:]

            if not historical:
                continue

            # Quality regression
            recent_quality = [r["avg_quality"] for r in recent if r.get("avg_quality") is not None]
            hist_quality = [r["avg_quality"] for r in historical if r.get("avg_quality") is not None]

            if recent_quality and hist_quality:
                avg_recent = sum(recent_quality) / len(recent_quality)
                avg_hist = sum(hist_quality) / len(hist_quality)
                if avg_hist > 0 and (avg_hist - avg_recent) / avg_hist > 0.20:
                    anomalies.append({
                        "type": "quality_regression",
                        "dimension": "model",
                        "value": dim_val,
                        "recent_avg": round(avg_recent, 2),
                        "historical_avg": round(avg_hist, 2),
                        "drop_pct": round((avg_hist - avg_recent) / avg_hist * 100, 1),
                        "severity": "high",
                    })

            # Latency regression
            recent_lat = [r["avg_latency_ms"] for r in recent if r.get("avg_latency_ms") is not None and r["avg_latency_ms"] > 0]
            hist_lat = [r["avg_latency_ms"] for r in historical if r.get("avg_latency_ms") is not None and r["avg_latency_ms"] > 0]

            if recent_lat and hist_lat:
                avg_recent_lat = sum(recent_lat) / len(recent_lat)
                avg_hist_lat = sum(hist_lat) / len(hist_lat)
                if avg_hist_lat > 0 and (avg_recent_lat - avg_hist_lat) / avg_hist_lat > 0.50:
                    anomalies.append({
                        "type": "latency_regression",
                        "dimension": "model",
                        "value": dim_val,
                        "recent_avg_ms": round(avg_recent_lat, 1),
                        "historical_avg_ms": round(avg_hist_lat, 1),
                        "increase_pct": round((avg_recent_lat - avg_hist_lat) / avg_hist_lat * 100, 1),
                        "severity": "medium",
                    })

        return anomalies

    @property
    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)
