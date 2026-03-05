"""
Tests for CRM Domain Agents — base class and 4 thin subclasses.

All LLM and vector_db calls are mocked — no external dependencies required.
Follows test_graph_sync.py conventions.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.agents.crm_domain_agent import (
    CrmDomainAgent,
    CrmBackendAgent,
    CrmFrontendAgent,
    CrmDataAgent,
    CrmIntegrationAgent,
)


# ==================================================================
# TestCrmDomainAgentInit
# ==================================================================


class TestCrmDomainAgentInit:
    """CrmDomainAgent initialization and properties."""

    def test_init_sets_domain(self):
        agent = CrmBackendAgent()
        assert agent._domain == "campaigns"

    def test_init_sets_categories(self):
        agent = CrmBackendAgent()
        assert "crm_backend" in agent._categories
        assert "crm_service" in agent._categories
        assert "crm_model" in agent._categories

    def test_capabilities_property(self):
        agent = CrmBackendAgent()
        caps = agent.capabilities
        assert isinstance(caps, set)
        assert "crm_backend" in caps
        assert "campaigns" in caps

    def test_initial_context_empty(self):
        agent = CrmBackendAgent()
        assert agent._usecase_context == []
        assert agent._code_context == []
        assert agent._graph_context == ""


# ==================================================================
# TestSubclassCapabilities
# ==================================================================


class TestSubclassCapabilities:
    """Each CRM subclass has correct domain and capabilities."""

    def test_backend_agent(self):
        agent = CrmBackendAgent()
        assert agent._domain == "campaigns"
        caps = agent.capabilities
        assert "crm_backend" in caps
        assert "express" in caps
        assert "kafka" in caps

    def test_frontend_agent(self):
        agent = CrmFrontendAgent()
        assert agent._domain == "tracker"
        caps = agent.capabilities
        assert "crm_frontend" in caps
        assert "react" in caps
        assert "react_flow" in caps

    def test_data_agent(self):
        agent = CrmDataAgent()
        assert agent._domain == "segments"
        caps = agent.capabilities
        assert "crm_data" in caps
        assert "clickhouse" in caps
        assert "kafka_workers" in caps

    def test_integration_agent(self):
        agent = CrmIntegrationAgent()
        assert agent._domain == "integrations"
        caps = agent.capabilities
        assert "crm_integration" in caps
        assert "sms" in caps
        assert "email" in caps
        assert "tracker_sdk" in caps


# ==================================================================
# TestBuildPrompt
# ==================================================================


class TestBuildPrompt:
    """_build_prompt constructs 3-layer prompt correctly."""

    def test_prompt_contains_all_layers(self):
        agent = CrmBackendAgent()
        prompt = agent._build_prompt(
            task="Create campaign endpoint",
            usecase_text="UC-CRM-001 spec here",
            code_text="router.post('/campaigns'...)",
            graph_text="Module: CampaignService",
        )
        assert "USE CASE SPECS" in prompt
        assert "UC-CRM-001 spec here" in prompt
        assert "CODE CONTEXT" in prompt
        assert "router.post" in prompt
        assert "GRAPH CONTEXT" in prompt
        assert "CampaignService" in prompt
        assert "TASK" in prompt
        assert "Create campaign endpoint" in prompt

    def test_prompt_includes_domain(self):
        agent = CrmBackendAgent()
        prompt = agent._build_prompt("test", "", "", "")
        assert "campaigns specialist" in prompt

    def test_prompt_includes_truth_boundary(self):
        agent = CrmBackendAgent()
        prompt = agent._build_prompt("test", "", "", "")
        assert "truth boundary" in prompt


# ==================================================================
# TestExecuteWithMocks
# ==================================================================


class TestExecuteWithMocks:
    """CrmDomainAgent.execute with mocked dependencies."""

    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._invoke_llm")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_graph_context")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_code_context")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_usecase_context")
    def test_execute_calls_all_layers(
        self, mock_usecase, mock_code, mock_graph, mock_llm
    ):
        mock_usecase.return_value = "usecase context"
        mock_code.return_value = "code context"
        mock_graph.return_value = "graph context"
        mock_llm.return_value = "LLM response"

        agent = CrmBackendAgent()
        result = agent.execute("Build campaign API")

        mock_usecase.assert_called_once()
        mock_code.assert_called_once()
        mock_graph.assert_called_once()
        mock_llm.assert_called_once()
        assert result == "LLM response"

    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._invoke_llm")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_graph_context")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_code_context")
    @patch("src.neural_link.agents.crm_domain_agent.CrmDomainAgent._load_usecase_context")
    def test_execute_passes_usecase_id(
        self, mock_usecase, mock_code, mock_graph, mock_llm
    ):
        mock_usecase.return_value = ""
        mock_code.return_value = ""
        mock_graph.return_value = ""
        mock_llm.return_value = "ok"

        agent = CrmBackendAgent()
        agent.execute("task", usecase_id="UC-CRM-001")

        # usecase_id is passed through kwargs
        call_args = mock_usecase.call_args
        assert call_args[0][0] == "task"  # first positional arg is task
        assert call_args[0][1] == "UC-CRM-001"  # second is usecase_id


# ==================================================================
# TestLoadUsecaseContext
# ==================================================================


class TestLoadUsecaseContext:
    """_load_usecase_context with mocked vector_db."""

    @patch("src.utils.vector_db.search_with_scores")
    def test_returns_context_from_vector_db(self, mock_search):
        mock_search.return_value = [
            {
                "content": "UseCase UC-CRM-001: Campaign Blast",
                "metadata": {"category": "usecase"},
                "score": 0.85,
            }
        ]
        agent = CrmBackendAgent()
        result = agent._load_usecase_context("campaign task")
        assert "Campaign Blast" in result

    @patch("src.utils.vector_db.search_with_scores", side_effect=Exception("ChromaDB down"))
    def test_returns_empty_on_error(self, mock_search):
        agent = CrmBackendAgent()
        result = agent._load_usecase_context("task")
        assert result == ""


# ==================================================================
# TestLoadCodeContext
# ==================================================================


class TestLoadCodeContext:
    """_load_code_context with mocked vector_db."""

    @patch("src.utils.vector_db.search_with_scores")
    def test_returns_code_chunks(self, mock_search):
        mock_search.return_value = [
            {
                "content": "router.get('/campaigns'...)",
                "metadata": {"category": "crm_backend", "source_file": "crm/campaigns.ts"},
                "score": 0.75,
            }
        ]
        agent = CrmBackendAgent()
        result = agent._load_code_context("campaign routes")
        assert "campaigns" in result

    @patch("src.utils.vector_db.search_with_scores", side_effect=Exception("Error"))
    def test_returns_empty_on_error(self, mock_search):
        agent = CrmBackendAgent()
        result = agent._load_code_context("task")
        assert result == ""


# ==================================================================
# TestLoadGraphContext
# ==================================================================


class TestLoadGraphContext:
    """_load_graph_context with mocked Neo4j."""

    @patch("src.neural_link.graph.manager.GraphManager.from_env")
    def test_returns_unavailable_when_no_connectivity(self, mock_from_env):
        mock_gm = MagicMock()
        mock_gm.verify_connectivity.return_value = False
        mock_from_env.return_value = mock_gm

        agent = CrmBackendAgent()
        result = agent._load_graph_context({})
        assert "unavailable" in result.lower()

    @patch("src.neural_link.graph.manager.GraphManager.from_env", side_effect=Exception("No Neo4j"))
    def test_returns_empty_on_exception(self, mock_from_env):
        agent = CrmBackendAgent()
        result = agent._load_graph_context({})
        assert result == ""
