"""
ModelBenchmark — Per-model performance tracking for KPI Intelligence.

Buffers LLM call metrics and flushes to Neo4j :ModelMetric daily buckets.
Provides leaderboard query ranked by cost-per-quality-point.
"""

import logging
import statistics
import threading
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ModelCallRecord:
    """Single LLM call observation."""
    model: str
    latency_ms: float
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    quality_score: float | None = None
    success: bool = True
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


# Approximate cost per 1M tokens (Groq pricing)
_COST_PER_M_TOKENS = {
    "llama-3.1-8b-instant": 0.05,
    "llama-3.3-70b-versatile": 0.59,
    "default": 0.30,
}


def _estimate_cost(model: str, tokens: int) -> float:
    rate = _COST_PER_M_TOKENS.get(model, _COST_PER_M_TOKENS["default"])
    return tokens * rate / 1_000_000


class ModelBenchmark:
    """
    Buffers per-model call records, computes daily aggregates,
    and flushes to Neo4j :ModelMetric nodes.
    """

    def __init__(self, graph_manager=None, flush_threshold: int = 50):
        self._graph = graph_manager
        self._buffer: list[ModelCallRecord] = []
        self._lock = threading.Lock()
        self._flush_threshold = flush_threshold

    def record(self, record: ModelCallRecord) -> None:
        """Add a call record to the buffer."""
        with self._lock:
            self._buffer.append(record)
            if len(self._buffer) >= self._flush_threshold:
                self._flush_locked()

    def record_from_profile(self, profile: Any) -> None:
        """Extract per-call latencies from a RequestCostProfile and record them."""
        latencies = getattr(profile, "per_call_latencies", [])
        if not latencies:
            # Fallback: single record from aggregate profile data
            models = getattr(profile, "model_tiers_used", [])
            if models:
                model = models[0]
                record = ModelCallRecord(
                    model=model,
                    latency_ms=getattr(profile, "elapsed_ms", 0.0),
                    input_tokens=getattr(profile, "total_input_tokens", 0),
                    output_tokens=getattr(profile, "total_output_tokens", 0),
                    cost_usd=getattr(profile, "estimated_cost_usd", 0.0),
                )
                self.record(record)
            return

        for model, latency_ms in latencies:
            record = ModelCallRecord(
                model=model,
                latency_ms=latency_ms,
                cost_usd=_estimate_cost(model, 0),
            )
            self.record(record)

    def flush(self) -> int:
        """Flush buffer to Neo4j. Returns count of flushed records."""
        with self._lock:
            return self._flush_locked()

    def _flush_locked(self) -> int:
        """Flush while lock is held."""
        if not self._buffer:
            return 0

        records = list(self._buffer)
        self._buffer.clear()

        if not self._graph:
            logger.debug("ModelBenchmark: no graph, discarding %d records", len(records))
            return 0

        # Group by (model, date)
        buckets: dict[tuple[str, str], list[ModelCallRecord]] = {}
        for r in records:
            day = r.timestamp[:10] if r.timestamp else date.today().isoformat()
            key = (r.model, day)
            buckets.setdefault(key, []).append(r)

        flushed = 0
        for (model_id, day), calls in buckets.items():
            params = self._aggregate_bucket(model_id, day, calls)
            try:
                from ..graph import queries as q
                self._graph.execute_write(q.UPSERT_MODEL_METRIC, params)
                flushed += len(calls)
            except Exception as e:
                logger.warning("ModelBenchmark flush failed for %s/%s: %s", model_id, day, e)

        return flushed

    @staticmethod
    def _aggregate_bucket(model_id: str, day: str, calls: list[ModelCallRecord]) -> dict:
        """Compute aggregate params for a (model, day) bucket."""
        latencies = [c.latency_ms for c in calls if c.latency_ms > 0]
        qualities = [c.quality_score for c in calls if c.quality_score is not None]
        failures = sum(1 for c in calls if not c.success)

        return {
            "id": f"mm_{model_id}_{day}",
            "model_id": model_id,
            "date": day,
            "requests_delta": len(calls),
            "tokens_in_delta": sum(c.input_tokens for c in calls),
            "tokens_out_delta": sum(c.output_tokens for c in calls),
            "cost_delta": sum(c.cost_usd for c in calls),
            "failure_delta": failures,
            "avg_quality_score": statistics.mean(qualities) if qualities else None,
            "avg_latency_ms": statistics.mean(latencies) if latencies else 0.0,
            "p50_latency_ms": statistics.median(latencies) if latencies else 0.0,
            "p95_latency_ms": (
                sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) >= 2 else (latencies[0] if latencies else 0.0)
            ),
        }

    def get_leaderboard(self) -> list[dict]:
        """Query Neo4j for model leaderboard ranked by cost-effectiveness."""
        if not self._graph:
            return []
        try:
            from ..graph import queries as q
            return self._graph.execute_read(q.GET_MODEL_METRICS_LEADERBOARD)
        except Exception as e:
            logger.warning("ModelBenchmark.get_leaderboard failed: %s", e)
            return []

    def get_model_history(self, model_id: str, limit: int = 30) -> list[dict]:
        """Query daily history for a specific model."""
        if not self._graph:
            return []
        try:
            from ..graph import queries as q
            return self._graph.execute_read(
                q.GET_MODEL_METRIC_HISTORY, {"model_id": model_id, "limit": limit}
            )
        except Exception as e:
            logger.warning("ModelBenchmark.get_model_history failed: %s", e)
            return []

    @property
    def buffer_size(self) -> int:
        with self._lock:
            return len(self._buffer)
