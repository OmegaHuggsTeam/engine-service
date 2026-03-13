"""Async client for the Engine Service Sovereign Gateway.

This is the primary entry point for the SDK. Use :class:`EngineClient`
to interact with all Engine Service capabilities: RAG search, agent
orchestration, graph exploration, document ingestion, and telemetry.

Example::

    from engine_sdk import EngineClient

    async with EngineClient(base_url="http://localhost:8766") as client:
        # Search
        results = await client.rag.search("revenue Q4")

        # Agents
        agents = await client.agents.list()

        # Telemetry
        stats = await client.telemetry.pipeline_stats()
"""

from __future__ import annotations

from typing import Any

import httpx

from .resources.agents import AgentsResource
from .resources.graph import GraphResource
from .resources.ingest import IngestResource
from .resources.rag import RAGResource
from .resources.telemetry import TelemetryResource


_DEFAULT_BASE_URL = "http://localhost:8766"
_DEFAULT_TIMEOUT = 30.0
_USER_AGENT = "engine-sdk-python/0.1.0"


class EngineClient:
    """Async client for the Engine Service Sovereign Gateway.

    Args:
        base_url: Base URL of the Engine Service (default ``http://localhost:8766``).
        api_key: Optional API key for authentication. Sent as
            ``Authorization: Bearer <key>`` header.
        timeout: Request timeout in seconds (default 30).
        httpx_client: Optional pre-configured :class:`httpx.AsyncClient`.
            When provided, ``base_url``, ``api_key``, and ``timeout``
            are ignored.

    Example::

        # Basic usage
        async with EngineClient() as client:
            results = await client.rag.search("hello world")

        # With API key
        client = EngineClient(
            base_url="https://api.huggs.tech",
            api_key="sk-...",
            timeout=60,
        )
    """

    def __init__(
        self,
        base_url: str = _DEFAULT_BASE_URL,
        *,
        api_key: str | None = None,
        timeout: float = _DEFAULT_TIMEOUT,
        httpx_client: httpx.AsyncClient | None = None,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._timeout = timeout
        self._owns_client = httpx_client is None

        if httpx_client is not None:
            self._client = httpx_client
        else:
            headers: dict[str, str] = {
                "User-Agent": _USER_AGENT,
                "Accept": "application/json",
            }
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            self._client = httpx.AsyncClient(
                base_url=self._base_url,
                timeout=httpx.Timeout(timeout),
                headers=headers,
            )

        # Resource namespaces (lazy-ish, but created once)
        self._rag: RAGResource | None = None
        self._agents: AgentsResource | None = None
        self._graph: GraphResource | None = None
        self._ingest: IngestResource | None = None
        self._telemetry: TelemetryResource | None = None

    # -- Resource properties ------------------------------------------------

    @property
    def rag(self) -> RAGResource:
        """RAG search resource.

        Example::

            results = await client.rag.search("query")
        """
        if self._rag is None:
            self._rag = RAGResource(self._client)
        return self._rag

    @property
    def agents(self) -> AgentsResource:
        """Agent management and execution resource.

        Example::

            agents = await client.agents.list()
        """
        if self._agents is None:
            self._agents = AgentsResource(self._client)
        return self._agents

    @property
    def graph(self) -> GraphResource:
        """Knowledge graph exploration resource.

        Example::

            subset = await client.graph.explore("node-id")
        """
        if self._graph is None:
            self._graph = GraphResource(self._client)
        return self._graph

    @property
    def ingest(self) -> IngestResource:
        """Document ingestion resource.

        Example::

            result = await client.ingest.upload("file.pdf")
        """
        if self._ingest is None:
            self._ingest = IngestResource(self._client)
        return self._ingest

    @property
    def telemetry(self) -> TelemetryResource:
        """Telemetry, KPI, and cluster health resource.

        Example::

            stats = await client.telemetry.pipeline_stats()
        """
        if self._telemetry is None:
            self._telemetry = TelemetryResource(self._client)
        return self._telemetry

    # -- Context manager ----------------------------------------------------

    async def __aenter__(self) -> EngineClient:
        return self

    async def __aexit__(self, *exc: Any) -> None:
        await self.close()

    async def close(self) -> None:
        """Close the underlying HTTP client.

        Only closes the client if it was created internally (not
        when a custom ``httpx_client`` was provided).
        """
        if self._owns_client:
            await self._client.aclose()

    # -- Convenience --------------------------------------------------------

    @property
    def base_url(self) -> str:
        """The base URL this client is connected to."""
        return self._base_url

    @property
    def is_closed(self) -> bool:
        """Whether the underlying HTTP client is closed."""
        return self._client.is_closed

    def __repr__(self) -> str:
        return f"EngineClient(base_url={self._base_url!r})"
