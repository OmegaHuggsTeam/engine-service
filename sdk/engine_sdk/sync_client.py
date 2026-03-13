"""Synchronous wrapper around :class:`EngineClient`.

Provides the same API surface as the async client but uses
``asyncio.run()`` under the hood for each call. Ideal for scripts,
notebooks, and environments where ``async/await`` is not available.

Example::

    from engine_sdk import EngineSyncClient

    client = EngineSyncClient(base_url="http://localhost:8766")
    results = client.rag.search("revenue Q4")
    client.close()
"""

from __future__ import annotations

import asyncio
from typing import Any

from .client import EngineClient


def _run(coro: Any) -> Any:
    """Run a coroutine synchronously.

    Uses the existing event loop if one is running (e.g. Jupyter),
    otherwise creates a new one via ``asyncio.run()``.
    """
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None

    if loop and loop.is_running():
        # We're inside an already-running loop (e.g. Jupyter).
        # Use nest_asyncio if available, otherwise create a new thread.
        import concurrent.futures

        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            return pool.submit(asyncio.run, coro).result()
    else:
        return asyncio.run(coro)


class _SyncRAGResource:
    """Sync wrapper for RAGResource."""

    def __init__(self, async_resource: Any) -> None:
        self._async = async_resource

    def search(self, query: str, *, top_k: int = 5) -> list:
        """Hybrid RAG search.

        Args:
            query: Natural-language search query.
            top_k: Maximum results (default 5, max 50).

        Returns:
            List of :class:`RAGResult` objects.

        Example::

            results = client.rag.search("customer churn")
        """
        return _run(self._async.search(query, top_k=top_k))

    def search_by_category(
        self, query: str, category: str, *, top_k: int = 5
    ) -> list:
        """Search within a specific document category.

        Args:
            query: Search query.
            category: Document category.
            top_k: Maximum results.

        Returns:
            List of :class:`RAGResult` objects.

        Example::

            results = client.rag.search_by_category("metrics", "reports")
        """
        return _run(
            self._async.search_by_category(query, category, top_k=top_k)
        )


class _SyncAgentsResource:
    """Sync wrapper for AgentsResource."""

    def __init__(self, async_resource: Any) -> None:
        self._async = async_resource

    def list(self) -> list:
        """List all registered agents.

        Returns:
            List of :class:`AgentInfo` objects.

        Example::

            agents = client.agents.list()
        """
        return _run(self._async.list())

    def get_history(self, agent_id: str, *, limit: int = 20) -> list:
        """Get task history for an agent.

        Args:
            agent_id: Agent identifier.
            limit: Maximum entries.

        Returns:
            List of task history records.
        """
        return _run(self._async.get_history(agent_id, limit=limit))

    def execute(
        self,
        agent_id: str,
        task: str,
        *,
        context: dict | None = None,
    ) -> Any:
        """Submit a task to the orchestrator.

        Args:
            agent_id: Preferred agent hint.
            task: Task description.
            context: Optional context.

        Returns:
            :class:`AgentResponse`.

        Example::

            resp = client.agents.execute("analyst", "summarize Q4")
        """
        return _run(self._async.execute(agent_id, task, context=context))

    def create(self, **kwargs: Any) -> Any:
        """Register a custom agent."""
        return _run(self._async.create(**kwargs))

    def update(self, agent_id: str, **kwargs: Any) -> Any:
        """Update an agent."""
        return _run(self._async.update(agent_id, **kwargs))

    def delete(self, agent_id: str) -> Any:
        """Soft-delete an agent."""
        return _run(self._async.delete(agent_id))

    def health(self) -> list:
        """Get agent health status.

        Returns:
            List of :class:`AgentInfo`.
        """
        return _run(self._async.health())


class _SyncGraphResource:
    """Sync wrapper for GraphResource."""

    def __init__(self, async_resource: Any) -> None:
        self._async = async_resource

    def explore(self, center: str, *, depth: int = 2) -> Any:
        """Explore a subgraph.

        Args:
            center: Center node ID.
            depth: Max hops (1-4).

        Returns:
            :class:`GraphSubset`.
        """
        return _run(self._async.explore(center, depth=depth))

    def services(self) -> list:
        """List graph services."""
        return _run(self._async.services())

    def concepts(self, *, limit: int = 50) -> list:
        """Get concept nodes."""
        return _run(self._async.concepts(limit=limit))

    def schema(self) -> dict:
        """Get graph schema."""
        return _run(self._async.schema())


