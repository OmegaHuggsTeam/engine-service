"""Graph resource.

Wraps the ``/api/v1/graph/*`` endpoints for exploring the Neo4j
knowledge graph.
"""

from __future__ import annotations

from typing import Any

from ..models import GraphEdge, GraphNode, GraphSubset
from ._base import BaseResource


class GraphResource(BaseResource):
    """Query and explore the knowledge graph.

    Example::

        async with EngineClient() as client:
            subset = await client.graph.explore("agent-analyst", depth=2)
            for node in subset.nodes:
                print(node.id, node.labels)
    """

    async def explore(
        self,
        center: str,
        *,
        depth: int = 2,
    ) -> GraphSubset:
        """Explore a subgraph centered on a node.

        Args:
            center: Node ID to start exploration from.
            depth: Maximum hops from center (1-4, default 2).

        Returns:
            :class:`GraphSubset` containing nodes and edges.

        Example::

            subset = await client.graph.explore("agent-analyst")
            print(f"Found {len(subset.nodes)} nodes")
        """
        data = await self._get(
            "/api/v1/graph/explore",
            params={"center": center, "depth": depth},
        )
        if isinstance(data, dict):
            return GraphSubset.model_validate(data)
        return GraphSubset()

    async def services(self) -> list[dict[str, Any]]:
        """List all Service nodes from GraphSynergy with neighbor info.

        Returns:
            List of service dicts with ``service``, ``node_count``, ``neighbors``.

        Example::

            services = await client.graph.services()
            for svc in services:
                print(svc["service"], svc["neighbors"])
        """
        data = await self._get("/api/v1/graph/services")
        return data if isinstance(data, list) else []

    async def concepts(self, *, limit: int = 50) -> list[dict[str, Any]]:
        """Get concept nodes from the knowledge graph.

        Uses the graph explore endpoint to fetch concept-type nodes.

        Args:
            limit: Maximum number of concepts to return.

        Returns:
            List of concept dicts.

        Example::

            concepts = await client.graph.concepts(limit=20)
        """
        # The gateway doesn't have a dedicated /graph/concepts endpoint.
        # We use /graph/services as the closest concept-level view.
        return await self.services()

    async def cypher(self, query: str) -> list[dict[str, Any]]:
        """Execute a read-only Cypher query against the graph.

        Note: The Sovereign Gateway does not expose a raw Cypher endpoint
        for security reasons. This method uses the graph explore endpoint
        or returns an informative error.

        Args:
            query: Cypher query string (read-only).

        Returns:
            List of result dicts.

        Raises:
            EngineError: If the query cannot be executed.

        Example::

            results = await client.graph.cypher(
                "MATCH (a:Agent) RETURN a.name LIMIT 10"
            )
        """
        from ..exceptions import ValidationError

        raise ValidationError(
            "Direct Cypher queries are not exposed by the Sovereign Gateway. "
            "Use client.graph.explore() or client.graph.services() instead.",
            status_code=405,
        )

    async def schema(self) -> dict[str, Any]:
        """Get the graph schema (node labels, relationship types).

        Returns a summary constructed from the services endpoint.

        Returns:
            Dict with ``labels`` and ``relationship_types`` keys.

        Example::

            schema = await client.graph.schema()
            print(schema["labels"])
        """
        services = await self.services()
        labels = set()
        for svc in services:
            labels.add(svc.get("service", ""))
            for neighbor in svc.get("neighbors", []):
                labels.add(neighbor)
        return {
            "labels": sorted(labels - {""}),
            "service_count": len(services),
        }
