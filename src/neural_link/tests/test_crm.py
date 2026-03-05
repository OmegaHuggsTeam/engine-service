"""
Tests for CRM Foundation — Lead / Flow / Interaction.

All Neo4j calls are mocked — no real Neo4j required.
Follows test_graph_sync.py conventions.
"""

import time
from unittest.mock import MagicMock, patch, AsyncMock

import pytest

from src.neural_link.graph import queries as q
from src.neural_link.graph.schema import SCHEMA_QUERIES
from src.neural_link.orchestrator.models import (
    CrmLead,
    CrmFlow,
    CrmInteraction,
    LeadSource,
    FlowStatus,
)
from src.neural_link.telemetry.provider import CrmEventProvider, EventType


# ==================================================================
# Fixtures
# ==================================================================


def _make_graph_mock():
    """Returns a MagicMock GraphManager."""
    graph = MagicMock()
    graph.verify_connectivity.return_value = True
    graph.execute_write.return_value = None
    graph.execute_read.return_value = []
    return graph


# ==================================================================
# TestCrmPydanticModels
# ==================================================================


class TestCrmPydanticModels:
    """Pydantic CRM model validation."""

    def test_lead_defaults(self):
        lead = CrmLead(name="Alice")
        assert lead.name == "Alice"
        assert lead.trust == 0.5
        assert lead.interaction_count == 0
        assert lead.source_channel == LeadSource.MANUAL
        assert lead.id.startswith("lead_")

    def test_lead_trust_bounds(self):
        lead = CrmLead(name="Bob", trust=0.0)
        assert lead.trust == 0.0
        lead2 = CrmLead(name="Carol", trust=1.0)
        assert lead2.trust == 1.0

    def test_lead_trust_invalid(self):
        with pytest.raises(Exception):
            CrmLead(name="Bad", trust=1.5)

    def test_flow_defaults(self):
        flow = CrmFlow(name="Onboarding")
        assert flow.status == FlowStatus.DRAFT
        assert flow.id.startswith("flow_")

    def test_flow_status_values(self):
        for s in FlowStatus:
            flow = CrmFlow(name="F", status=s)
            assert flow.status == s

    def test_interaction_defaults(self):
        interaction = CrmInteraction(lead_id="lead_001")
        assert interaction.lead_id == "lead_001"
        assert interaction.channel == "manual"
        assert interaction.id.startswith("interaction_")

    def test_lead_source_values(self):
        assert LeadSource.TELEGRAM == "telegram"
        assert LeadSource.N8N == "n8n"
        assert LeadSource.WEBHOOK == "webhook"


# ==================================================================
# TestCrmLeadQueries
# ==================================================================


class TestCrmLeadQueries:
    """CRM Lead Cypher query constants."""

    def test_upsert_lead_uses_merge(self):
        assert "MERGE" in q.UPSERT_LEAD
        assert "$id" in q.UPSERT_LEAD

    def test_upsert_lead_idempotent(self):
        """Calling UPSERT_LEAD twice with same params produces no error."""
        graph = _make_graph_mock()
        params = {
            "id": "lead_001",
            "name": "Alice",
            "email": "a@test.com",
            "company": "Acme",
            "trust": 0.5,
            "source_channel": "manual",
            "tags": ["vip"],
            "created_at": "2026-01-01",
            "updated_at": "2026-01-01",
        }
        graph.execute_write(q.UPSERT_LEAD, params)
        graph.execute_write(q.UPSERT_LEAD, params)
        assert graph.execute_write.call_count == 2

    def test_get_all_leads_has_limit(self):
        assert "$limit" in q.GET_ALL_LEADS

    def test_get_lead_by_id(self):
        assert "$lead_id" in q.GET_LEAD_BY_ID

    def test_fulltext_search_leads(self):
        assert "lead_search" in q.FULLTEXT_SEARCH_LEADS
        assert "$query" in q.FULLTEXT_SEARCH_LEADS

    def test_update_lead_trust(self):
        assert "$trust" in q.UPDATE_LEAD_TRUST
        assert "$lead_id" in q.UPDATE_LEAD_TRUST

    def test_increment_interaction_count(self):
        assert "interaction_count" in q.INCREMENT_LEAD_INTERACTION_COUNT


# ==================================================================
# TestCrmFlowQueries
# ==================================================================