class _SyncIngestResource:
    """Sync wrapper for IngestResource."""

    def __init__(self, async_resource: Any) -> None:
        self._async = async_resource

    def upload(self, file_path: str, *, category: str = "documents") -> Any:
        """Upload a file for ingestion.

        Args:
            file_path: Path to the file.
            category: Document category.

        Returns:
            :class:`IngestResult`.

        Example::

            result = client.ingest.upload("report.pdf")
        """
        return _run(self._async.upload(file_path, category=category))

    def status(self, task_id: str) -> dict:
        """Check ingestion status."""
        return _run(self._async.status(task_id))


class _SyncTelemetryResource:
    """Sync wrapper for TelemetryResource."""

    def __init__(self, async_resource: Any) -> None:
        self._async = async_resource

    def pipeline_stats(self) -> Any:
        """Get pipeline statistics.

        Returns:
            :class:`PipelineStats`.

        Example::

            stats = client.telemetry.pipeline_stats()
        """
        return _run(self._async.pipeline_stats())

    def cost_report(self) -> dict:
        """Get cost-quality analysis."""
        return _run(self._async.cost_report())

    def model_leaderboard(self) -> list:
        """Get model leaderboard."""
        return _run(self._async.model_leaderboard())

    def model_history(self, model_id: str, *, limit: int = 30) -> list:
        """Get model daily time series."""
        return _run(self._async.model_history(model_id, limit=limit))

    def tool_comparison(self) -> list:
        """Get tool comparison aggregates."""
        return _run(self._async.tool_comparison())

    def tool_history(self, tool_name: str, *, limit: int = 20) -> list:
        """Get tool sprint reviews."""
        return _run(self._async.tool_history(tool_name, limit=limit))

    def trends(self, *, dimension: str = "model", limit: int = 90) -> list:
        """Get daily aggregates by dimension."""
        return _run(self._async.trends(dimension=dimension, limit=limit))

    def agent_heatmap(self) -> list:
        """Get agent x task_type matrix."""
        return _run(self._async.agent_heatmap())

    def anomalies(self) -> list:
        """Detect regression alerts."""
        return _run(self._async.anomalies())

    def recommend_model(self) -> Any:
        """Get recommended model."""
        return _run(self._async.recommend_model())

    def cluster_health(self) -> Any:
        """Get cluster health check."""
        return _run(self._async.cluster_health())


class EngineSyncClient:
    """Synchronous client for the Engine Service Sovereign Gateway.

    Wraps :class:`EngineClient` with blocking calls. Each method
    internally calls ``asyncio.run()`` (or uses a thread pool when
    running inside an existing event loop like Jupyter).

    Args:
        base_url: Base URL (default ``http://localhost:8766``).
        api_key: Optional API key.
        timeout: Request timeout in seconds (default 30).

    Example::

        client = EngineSyncClient()
        agents = client.agents.list()
        client.close()
    """

    def __init__(
        self,
        base_url: str = "http://localhost:8766",
        *,
        api_key: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self._async_client = EngineClient(
            base_url=base_url, api_key=api_key, timeout=timeout
        )

        self._rag: _SyncRAGResource | None = None
        self._agents: _SyncAgentsResource | None = None
        self._graph: _SyncGraphResource | None = None
        self._ingest: _SyncIngestResource | None = None
        self._telemetry: _SyncTelemetryResource | None = None

    @property
    def rag(self) -> _SyncRAGResource:
        """RAG search resource (sync)."""
        if self._rag is None:
            self._rag = _SyncRAGResource(self._async_client.rag)
        return self._rag

    @property
    def agents(self) -> _SyncAgentsResource:
        """Agent management resource (sync)."""
        if self._agents is None:
            self._agents = _SyncAgentsResource(self._async_client.agents)
        return self._agents

    @property
    def graph(self) -> _SyncGraphResource:
        """Graph exploration resource (sync)."""
        if self._graph is None:
            self._graph = _SyncGraphResource(self._async_client.graph)
        return self._graph

    @property
    def ingest(self) -> _SyncIngestResource:
        """Document ingestion resource (sync)."""
        if self._ingest is None:
            self._ingest = _SyncIngestResource(self._async_client.ingest)
        return self._ingest

    @property
    def telemetry(self) -> _SyncTelemetryResource:
        """Telemetry resource (sync)."""
        if self._telemetry is None:
            self._telemetry = _SyncTelemetryResource(
                self._async_client.telemetry
            )
        return self._telemetry

    def close(self) -> None:
        """Close the underlying HTTP client."""
        _run(self._async_client.close())

    def __enter__(self) -> EngineSyncClient:
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()

    @property
    def base_url(self) -> str:
        """The base URL this client is connected to."""
        return self._async_client.base_url

    def __repr__(self) -> str:
        return f"EngineSyncClient(base_url={self._async_client.base_url!r})"
