"""RAG (Retrieval-Augmented Generation) resource.

Wraps the ``/api/v1/rag/*`` endpoints for hybrid search across
chunks and graph concepts.
"""

from __future__ import annotations

from typing import Any

from ..models import RAGResult
from ._base import BaseResource


class RAGResource(BaseResource):
    """Search the HybridRAG pipeline.

    Example::

        async with EngineClient() as client:
            results = await client.rag.search("revenue Q4 2025", top_k=5)
            for r in results:
                print(r.content, r.score)
    """

    async def search(
        self,
        query: str,
        *,
        top_k: int = 5,
    ) -> list[RAGResult]:
        """Hybrid RAG search across chunks and concepts.

        Args:
            query: Natural-language search query.
            top_k: Maximum number of results to return (default 5, max 50).

        Returns:
            Ranked list of :class:`RAGResult` objects.

        Example::

            results = await client.rag.search("customer churn analysis")
            print(results[0].content)
        """
        data = await self._get(
            "/api/v1/rag/search",
            params={"q": query, "top_k": top_k},
        )
        if isinstance(data, list):
            return [RAGResult.model_validate(item) for item in data]
        return []

    async def search_by_category(
        self,
        query: str,
        category: str,
        *,
        top_k: int = 5,
    ) -> list[RAGResult]:
        """Search within a specific document category.

        This uses the ``/api/v1/tasks`` endpoint with context to scope
        the search to a given category.

        Args:
            query: Natural-language search query.
            category: Document category to filter by (e.g. ``"reports"``).
            top_k: Maximum number of results to return.

        Returns:
            Ranked list of :class:`RAGResult` objects.

        Example::

            results = await client.rag.search_by_category(
                "monthly metrics", "reports", top_k=3
            )
        """
        data = await self._post(
            "/api/v1/tasks",
            json={
                "query": query,
                "context": {"category": category, "top_k": top_k},
            },
        )
        # The tasks endpoint returns a dict with answer/results
        results = data.get("results", []) if isinstance(data, dict) else []
        return [RAGResult.model_validate(item) for item in results]
