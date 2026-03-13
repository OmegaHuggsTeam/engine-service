"""Agents resource.

Wraps the ``/api/v1/agents/*`` endpoints for managing and executing
tasks through the multi-agent orchestrator.
"""

from __future__ import annotations

from typing import Any

from ..models import AgentInfo, AgentResponse
from ._base import BaseResource


class AgentsResource(BaseResource):
    """Manage and execute tasks through agents.

    Example::

        async with EngineClient() as client:
            agents = await client.agents.list()
            for a in agents:
                print(f"{a.name}: {a.status}")
    """

    async def list(self) -> list[AgentInfo]:
        """List all registered agents with status and performance metrics.

        Returns:
            List of :class:`AgentInfo` objects.

        Example::

            agents = await client.agents.list()
            active = [a for a in agents if a.status == "active"]
        """
        data = await self._get("/api/v1/agents")
        if isinstance(data, list):
            return [AgentInfo.model_validate(item) for item in data]
        return []

    async def get_history(
        self,
        agent_id: str,
        *,
        limit: int = 20,
    ) -> list[dict[str, Any]]:
        """Get task history for a specific agent.

        Args:
            agent_id: Unique identifier of the agent.
            limit: Maximum number of history entries (default 20, max 100).

        Returns:
            List of task history records.

        Example::

            history = await client.agents.get_history("analyst", limit=10)
        """
        data = await self._get(
            f"/api/v1/agents/{agent_id}/history",
            params={"limit": limit},
        )
        return data if isinstance(data, list) else []

    async def execute(
        self,
        agent_id: str,
        task: str,
        *,
        context: dict[str, Any] | None = None,
    ) -> AgentResponse:
        """Submit a task to the Neural Link orchestrator.

        The orchestrator routes the task to the appropriate agent based
        on the query content and agent capabilities.

        Args:
            agent_id: Hint for preferred agent (routing may override).
            task: Natural-language task description.
            context: Optional context dict passed to the orchestrator.

        Returns:
            :class:`AgentResponse` with the result and metrics.

        Example::

            resp = await client.agents.execute(
                "analyst", "summarize revenue trends for Q4"
            )
            print(resp.result)
        """
        payload: dict[str, Any] = {"query": task}
        if context:
            payload["context"] = context
        else:
            payload["context"] = {"preferred_agent": agent_id}

        data = await self._post("/api/v1/tasks", json=payload)
        if isinstance(data, dict):
            return AgentResponse(
                agent_id=data.get("agent_id", agent_id),
                task=task,
                result=data.get("answer", data.get("result", "")),
                processing_time_ms=data.get("processing_time_ms", 0),
                model_used=data.get("model_used", ""),
                cost=data.get("cost", 0.0),
            )
        return AgentResponse(agent_id=agent_id, task=task)

    async def create(
        self,
        *,
        id: str,
        name: str,
        type: str = "custom",
        module_path: str = "",
        capabilities: list[str] | None = None,
    ) -> AgentInfo:
        """Register a custom agent.

        Args:
            id: Unique identifier for the agent.
            name: Human-readable agent name.
            type: Agent type (``"domain"``, ``"specialist"``, ``"operator"``, ``"custom"``).
            module_path: Python module path for the agent implementation.
            capabilities: List of capability strings.

        Returns:
            :class:`AgentInfo` for the created agent.

        Example::

            agent = await client.agents.create(
                id="custom-analyst",
                name="Custom Analyst",
                type="specialist",
                capabilities=["analysis", "reporting"],
            )
        """
        data = await self._post(
            "/api/v1/agents",
            json={
                "id": id,
                "name": name,
                "type": type,
                "module_path": module_path,
                "capabilities": capabilities or [],
            },
        )
        return AgentInfo.model_validate(data)

    async def update(
        self,
        agent_id: str,
        *,
        name: str | None = None,
        type: str | None = None,
        capabilities: list[str] | None = None,
        status: str | None = None,
        success_rate: float | None = None,
    ) -> AgentInfo:
        """Update an existing agent's metadata.

        Args:
            agent_id: Agent to update.
            name: New name (optional).
            type: New type (optional).
            capabilities: New capabilities list (optional).
            status: New status (optional).
            success_rate: New success rate (optional).

        Returns:
            Updated :class:`AgentInfo`.

        Example::

            agent = await client.agents.update(
                "custom-analyst", status="inactive"
            )
        """
        payload: dict[str, Any] = {}
        if name is not None:
            payload["name"] = name
        if type is not None:
            payload["type"] = type
        if capabilities is not None:
            payload["capabilities"] = capabilities
        if status is not None:
            payload["status"] = status
        if success_rate is not None:
            payload["success_rate"] = success_rate

        data = await self._put(f"/api/v1/agents/{agent_id}", json=payload)
        return AgentInfo.model_validate(data)

    async def delete(self, agent_id: str) -> dict[str, Any]:
        """Soft-delete an agent (sets status to inactive).

        Args:
            agent_id: Agent to deactivate.

        Returns:
            Confirmation dict.

        Example::

            await client.agents.delete("custom-analyst")
        """
        data = await self._delete(f"/api/v1/agents/{agent_id}")
        return data if isinstance(data, dict) else {"success": True}

    async def health(self) -> list[AgentInfo]:
        """Get health status of all agents (alias for :meth:`list`).

        Returns:
            List of :class:`AgentInfo` with current status.

        Example::

            healthy = await client.agents.health()
            for a in healthy:
                print(f"{a.name}: {a.status}")
        """
        return await self.list()
