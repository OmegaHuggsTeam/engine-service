"""Tests for EngineClient initialization, context manager, and resource access."""

from __future__ import annotations

import pytest
import httpx

from engine_sdk import EngineClient, EngineSyncClient
from engine_sdk.resources.rag import RAGResource
from engine_sdk.resources.agents import AgentsResource
from engine_sdk.resources.graph import GraphResource
from engine_sdk.resources.ingest import IngestResource
from engine_sdk.resources.telemetry import TelemetryResource


class TestEngineClientInit:
    """Test client construction and configuration."""

    def test_default_base_url(self):
        client = EngineClient()
        assert client.base_url == "http://localhost:8766"

    def test_custom_base_url(self):
        client = EngineClient(base_url="https://api.huggs.tech")
        assert client.base_url == "https://api.huggs.tech"

    def test_trailing_slash_stripped(self):
        client = EngineClient(base_url="http://localhost:8766/")
        assert client.base_url == "http://localhost:8766"

    def test_repr(self):
        client = EngineClient(base_url="http://localhost:8766")
        assert "localhost:8766" in repr(client)

    def test_not_closed_on_init(self):
        client = EngineClient()
        assert not client.is_closed


class TestEngineClientResources:
    """Test that resource properties return correct types."""

    def test_rag_resource(self):
        client = EngineClient()
        assert isinstance(client.rag, RAGResource)

    def test_agents_resource(self):
        client = EngineClient()
        assert isinstance(client.agents, AgentsResource)

    def test_graph_resource(self):
        client = EngineClient()
        assert isinstance(client.graph, GraphResource)

    def test_ingest_resource(self):
        client = EngineClient()
        assert isinstance(client.ingest, IngestResource)

    def test_telemetry_resource(self):
        client = EngineClient()
        assert isinstance(client.telemetry, TelemetryResource)

    def test_resource_cached(self):
        client = EngineClient()
        rag1 = client.rag
        rag2 = client.rag
        assert rag1 is rag2


class TestEngineClientContextManager:
    """Test async context manager behavior."""

    @pytest.mark.asyncio
    async def test_context_manager_closes_client(self):
        async with EngineClient() as client:
            assert not client.is_closed
        assert client.is_closed

    @pytest.mark.asyncio
    async def test_custom_httpx_client_not_closed(self):
        """When a custom httpx client is provided, we don't close it."""
        http_client = httpx.AsyncClient()
        async with EngineClient(httpx_client=http_client) as client:
            pass
        # Custom client should NOT be closed by EngineClient
        assert not http_client.is_closed
        await http_client.aclose()


class TestEngineSyncClient:
    """Test synchronous client wrapper."""

    def test_default_base_url(self):
        client = EngineSyncClient()
        assert client.base_url == "http://localhost:8766"

    def test_repr(self):
        client = EngineSyncClient()
        assert "localhost:8766" in repr(client)

    def test_context_manager(self):
        with EngineSyncClient() as client:
            assert client.base_url == "http://localhost:8766"

    def test_resource_types(self):
        client = EngineSyncClient()
        # Just verify they're accessible (they're sync wrappers)
        assert client.rag is not None
        assert client.agents is not None
        assert client.graph is not None
        assert client.ingest is not None
        assert client.telemetry is not None
