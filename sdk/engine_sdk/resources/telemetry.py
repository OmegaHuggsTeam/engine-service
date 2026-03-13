"""Telemetry resource.

Wraps the ``/api/v1/pipeline/*`` and ``/api/v1/kpi/*`` endpoints for
monitoring pipeline performance, cost tracking, and KPI analytics.
"""

from __future__ import annotations

from typing import Any

from ..models import ClusterHealth, KpiRecommendation, PipelineStats
from ._base import BaseResource


class TelemetryResource(BaseResource):
    """Pipeline telemetry, KPI analytics, and cluster health.

    Example::

        async with EngineClient() as client:
            stats = await client.telemetry.pipeline_stats()
            print(f"Total requests: {stats.total_requests}")
    """

    # -- Pipeline -----------------------------------------------------------

    async def pipeline_stats(self) -> PipelineStats:
        """Get aggregate pipeline statistics (requests, latency, costs).

        Returns:
            :class:`PipelineStats` with current metrics.

        Example::

            stats = await client.telemetry.pipeline_stats()
            print(f"Cache hit rate: {stats.cache_hit_rate}%")
        """
        data = await self._get("/api/v1/pipeline/stats")
        if isinstance(data, dict):
            return PipelineStats.model_validate(data)
        return PipelineStats()

    # -- Cost ---------------------------------------------------------------

    async def cost_report(self) -> dict[str, Any]:
        """Get cost-quality analysis across models, agents, and task types.

        Returns:
            Dict with ``by_model``, ``by_agent``, ``by_task_type`` breakdowns.

        Example::

            report = await client.telemetry.cost_report()
            for model in report.get("by_model", []):
                print(model)
        """
        data = await self._get("/api/v1/kpi/cost-quality")
        return data if isinstance(data, dict) else {}

    # -- KPI ---------------------------------------------------------------

    async def model_leaderboard(self) -> list[dict[str, Any]]:
        """Get model leaderboard ranked by cost-effectiveness.

        Returns:
            List of model performance dicts.

        Example::

            models = await client.telemetry.model_leaderboard()
            for m in models:
                print(m)
        """
        data = await self._get("/api/v1/kpi/models")
        return data if isinstance(data, list) else []

    async def model_history(
        self,
        model_id: str,
        *,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        """Get daily time series for a specific model.

        Args:
            model_id: Model identifier.
            limit: Maximum number of days (default 30, max 365).

        Returns:
            List of daily metric dicts.

        Example::

            history = await client.telemetry.model_history("claude-3-haiku")
        """
        data = await self._get(
            f"/api/v1/kpi/models/{model_id}/history",
            params={"limit": limit},
        )
        return data if isinstance(data, list) else []

    async def tool_comparison(self) -> list[dict[str, Any]]:
        """Get tool comparison aggregates.

        Returns:
            List of tool performance dicts.

        Example::

            tools = await client.telemetry.tool_comparison()
        """
        data = await self._get("/api/v1/kpi/tools")
        return data if isinstance(data, list) else []

    async def tool_history(
        self,
        tool_name: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get sprint-by-sprint reviews for a tool.

        Args:
            tool_name: Tool identifier.
            limit: Maximum entries (default 20, max 100).

        Returns:
            List of review dicts.

        Example::

            history = await client.telemetry.tool_history("claude_code")
        """
        data = await self._get(
            f"/api/v1/kpi/tools/{tool_name}/history",
            params={"limit": limit},
        )
        return data if isinstance(data, list) else []

    async def trends(
        self,
        *,
        dimension: str = "model",
        limit: int = 90,
    ) -> list[dict[str, Any]]:
        """Get daily aggregates by dimension.

        Args:
            dimension: Grouping dimension (``"model"``, ``"agent"``, ``"task_type"``).
            limit: Maximum days (default 90, max 365).

        Returns:
            List of daily aggregate dicts.

        Example::

            trends = await client.telemetry.trends(dimension="agent", limit=30)
        """
        data = await self._get(
            "/api/v1/kpi/trends",
            params={"dimension": dimension, "limit": limit},
        )
        return data if isinstance(data, list) else []

    async def agent_heatmap(self) -> list[dict[str, Any]]:
        """Get agent x task_type quality matrix.

        Returns:
            List of heatmap cell dicts.

        Example::

            heatmap = await client.telemetry.agent_heatmap()
        """
        data = await self._get("/api/v1/kpi/agents/heatmap")
        return data if isinstance(data, list) else []

    async def anomalies(self) -> list[dict[str, Any]]:
        """Detect regression alerts from metrics time series.

        Returns:
            List of anomaly dicts.

        Example::

            anomalies = await client.telemetry.anomalies()
            for a in anomalies:
                print(a)
        """
        data = await self._get("/api/v1/kpi/anomalies")
        return data if isinstance(data, list) else []

    async def recommend_model(self) -> KpiRecommendation:
        """Get the recommended model based on cost-quality analysis.

        Returns:
            :class:`KpiRecommendation` with the best model choice.

        Example::

            rec = await client.telemetry.recommend_model()
            print(f"Recommended: {rec.model} ({rec.reason})")
        """
        data = await self._get("/api/v1/kpi/recommend")
        if isinstance(data, dict):
            return KpiRecommendation.model_validate(data)
        return KpiRecommendation()

    # -- Cluster ------------------------------------------------------------

    async def cluster_health(self) -> ClusterHealth:
        """Get cluster health check (ChromaDB, Neo4j, Evidence, n8n, Tailscale).

        Returns:
            :class:`ClusterHealth` with service statuses.

        Example::

            health = await client.telemetry.cluster_health()
            print(f"OK: {health.summary.get('ok', 0)}/{health.summary.get('total', 0)}")
        """
        data = await self._get("/api/v1/cluster/health")
        if isinstance(data, dict):
            return ClusterHealth.model_validate(data)
        return ClusterHealth()
