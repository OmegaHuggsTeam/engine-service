"""Tests for Pydantic model validation."""

from __future__ import annotations

import pytest

from engine_sdk.models import (
    AgentInfo,
    AgentResponse,
    ClusterHealth,
    ContainerExecResult,
    ContainerInfo,
    ContainerStatus,
    CrmFlow,
    CrmLead,
    CrmLeadScore,
    CrmStats,
    ErrorResolution,
    FlowComposeResult,
    FlowDeployResult,
    GraphEdge,
    GraphNode,
    GraphSubset,
    IngestResult,
    KpiRecommendation,
    PipelineStats,
    RAGResult,
)


class TestRAGResult:
    """Test RAGResult model validation."""

    def test_full_construction(self):
        r = RAGResult(
            content="hello",
            source="file.pdf",
            score=0.95,
            metadata={"page": 1},
        )
        assert r.content == "hello"
        assert r.source_file == "file.pdf"
        assert r.score == 0.95
        assert r.metadata == {"page": 1}

    def test_defaults(self):
        r = RAGResult()
        assert r.content == ""
        assert r.source_file == ""
        assert r.score == 0.0
        assert r.metadata == {}

    def test_alias_source(self):
        """source_file has alias 'source' for gateway compatibility."""
        r = RAGResult.model_validate({"source": "test.pdf"})
        assert r.source_file == "test.pdf"

    def test_populate_by_name(self):
        """Can also use source_file directly."""
        r = RAGResult(source_file="direct.pdf")
        assert r.source_file == "direct.pdf"


class TestAgentInfo:
    """Test AgentInfo model."""

    def test_full_construction(self):
        a = AgentInfo(
            id="analyst",
            name="Data Analyst",
            type="domain",
            status="active",
            capabilities=["analysis"],
            success_rate=0.95,
        )
        assert a.id == "analyst"
        assert a.capabilities == ["analysis"]

    def test_defaults(self):
        a = AgentInfo(id="x", name="X", type="t")
        assert a.status == "active"
        assert a.capabilities == []
        assert a.success_rate is None


class TestAgentResponse:
    """Test AgentResponse model."""

    def test_full_construction(self):
        r = AgentResponse(
            agent_id="analyst",
            task="summarize",
            result={"answer": "done"},
            processing_time_ms=500,
            model_used="haiku",
            cost=0.001,
        )
        assert r.agent_id == "analyst"
        assert r.cost == 0.001

    def test_defaults(self):
        r = AgentResponse()
        assert r.agent_id == ""
        assert r.cost == 0.0


class TestIngestResult:
    """Test IngestResult model."""

    def test_full_construction(self):
        r = IngestResult(
            chunks_created=42,
            source_file="report.pdf",
            category="reports",
            models_embedded=["text-embedding-3-small"],
        )
        assert r.chunks_created == 42
        assert r.models_embedded == ["text-embedding-3-small"]

    def test_defaults(self):
        r = IngestResult()
        assert r.chunks_created == 0
        assert r.models_embedded == []


class TestPipelineStats:
    """Test PipelineStats model."""

    def test_full_construction(self):
        s = PipelineStats(
            cache_hit_rate=0.75,
            avg_latency_ms=120.5,
            total_requests=5000,
            active_agents=12,
            cost_today=1.50,
        )
        assert s.cache_hit_rate == 0.75
        assert s.total_requests == 5000

    def test_defaults(self):
        s = PipelineStats()
        assert s.total_requests == 0


class TestGraphModels:
    """Test graph-related models."""

    def test_graph_node(self):
        n = GraphNode(
            id="node-1",
            labels=["Agent"],
            properties={"name": "test"},
        )
        assert n.id == "node-1"
        assert "Agent" in n.labels

    def test_graph_edge(self):
        e = GraphEdge(
            source="a", target="b", type="RELATES_TO",
        )
        assert e.source == "a"
        assert e.type == "RELATES_TO"

    def test_graph_subset(self):
        s = GraphSubset(
            nodes=[GraphNode(id="a", labels=["X"])],
            edges=[GraphEdge(source="a", target="b", type="R")],
        )
        assert len(s.nodes) == 1
        assert len(s.edges) == 1

    def test_graph_subset_defaults(self):
        s = GraphSubset()
        assert s.nodes == []
        assert s.edges == []


class TestCrmModels:
    """Test CRM-related models."""

    def test_crm_lead(self):
        lead = CrmLead(
            id="lead-1",
            name="John Doe",
            email="john@example.com",
            trust=0.8,
        )
        assert lead.id == "lead-1"
        assert lead.trust == 0.8

    def test_crm_lead_defaults(self):
        lead = CrmLead(id="x", name="X")
        assert lead.trust == 0.5
        assert lead.tags == []

    def test_crm_flow(self):
        flow = CrmFlow(id="flow-1", name="Onboarding")
        assert flow.status == "draft"

    def test_crm_stats(self):
        s = CrmStats(total_leads=100, avg_trust=0.6)
        assert s.total_leads == 100

    def test_crm_lead_score(self):
        score = CrmLeadScore(
            lead_id="lead-1",
            trust=0.75,
            interaction_count=10,
            flow_count=2,
        )
        assert score.trust == 0.75


class TestClusterHealth:
    """Test ClusterHealth model."""

    def test_construction(self):
        h = ClusterHealth(
            timestamp="2025-01-01T00:00:00",
            services={"neo4j": {"status": "ok"}},
            summary={"total": 5, "ok": 4, "fail": 1},
        )
        assert h.summary["ok"] == 4


class TestKpiRecommendation:
    """Test KpiRecommendation model."""

    def test_construction(self):
        r = KpiRecommendation(
            model="claude-3-haiku",
            avg_quality=0.92,
            total_cost=5.50,
            reason="Best cost/quality ratio",
        )
        assert r.model == "claude-3-haiku"


class TestFlowModels:
    """Test Flow models."""

    def test_compose_result(self):
        r = FlowComposeResult(
            objective="Send welcome emails",
            status="composed",
        )
        assert r.objective == "Send welcome emails"

    def test_deploy_result(self):
        r = FlowDeployResult(
            success=True,
            message="Deployed",
            workflow_id="wf-123",
        )
        assert r.success is True


class TestContainerModels:
    """Test Container models."""

    def test_container_info(self):
        c = ContainerInfo(
            container_id="c-1",
            node_id="n-1",
            tenant_id="t-1",
            image="python:3.12-slim",
            status="running",
        )
        assert c.status == "running"

    def test_container_status(self):
        s = ContainerStatus(
            container_id="c-1",
            status="running",
            memory_mb=64.5,
            cpu_percent=12.3,
        )
        assert s.memory_mb == 64.5

    def test_container_exec_result(self):
        r = ContainerExecResult(
            container_id="c-1",
            exit_code=0,
            stdout="hello\n",
            duration_ms=150.0,
        )
        assert r.exit_code == 0


class TestErrorResolution:
    """Test ErrorResolution model."""

    def test_construction(self):
        e = ErrorResolution(
            error_type="timeout",
            skill_name="heal_macro",
            resolution="Restarted service",
            frequency=5,
        )
        assert e.frequency == 5
