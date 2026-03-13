"""Pydantic response models for the Engine SDK.

These models mirror the Sovereign Gateway response shapes and provide
type-safe access to all returned fields.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# RAG
# ---------------------------------------------------------------------------

class RAGResult(BaseModel):
    """A single search result from the HybridRAG pipeline.

    Example::

        result = results[0]
        print(result.content, result.score)
    """

    content: str = ""
    source_file: str = Field(default="", alias="source")
    score: float = 0.0
    metadata: dict[str, Any] = Field(default_factory=dict)

    model_config = {"populate_by_name": True}


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    """Metadata for a registered agent.

    Example::

        for agent in agents:
            print(f"{agent.name} ({agent.type}) - {agent.status}")
    """

    id: str
    name: str
    type: str
    status: str = "active"
    capabilities: list[str] = Field(default_factory=list)
    success_rate: float | None = None


class AgentResponse(BaseModel):
    """Response from executing a task via an agent.

    Example::

        resp = await client.agents.execute("analyst", "summarize Q4 revenue")
        print(resp.result)
    """

    agent_id: str = ""
    task: str = ""
    result: dict[str, Any] | str = ""
    processing_time_ms: float = 0.0
    model_used: str = ""
    cost: float = 0.0


# ---------------------------------------------------------------------------
# Ingest
# ---------------------------------------------------------------------------

class IngestResult(BaseModel):
    """Result of a document ingestion operation.

    Example::

        result = await client.ingest.upload("report.pdf", category="reports")
        print(f"Created {result.chunks_created} chunks")
    """

    chunks_created: int = 0
    source_file: str = ""
    category: str = ""
    models_embedded: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Telemetry / Pipeline
# ---------------------------------------------------------------------------

class PipelineStats(BaseModel):
    """Aggregate statistics from the pipeline cost tracker.

    Example::

        stats = await client.telemetry.pipeline_stats()
        print(f"Cache hit rate: {stats.cache_hit_rate}%")
    """

    cache_hit_rate: float = 0.0
    avg_latency_ms: float = 0.0
    total_requests: int = 0
    active_agents: int = 0
    cost_today: float = 0.0


# ---------------------------------------------------------------------------
# Graph
# ---------------------------------------------------------------------------

class GraphNode(BaseModel):
    """A node returned from a graph query.

    Example::

        for node in nodes:
            print(node.id, node.labels, node.properties)
    """

    id: str
    labels: list[str] = Field(default_factory=list)
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphEdge(BaseModel):
    """An edge (relationship) returned from a graph query."""

    source: str
    target: str
    type: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GraphSubset(BaseModel):
    """A subgraph consisting of nodes and edges."""

    nodes: list[GraphNode] = Field(default_factory=list)
    edges: list[GraphEdge] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Error Resolution (from Jitbit)
# ---------------------------------------------------------------------------

class ErrorResolution(BaseModel):
    """A Jitbit macro error resolution record.

    Example::

        print(f"{resolution.error_type}: {resolution.resolution}")
    """

    error_type: str = ""
    skill_name: str = ""
    resolution: str = ""
    frequency: int = 0


# ---------------------------------------------------------------------------
# CRM
# ---------------------------------------------------------------------------

class CrmLead(BaseModel):
    """A CRM lead record."""

    id: str
    name: str
    email: str | None = None
    company: str | None = None
    trust: float = 0.5
    interaction_count: int = 0
    source_channel: str = "manual"
    tags: list[str] = Field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""


class CrmLeadScore(BaseModel):
    """Computed lead scoring breakdown."""

    lead_id: str
    trust: float
    interaction_count: int
    last_interaction: str | None = None
    flow_count: int = 0
    interaction_score: float = 0.0
    recency_score: float = 0.0
    flow_score: float = 0.0


class CrmFlow(BaseModel):
    """A CRM automation flow."""

    id: str
    name: str
    objective: str = ""
    n8n_workflow_id: str | None = None
    status: str = "draft"
    lead_count: int = 0
    created_at: str = ""


class CrmStats(BaseModel):
    """Aggregate CRM statistics."""

    total_leads: int = 0
    total_flows: int = 0
    total_interactions: int = 0
    avg_trust: float = 0.0


# ---------------------------------------------------------------------------
# KPI
# ---------------------------------------------------------------------------

class KpiRecommendation(BaseModel):
    """Model recommendation from the cost-quality analyzer."""

    model: str = ""
    avg_quality: float = 0.0
    total_cost: float = 0.0
    total_requests: int = 0
    cost_per_quality_point: float = 0.0
    reason: str = ""


# ---------------------------------------------------------------------------
# Cluster
# ---------------------------------------------------------------------------

class ClusterHealth(BaseModel):
    """Cluster health status (ChromaDB, Neo4j, Evidence, n8n, Tailscale)."""

    timestamp: str = ""
    services: dict[str, Any] = Field(default_factory=dict)
    summary: dict[str, int] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Flows (n8n)
# ---------------------------------------------------------------------------

class FlowComposeResult(BaseModel):
    """Result of composing a workflow from natural language."""

    objective: str = ""
    workflow: dict[str, Any] = Field(default_factory=dict)
    nodes: list[str] = Field(default_factory=list)
    status: str = "composed"


class FlowDeployResult(BaseModel):
    """Result of deploying a workflow to n8n."""

    success: bool = False
    message: str = ""
    workflow_id: str | None = None


# ---------------------------------------------------------------------------
# Containers
# ---------------------------------------------------------------------------

class ContainerInfo(BaseModel):
    """Metadata for a spawned container."""

    container_id: str
    node_id: str
    tenant_id: str
    image: str
    status: str
    started_at: str | None = None


class ContainerStatus(BaseModel):
    """Runtime status and metrics for a container."""

    container_id: str
    status: str
    memory_mb: float = 0.0
    cpu_percent: float = 0.0
    started_at: str | None = None
    finished_at: str | None = None
    exit_code: int | None = None
    logs: str = ""


class ContainerExecResult(BaseModel):
    """Result of executing a command inside a container."""

    container_id: str
    exit_code: int
    stdout: str = ""
    stderr: str = ""
    duration_ms: float = 0.0