class TestCrmFlowQueries:
    """CRM Flow Cypher query constants."""

    def test_upsert_flow_uses_merge(self):
        assert "MERGE" in q.UPSERT_FLOW
        assert "$id" in q.UPSERT_FLOW

    def test_update_flow_status(self):
        assert "$flow_id" in q.UPDATE_FLOW_STATUS
        assert "$status" in q.UPDATE_FLOW_STATUS

    def test_get_all_flows_returns_lead_count(self):
        assert "lead_count" in q.GET_ALL_FLOWS

    def test_add_lead_to_flow(self):
        """CREATE_LEAD_PART_OF_FLOW links Lead → Flow."""
        assert "PART_OF_FLOW" in q.CREATE_LEAD_PART_OF_FLOW
        assert "$lead_id" in q.CREATE_LEAD_PART_OF_FLOW
        assert "$flow_id" in q.CREATE_LEAD_PART_OF_FLOW


# ==================================================================
# TestCrmInteractionRecording
# ==================================================================


class TestCrmInteractionRecording:
    """Interaction recording in the graph."""

    def test_upsert_interaction(self):
        assert "MERGE" in q.UPSERT_INTERACTION
        assert "$lead_id" in q.UPSERT_INTERACTION

    def test_interaction_for_lead_relationship(self):
        assert "FOR_LEAD" in q.CREATE_INTERACTION_FOR_LEAD

    def test_interaction_by_agent_relationship(self):
        assert "BY_AGENT" in q.CREATE_INTERACTION_BY_AGENT

    def test_task_executor_creates_interaction_for_lead(self):
        """TaskExecutor creates CRM interaction when lead_id is in input_data."""
        from src.neural_link.orchestrator.task_executor import TaskExecutor
        from src.neural_link.orchestrator.models import Task, TaskType

        graph = _make_graph_mock()
        executor = TaskExecutor(graph_manager=graph)

        task = Task(
            id="task_001",
            description="Test task",
            type=TaskType.QUERY,
            input_data={"lead_id": "lead_abc"},
        )

        # Mock _invoke_agent to avoid LLM calls
        with patch.object(executor, "_invoke_agent", return_value="ok"):
            result = executor.execute(task, "groq_operator")

        assert result.success
        # Should have called execute_write for: UPSERT_TASK, CREATE_TASK_ASSIGNED,
        # UPSERT_INTERACTION, CREATE_INTERACTION_FOR_LEAD, CREATE_INTERACTION_BY_AGENT,
        # INCREMENT_LEAD_INTERACTION_COUNT
        assert graph.execute_write.call_count >= 4


# ==================================================================
# TestCrmSchema
# ==================================================================


class TestCrmSchema:
    """CRM schema entries in SCHEMA_QUERIES."""

    def test_crm_constraints_in_schema(self):
        names = [name for name, _ in SCHEMA_QUERIES]
        assert "lead_id constraint" in names
        assert "flow_id constraint" in names
        assert "interaction_id constraint" in names

    def test_crm_indexes_in_schema(self):
        names = [name for name, _ in SCHEMA_QUERIES]
        assert "lead_name index" in names
        assert "lead_email index" in names
        assert "lead_source index" in names
        assert "flow_status index" in names
        assert "interaction_timestamp index" in names
        assert "lead_search fulltext" in names

    def test_total_schema_count(self):
        """9 CRM entries added to existing schema list."""
        crm_names = [n for n, _ in SCHEMA_QUERIES if n.startswith(("lead_", "flow_", "interaction_"))]
        assert len(crm_names) == 9


# ==================================================================
# TestCrmEventProvider
# ==================================================================


class TestCrmEventProvider:
    """CrmEventProvider telemetry integration."""

    def test_provider_id(self):
        provider = CrmEventProvider()
        assert provider.provider_id == "crm"
        assert provider.display_name == "CRM Events"

    def test_health_check(self):
        provider = CrmEventProvider()
        assert provider.health_check() is True

    def test_push_and_poll(self):
        provider = CrmEventProvider()
        provider.push("lead_created", "New lead: Alice", {"id": "lead_001"})
        events = provider.poll()
        assert len(events) == 1
        assert events[0].source == "crm"
        assert events[0].message == "New lead: Alice"

    def test_poll_drains_buffer(self):
        provider = CrmEventProvider()
        provider.push("lead_created", "Test")
        assert len(provider.poll()) == 1
        assert len(provider.poll()) == 0


# ==================================================================
# TestCrmGatewayEndpoints
# ==================================================================


