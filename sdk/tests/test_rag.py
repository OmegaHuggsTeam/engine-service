"""Tests for RAGResource with mocked HTTP responses."""

from __future__ import annotations

import json

import pytest

from engine_sdk.models import RAGResult


@pytest.mark.asyncio
class TestRAGSearch:
    """Test RAG search endpoint."""

    async def test_search_returns_results(self, client, mock_transport):
        mock_transport.set_response(200, [
            {
                "content": "Q4 revenue was $10M",
                "source": "report.pdf",
                "score": 0.95,
                "metadata": {"page": 3},
            },
            {
                "content": "Revenue grew 15% YoY",
                "source": "analysis.md",
                "score": 0.87,
                "metadata": {},
            },
        ])

        results = await client.rag.search("revenue Q4")

        assert len(results) == 2
        assert isinstance(results[0], RAGResult)
        assert results[0].content == "Q4 revenue was $10M"
        assert results[0].source_file == "report.pdf"
        assert results[0].score == 0.95
        assert results[0].metadata == {"page": 3}

    async def test_search_empty_results(self, client, mock_transport):
        mock_transport.set_response(200, [])

        results = await client.rag.search("nonexistent topic")

        assert results == []

    async def test_search_sends_correct_params(self, client, mock_transport):
        mock_transport.set_response(200, [])

        await client.rag.search("test query", top_k=3)

        req = mock_transport.last_request
        assert req is not None
        assert req.method == "GET"
        assert "q=test+query" in str(req.url) or "q=test%20query" in str(req.url)
        assert "top_k=3" in str(req.url)

    async def test_search_default_top_k(self, client, mock_transport):
        mock_transport.set_response(200, [])

        await client.rag.search("test")

        req = mock_transport.last_request
        assert "top_k=5" in str(req.url)


@pytest.mark.asyncio
class TestRAGSearchByCategory:
    """Test category-scoped RAG search."""

    async def test_search_by_category(self, client, mock_transport):
        mock_transport.set_response(200, {
            "answer": "Revenue summary...",
            "results": [
                {
                    "content": "Revenue report",
                    "source": "report.pdf",
                    "score": 0.9,
                    "metadata": {},
                }
            ],
        })

        results = await client.rag.search_by_category(
            "revenue", "reports", top_k=3
        )

        assert len(results) == 1
        assert results[0].content == "Revenue report"

    async def test_search_by_category_posts_correct_payload(
        self, client, mock_transport
    ):
        mock_transport.set_response(200, {"results": []})

        await client.rag.search_by_category("test", "docs")

        req = mock_transport.last_request
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["query"] == "test"
        assert body["context"]["category"] == "docs"
