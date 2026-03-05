"""
CostTracker - Per-request cost profiling for the optimization pipeline.

Tracks LLM calls, token usage, cache hits, model tiers, and layer reached
for each request through the NeuralLinkOrchestrator.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# Approximate cost per 1M tokens (Groq pricing)
_COST_PER_M_TOKENS = {
    "llama-3.1-8b-instant": 0.05,
    "llama-3.3-70b-versatile": 0.59,
    "default": 0.30,
}


@dataclass
class RequestCostProfile:
    """Tracks cost metrics for a single orchestrator request."""

    session_id: str = ""
    started_at: float = 0.0
    ended_at: float = 0.0

    # LLM usage
    llm_calls: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    model_tiers_used: list[str] = field(default_factory=list)

    # Layer tracking
    layers_reached: int = 0  # 0=cache, 1=triage, 2=context, 3=llm, 4=eval
    decision_layer: int = -1  # DecisionTree.classify() advisory layer (-1 = not set)
    cache_hit: bool = False
    graph_shortcut: bool = False
    triage_resolved: bool = False
    evaluation_skipped: bool = False

    # Context metrics
    context_tokens_injected: int = 0
    rag_results_filtered: int = 0  # Results below threshold

    # Per-call latencies (for ModelBenchmark aggregation)
    per_call_latencies: list[tuple[str, float]] = field(default_factory=list)  # [(model, ms), ...]

    @property
    def total_tokens(self) -> int:
        return self.total_input_tokens + self.total_output_tokens

    @property
    def elapsed_ms(self) -> float:
        if self.ended_at and self.started_at:
            return (self.ended_at - self.started_at) * 1000
        return 0.0

    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on models used and token counts."""
        if not self.model_tiers_used:
            rate = _COST_PER_M_TOKENS["default"]
            return self.total_tokens * rate / 1_000_000

        # Use average rate of models used
        rates = []
        for model in self.model_tiers_used:
            rates.append(_COST_PER_M_TOKENS.get(model, _COST_PER_M_TOKENS["default"]))
        avg_rate = sum(rates) / len(rates) if rates else _COST_PER_M_TOKENS["default"]
        return self.total_tokens * avg_rate / 1_000_000

    def record_llm_call(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
    ) -> None:
        """Record an LLM call."""
        self.llm_calls += 1
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        self.model_tiers_used.append(model)

    def record_llm_call_with_latency(
        self,
        model: str,
        input_tokens: int = 0,
        output_tokens: int = 0,
        latency_ms: float = 0.0,
    ) -> None:
        """Record an LLM call with latency tracking."""
        self.record_llm_call(model, input_tokens, output_tokens)
        if latency_ms > 0:
            self.per_call_latencies.append((model, latency_ms))

    def to_dict(self) -> dict:
        """Serialize for logging/Neo4j persistence."""
        return {
            "session_id": self.session_id,
            "llm_calls": self.llm_calls,
            "total_tokens": self.total_tokens,
            "estimated_cost_usd": round(self.estimated_cost_usd, 6),
            "elapsed_ms": round(self.elapsed_ms, 1),
            "layers_reached": self.layers_reached,
            "decision_layer": self.decision_layer,
            "cache_hit": self.cache_hit,
            "graph_shortcut": self.graph_shortcut,
            "triage_resolved": self.triage_resolved,
            "evaluation_skipped": self.evaluation_skipped,
            "context_tokens_injected": self.context_tokens_injected,
            "rag_results_filtered": self.rag_results_filtered,
            "models_used": list(set(self.model_tiers_used)),
        }

    def to_request_metric_params(self, task_type: str = "unknown", agent_used: str = "", quality_score: float | None = None) -> dict:
        """Build params dict for UPSERT_REQUEST_METRIC query."""
        import uuid
        from datetime import datetime
        primary_model = self.model_tiers_used[0] if self.model_tiers_used else "unknown"
        return {
            "id": f"rm_{uuid.uuid4().hex[:12]}",
            "session_id": self.session_id,
            "model_used": primary_model,
            "task_type": task_type,
            "agent_used": agent_used,
            "input_tokens": self.total_input_tokens,
            "output_tokens": self.total_output_tokens,
            "cost_usd": round(self.estimated_cost_usd, 8),
            "latency_ms": round(self.elapsed_ms, 1),
            "quality_score": quality_score,
            "layer_reached": self.layers_reached,
            "cache_hit": self.cache_hit,
            "evaluation_skipped": self.evaluation_skipped,
            "created_at": datetime.now().isoformat(),
        }

    def summary(self) -> str:
        """Human-readable summary line."""
        resolution = "cache" if self.cache_hit else (
            "graph" if self.graph_shortcut else (
                "triage" if self.triage_resolved else f"layer_{self.layers_reached}"
            )
        )
        dec = f" dec={self.decision_layer}" if self.decision_layer >= 0 else ""
        return (
            f"[Cost] {resolution}{dec} | "
            f"{self.llm_calls} calls | "
            f"{self.total_tokens} tokens | "
            f"${self.estimated_cost_usd:.5f} | "
            f"{self.elapsed_ms:.0f}ms"
        )


class CostTracker:
    """Aggregates cost profiles across requests."""

    def __init__(self):
        self._profiles: list[RequestCostProfile] = []
        self._max_history = 1000

    def start_request(self, session_id: str = "") -> RequestCostProfile:
        """Create a new cost profile for a request."""
        profile = RequestCostProfile(
            session_id=session_id,
            started_at=time.time(),
        )
        return profile

    def finish_request(self, profile: RequestCostProfile) -> None:
        """Finalize and store a request profile."""
        profile.ended_at = time.time()
        self._profiles.append(profile)
        logger.info(profile.summary())
        # Evict old profiles
        if len(self._profiles) > self._max_history:
            self._profiles = self._profiles[-self._max_history:]

    @property
    def stats(self) -> dict:
        """Aggregate stats across all tracked requests."""
        if not self._profiles:
            return {"total_requests": 0}

        total = len(self._profiles)
        cache_hits = sum(1 for p in self._profiles if p.cache_hit)
        graph_hits = sum(1 for p in self._profiles if p.graph_shortcut)
        total_tokens = sum(p.total_tokens for p in self._profiles)
        total_cost = sum(p.estimated_cost_usd for p in self._profiles)
        total_calls = sum(p.llm_calls for p in self._profiles)
        eval_skipped = sum(1 for p in self._profiles if p.evaluation_skipped)

        return {
            "total_requests": total,
            "cache_hit_rate": round(cache_hits / total, 3),
            "graph_shortcut_rate": round(graph_hits / total, 3),
            "avg_tokens_per_request": round(total_tokens / total),
            "avg_cost_per_request": round(total_cost / total, 6),
            "avg_llm_calls_per_request": round(total_calls / total, 2),
            "evaluation_skip_rate": round(eval_skipped / total, 3),
            "total_cost_usd": round(total_cost, 4),
        }