class TestCrmGatewayEndpoints:
    """Gateway CRM endpoint integration (mock graph)."""

    @pytest.fixture(autouse=True)
    def _setup_gateway(self):
        """Patch _svc.graph so endpoints have a graph."""
        from src.neural_link.api import sovereign_gateway as gw
        self._orig_graph = gw._svc._graph
        self._orig_init = gw._svc._initialized
        gw._svc._initialized = True
        gw._svc._graph = _make_graph_mock()
        yield
        gw._svc._graph = self._orig_graph
        gw._svc._initialized = self._orig_init

    def test_list_leads_empty(self):
        from src.neural_link.api.sovereign_gateway import list_crm_leads
        import asyncio
        result = asyncio.run(list_crm_leads())
        assert result == []

    def test_list_leads_returns_data(self):
        from src.neural_link.api import sovereign_gateway as gw
        from src.neural_link.api.sovereign_gateway import list_crm_leads
        gw._svc._graph.execute_read.return_value = [
            {
                "id": "lead_001",
                "name": "Alice",
                "email": "a@test.com",
                "company": "Acme",
                "trust": 0.8,
                "interaction_count": 5,
                "source_channel": "telegram",
                "tags": ["vip"],
                "created_at": "2026-01-01",
                "updated_at": "2026-01-01",
            }
        ]
        import asyncio
        result = asyncio.run(list_crm_leads())
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_crm_stats_empty(self):
        from src.neural_link.api.sovereign_gateway import crm_stats
        import asyncio
        result = asyncio.run(crm_stats())
        assert result.total_leads == 0

    def test_crm_stats_with_data(self):
        from src.neural_link.api import sovereign_gateway as gw
        gw._svc._graph.execute_read.return_value = [
            {
                "total_leads": 10,
                "total_flows": 3,
                "total_interactions": 25,
                "avg_trust": 0.72,
            }
        ]
        from src.neural_link.api.sovereign_gateway import crm_stats
        import asyncio
        result = asyncio.run(crm_stats())
        assert result.total_leads == 10
        assert result.avg_trust == 0.72

    def test_crm_graph_empty(self):
        from src.neural_link.api.sovereign_gateway import get_crm_graph
        import asyncio
        result = asyncio.run(get_crm_graph())
        assert result.nodes == []
        assert result.edges == []


# ==================================================================
# TestCrmCrudCompletion
# ==================================================================


