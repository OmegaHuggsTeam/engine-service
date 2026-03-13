"""Tests for AgentsResource with mocked HTTP responses."""

from __future__ import annotations

import json

import pytest

from engine_sdk.models import AgentInfo, AgentResponse


@pytest.mark.asyncio
class TestAgentsList:
    """Test agent listing endpoint."""

    async def test_list_returns_agents(self, client, mock_transport):
        mock_transport.set_response(200, [
            {
                "id": "analyst",
                "name": "Data Analyst",
                "type": "domain",
                "status": "active",
                "success_rate": 0.95,
            },
            {
                "id": "writer",
                "name": "Content Writer",
                "type": "specialist",
                "status": "active",
                "success_rate": 0.88,
            },
        ])

        agents = await client.agents.list()

        assert len(agents) == 2
        assert isinstance(agents[0], AgentInfo)
        assert agents[0].id == "analyst"
        assert agents[0].name == "Data Analyst"
        assert agents[0].type == "domain"
        assert agents[0].status == "active"
        assert agents[0].success_rate == 0.95

    async def test_list_empty(self, client, mock_transport):
        mock_transport.set_response(200, [])

        agents = await client.agents.list()

        assert agents == []

    async def test_list_sends_get_request(self, client, mock_transport):
        mock_transport.set_response(200, [])

        await client.agents.list()

        req = mock_transport.last_request
        assert req.method == "GET"
        assert "/api/v1/agents" in str(req.url)


@pytest.mark.asyncio
class TestAgentsExecute:
    """Test task execution via agents."""

    async def test_execute_returns_response(self, client, mock_transport):
        mock_transport.set_response(200, {
            "answer": "Q4 revenue was $10M, up 15% YoY",
            "agent_id": "analyst",
            "processing_time_ms": 1250,
            "model_used": "claude-3-haiku",
            "cost": 0.003,
        })

        resp = await client.agents.execute(
            "analyst", "summarize Q4 revenue"
        )

        assert isinstance(resp, AgentResponse)
        assert resp.agent_id == "analyst"
        assert resp.task == "summarize Q4 revenue"
        assert "Q4 revenue" in str(resp.result)
        assert resp.processing_time_ms == 1250
        assert resp.model_used == "claude-3-haiku"
        assert resp.cost == 0.003

    async def test_execute_sends_post_with_query(self, client, mock_transport):
        mock_transport.set_response(200, {"answer": "ok"})

        await client.agents.execute("analyst", "test task")

        req = mock_transport.last_request
        assert req.method == "POST"
        body = json.loads(req.content)
        assert body["query"] == "test task"
        assert body["context"]["preferred_agent"] == "analyst"

    async def test_execute_with_custom_context(self, client, mock_transport):
        mock_transport.set_response(200, {"answer": "ok"})

        await client.agents.execute(
            "analyst",
            "test task",
            context={"department": "finance"},
        )

        req = mock_transport.last_request
        body = json.loads(req.content)
        assert body["context"]["department"] == "finance"


@pytest.mark.asyncio
class TestAgentsCreate:
    """Test agent creation."""

    async def test_create_agent(self, client, mock_transport):
        mock_transport.set_response(200, {
            "id": "custom-1",
            "name": "Custom Agent",
            "type": "custom",
            "status": "active",
        })

        agent = await client.agents.create(
            id="custom-1",
            name="Custom Agent",
            type="custom",
            capabilities=["analysis"],
        )

        assert isinstance(agent, AgentInfo)
        assert agent.id == "custom-1"
        assert agent.name == "Custom Agent"

    async def test_create_sends_correct_payload(self, client, mock_transport):
        mock_transport.set_response(200, {
            "id": "x", "name": "X", "type": "custom", "status": "active",
        })

        await client.agents.create(
            id="x",
            name="X",
            capabilities=["a", "b"],
        )

        req = mock_transport.last_request
        body = json.loads(req.content)
        assert body["id"] == "x"
        assert body["name"] == "X"
        assert body["capabilities"] == ["a", "b"]


@pytest.mark.asyncio
class TestAgentsUpdate:
    """Test agent updates."""

    async def test_update_agent(self, client, mock_transport):
        mock_transport.set_response(200, {
            "id": "analyst",
            "name": "Updated Analyst",
            "type": "domain",
            "status": "inactive",
        })

        agent = await client.agents.update(
            "analyst", status="inactive"
        )

        assert agent.status == "inactive"

    async def test_update_sends_put(self, client, mock_transport):
        mock_transport.set_response(200, {
            "id": "a", "name": "A", "type": "t", "status": "active",
        })

        await client.agents.update("a", name="New Name")

        req = mock_transport.last_request
        assert req.method == "PUT"
        assert "/api/v1/agents/a" in str(req.url)


@pytest.mark.asyncio
class TestAgentsDelete:
    """Test agent soft-deletion."""

    async def test_delete_agent(self, client, mock_transport):
        mock_transport.set_response(200, {
            "success": True, "agent_id": "custom-1",
        })

        result = await client.agents.delete("custom-1")

        assert result["success"] is True

    async def test_delete_sends_delete(self, client, mock_transport):
        mock_transport.set_response(200, {"success": True})

        await client.agents.delete("x")

        req = mock_transport.last_request
        assert req.method == "DELETE"


@pytest.mark.asyncio
class TestAgentsHealth:
    """Test agent health check (alias for list)."""

    async def test_health_returns_agents(self, client, mock_transport):
        mock_transport.set_response(200, [
            {"id": "a", "name": "A", "type": "t", "status": "active"},
        ])

        agents = await client.agents.health()

        assert len(agents) == 1
        assert agents[0].id == "a"
