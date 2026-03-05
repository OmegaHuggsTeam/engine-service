"""
CostQualityAnalyzer — $/quality-point analysis for KPI Intelligence.

Reads :RequestMetric and :ModelMetric nodes to compute cost-effectiveness
per model, agent, and task_type. Recommends the cheapest model above
a quality threshold.
"""

import logging
from typing import Any

from src.neural_link.graph import queries as q

logger = logging.getLogger(__name__)


class CostQualityAnalyzer:
    """Analyzes cost-per-quality-point across models, agents, and task types."""

    def __init__(self, graph_manager=None):
        self._graph = graph_manager

    def get_by_model(self) -> list[dict]:
        """$/quality-point ranked by model."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(q.GET_COST_PER_QUALITY_BY_MODEL)
        except Exception as e:
            logger.warning("CostQualityAnalyzer.get_by_model failed: %s", e)
            return []

    def get_by_agent(self) -> list[dict]:
        """$/quality-point ranked by agent."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(q.GET_COST_PER_QUALITY_BY_AGENT)
        except Exception as e:
            logger.warning("CostQualityAnalyzer.get_by_agent failed: %s", e)
            return []

    def get_by_task_type(self) -> list[dict]:
        """$/quality-point ranked by task type."""
        if not self._graph:
            return []
        try:
            return self._graph.execute_read(q.GET_COST_PER_QUALITY_BY_TASK_TYPE)
        except Exception as e:
            logger.warning("CostQualityAnalyzer.get_by_task_type failed: %s", e)
            return []

    def get_combined(self) -> dict:
        """Full cost-quality analysis: by_model, by_agent, by_task_type."""
        return {
            "by_model": self.get_by_model(),
            "by_agent": self.get_by_agent(),
            "by_task_type": self.get_by_task_type(),
        }

    def recommend_model(
        self, task_type: str = "", min_quality: float = 7.0
    ) -> dict | None:
        """
        Recommend the cheapest model that meets the quality threshold.
        """
        candidates = self.get_by_model()
        if not candidates:
            return None

        qualified = [
            c for c in candidates
            if c.get("avg_quality") is not None and c["avg_quality"] >= min_quality
        ]

        if not qualified:
            return None

        qualified.sort(key=lambda c: c.get("cost_per_quality_point", float("inf")))
        best = qualified[0]
        return {
            "model": best.get("model", best.get("model_id", "")),
            "avg_quality": best.get("avg_quality", 0),
            "total_cost": best.get("total_cost", 0),
            "total_requests": best.get("total_requests", 0),
            "cost_per_quality_point": best.get("cost_per_quality_point", 0),
            "reason": f"Cheapest model with avg quality >= {min_quality}",
        }

    def compute_from_profiles(self, profiles: list[Any]) -> dict:
        """
        Compute cost-quality analysis from in-memory RequestCostProfile objects.
        Useful when Neo4j is unavailable.
        """
        if not profiles:
            return {"by_model": [], "by_agent": [], "summary": {}}

        model_data: dict[str, list] = {}
        for p in profiles:
            models = getattr(p, "model_tiers_used", [])
            model = models[0] if models else "unknown"
            model_data.setdefault(model, []).append(p)

        by_model = []
        for model, profs in model_data.items():
            total_cost = sum(getattr(p, "estimated_cost_usd", 0) for p in profs)
            by_model.append({
                "model": model,
                "total_requests": len(profs),
                "total_cost": round(total_cost, 6),
                "total_tokens": sum(getattr(p, "total_tokens", 0) for p in profs),
                "avg_cost_per_request": round(total_cost / len(profs), 8) if profs else 0,
            })

        by_model.sort(key=lambda x: x["avg_cost_per_request"])

        return {
            "by_model": by_model,
            "by_agent": [],
            "summary": {
                "total_profiles": len(profiles),
                "total_cost": round(sum(getattr(p, "estimated_cost_usd", 0) for p in profiles), 6),
                "models_seen": len(model_data),
            },
        }