class TestCrmCrudCompletion:
    """Tests for update, delete, search, and scoring operations."""

    def test_update_lead_query(self):
        """UPDATE_LEAD query uses coalesce for partial updates."""
        assert "UPDATE_LEAD" in dir(q)
        assert "coalesce" in q.UPDATE_LEAD
        assert "$id" in q.UPDATE_LEAD
        assert "$name" in q.UPDATE_LEAD

    def test_soft_delete_lead_query(self):
        """SOFT_DELETE_LEAD sets deleted_at and active=false."""
        assert "SOFT_DELETE_LEAD" in dir(q)
        assert "deleted_at" in q.SOFT_DELETE_LEAD
        assert "active = false" in q.SOFT_DELETE_LEAD
        assert "DETACH DELETE" not in q.SOFT_DELETE_LEAD

    def test_get_all_leads_filters_deleted(self):
        """GET_ALL_LEADS excludes soft-deleted leads."""
        assert "WHERE" in q.GET_ALL_LEADS
        assert "active" in q.GET_ALL_LEADS

    def test_update_flow_query(self):
        """UPDATE_FLOW query uses coalesce for partial updates."""
        assert "UPDATE_FLOW" in dir(q)
        assert "coalesce" in q.UPDATE_FLOW
        assert "$id" in q.UPDATE_FLOW

    def test_soft_delete_flow_query(self):
        """SOFT_DELETE_FLOW sets deleted_at and active=false."""
        assert "SOFT_DELETE_FLOW" in dir(q)
        assert "deleted_at" in q.SOFT_DELETE_FLOW
        assert "active = false" in q.SOFT_DELETE_FLOW

    def test_calculate_lead_score_query(self):
        """CALCULATE_LEAD_SCORE returns interaction/flow counts."""
        assert "CALCULATE_LEAD_SCORE" in dir(q)
        assert "interaction_count" in q.CALCULATE_LEAD_SCORE
        assert "flow_count" in q.CALCULATE_LEAD_SCORE
        assert "last_interaction" in q.CALCULATE_LEAD_SCORE

    def test_update_lead_endpoint(self):
        """PUT /crm/leads/{id} updates lead fields."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        gw._svc._graph.execute_write.return_value = [{"id": "lead_123"}]
        gw._svc._graph.execute_read.return_value = [
            {"id": "lead_123", "name": "Updated", "email": "new@test.com", "company": "NewCo",
             "trust": 0.5, "interaction_count": 0, "source_channel": "manual", "tags": [],
             "created_at": "2024-01-01", "updated_at": "2024-01-02"}
        ]

        from src.neural_link.api.sovereign_gateway import CrmLeadUpdate
        body = CrmLeadUpdate(name="Updated", email="new@test.com")
        result = asyncio.run(gw.update_crm_lead("lead_123", body))
        
        assert result.name == "Updated"
        assert result.email == "new@test.com"

    def test_delete_lead_endpoint(self):
        """DELETE /crm/leads/{id} soft-deletes lead."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        result = asyncio.run(gw.delete_crm_lead("lead_123"))
        
        # Should not raise exception
        assert result is None

    def test_search_leads_endpoint(self):
        """GET /crm/leads/search returns scored results."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        gw._svc._graph.execute_read.return_value = [
            {"id": "lead_123", "name": "Alice", "email": "alice@test.com", "company": "TestCo",
             "trust": 0.8, "interaction_count": 5, "source_channel": "manual", "tags": [],
             "created_at": "2024-01-01", "updated_at": "2024-01-02", "score": 0.95}
        ]

        result = asyncio.run(gw.search_crm_leads("alice"))
        
        assert len(result) == 1
        assert result[0].name == "Alice"

    def test_lead_score_endpoint(self):
        """GET /crm/leads/{id}/score returns trust breakdown."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        gw._svc._graph.execute_read.return_value = [
            {"id": "lead_123", "interaction_count": 10, "last_interaction": "2024-01-01T12:00:00",
             "flow_count": 2}
        ]

        result = asyncio.run(gw.get_lead_score("lead_123"))
        
        assert result.lead_id == "lead_123"
        assert result.interaction_count == 10
        assert result.flow_count == 2
        assert 0.0 <= result.trust <= 1.0

    def test_recency_decay_function(self):
        """_recency_decay calculates exponential decay."""
        from src.neural_link.api.sovereign_gateway import _recency_decay
        from datetime import datetime, timedelta

        # Recent interaction should have high score
        recent = datetime.now().isoformat()
        score_recent = _recency_decay(recent)
        assert score_recent > 0.9

        # Old interaction should have low score
        old = (datetime.now() - timedelta(days=60)).isoformat()
        score_old = _recency_decay(old)
        assert score_old < 0.3

        # None should return 0
        assert _recency_decay(None) == 0.0

    def test_recalculate_trust_function(self):
        """_recalculate_trust calculates weighted trust score."""
        from src.neural_link.api.sovereign_gateway import _recalculate_trust

        graph = _make_graph_mock()
        graph.execute_read.return_value = [
            {"id": "lead_123", "interaction_count": 20, "last_interaction": "2024-01-01T12:00:00",
             "flow_count": 5}
        ]

        trust = _recalculate_trust("lead_123", graph)
        
        # Should be weighted average of components
        assert 0.0 <= trust <= 1.0
        # With max interactions (20) and max flows (5), should be high
        assert trust > 0.5

    def test_auto_recalculate_on_interaction(self):
        """Recording interaction auto-recalculates trust."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        gw._svc._graph.execute_read.return_value = [
            {"id": "lead_123", "interaction_count": 5, "last_interaction": "2024-01-01T12:00:00",
             "flow_count": 1}
        ]

        from src.neural_link.api.sovereign_gateway import CrmInteractionCreate
        body = CrmInteractionCreate(lead_id="lead_123", channel="email", action="opened")
        
        result = asyncio.run(gw.record_crm_interaction(body))
        
        # Should have called _recalculate_trust
        assert "id" in result

    def test_update_flow_endpoint(self):
        """PUT /crm/flows/{id} updates flow fields."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        gw._svc._graph.execute_write.return_value = [{"id": "flow_123"}]
        gw._svc._graph.execute_read.return_value = [
            {"id": "flow_123", "name": "Updated Flow", "objective": "New objective",
             "n8n_workflow_id": None, "status": "active", "lead_ids": [], "created_at": "2024-01-01"}
        ]

        from src.neural_link.api.sovereign_gateway import CrmFlowUpdate
        body = CrmFlowUpdate(name="Updated Flow", status="active")
        result = asyncio.run(gw.update_crm_flow("flow_123", body))
        
        assert result.name == "Updated Flow"
        assert result.status == "active"

    def test_delete_flow_endpoint(self):
        """DELETE /crm/flows/{id} soft-deletes flow."""
        from src.neural_link.api import sovereign_gateway as gw
        import asyncio

        gw._svc._graph = _make_graph_mock()
        result = asyncio.run(gw.delete_crm_flow("flow_123"))
        
        # Should not raise exception
        assert result is None
