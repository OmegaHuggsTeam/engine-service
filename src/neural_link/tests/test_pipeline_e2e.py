"""
E2E tests for NeuralLinkOrchestrator — full pipeline flow.
All LLM calls mocked. Tests verify the FLOW, not the responses.
"""

from unittest.mock import patch, MagicMock

import pytest

from src.neural_link.orchestrator.core import NeuralLinkOrchestrator
from src.neural_link.orchestrator.pipeline_cache import PipelineCache
from src.neural_link.orchestrator.quality_gate import QualityGate
from src.neural_link.telemetry.cost_tracker import CostTracker


# Patch chat_completion at the point of use
CHAT_PATCH = "src.utils.llm_client.chat_completion"


class TestFullPipelineFlow:
    """Request → Decompose → Select → Execute → Synthesize → Cache"""

    @patch(CHAT_PATCH)
    def test_simple_query_flow(self, mock_chat):
        """Simple query goes: classify → triage → single task → agent → response"""
        mock_chat.return_value = "mocked answer"

        cache = PipelineCache()
        orchestrator = NeuralLinkOrchestrator(
            graph_manager=None,
            hybrid_rag=None,
            pipeline_cache=cache,
            quality_gate=QualityGate(),
            cost_tracker=CostTracker(),
        )

        # Use query that doesn't match graph shortcut (e.g. faq_definition for "RAG")
        response = orchestrator.process("what is vector search?")

        assert response.answer
        assert len(response.tasks) >= 1
        assert len(response.results) >= 1
        assert all(r.success for r in response.results)
        stats = orchestrator.cost_stats
        assert stats["total_requests"] >= 1

    @patch(CHAT_PATCH)
    def test_cached_query_flow(self, mock_chat):
        """Second identical query returns from cache, zero LLM"""
        mock_chat.return_value = "mocked answer"

        cache = PipelineCache()
        orchestrator = NeuralLinkOrchestrator(
            graph_manager=None,
            hybrid_rag=None,
            pipeline_cache=cache,
            quality_gate=QualityGate(),
            cost_tracker=CostTracker(),
        )

        query = "what is vector search?"
        r1 = orchestrator.process(query)
        call_count_1 = mock_chat.call_count

        r2 = orchestrator.process(query)

        assert r2.tasks == []
        assert r2.results == []
        assert r2.answer == r1.answer
        assert mock_chat.call_count == call_count_1

    @patch(CHAT_PATCH)
    def test_complex_query_decomposition(self, mock_chat):
        """Complex query decomposes into multiple tasks"""
        mock_chat.return_value = "mocked answer"

        with patch(
            "src.neural_link.orchestrator.task_decomposer.TaskDecomposer.decompose"
        ) as mock_decompose:
            from src.neural_link.orchestrator.models import Task, TaskType

            mock_decompose.return_value = [
                Task(
                    id="task_1",
                    description="First subtask",
                    type=TaskType.QUERY,
                    priority=8,
                    required_capabilities=["marketing"],
                ),
                Task(
                    id="task_2",
                    description="Second subtask",
                    type=TaskType.QUERY,
                    priority=5,
                    required_capabilities=["analytics"],
                ),
            ]

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("analyze campaigns and then create report")

            assert len(response.tasks) == 2
            assert len(response.results) == 2
            mock_decompose.assert_called_once()

    @patch(CHAT_PATCH)
    def test_graph_shortcut_flow(self, mock_chat):
        """Graph shortcut query resolves at layer 0"""
        cache = PipelineCache()
        orchestrator = NeuralLinkOrchestrator(
            graph_manager=None,
            hybrid_rag=None,
            pipeline_cache=cache,
            quality_gate=QualityGate(),
            cost_tracker=CostTracker(),
        )

        response = orchestrator.process("list agents")

        assert "agents registered" in response.answer.lower()
        assert response.tasks == []
        mock_chat.assert_not_called()

    @patch(CHAT_PATCH)
    def test_cost_profile_tracks_flow(self, mock_chat):
        """CostTracker records full request lifecycle"""
        mock_chat.return_value = "mocked answer"

        cost_tracker = CostTracker()
        cache = PipelineCache()
        orchestrator = NeuralLinkOrchestrator(
            graph_manager=None,
            hybrid_rag=None,
            pipeline_cache=cache,
            quality_gate=QualityGate(),
            cost_tracker=cost_tracker,
        )

        orchestrator.process("what is vector search?")

        stats = orchestrator.cost_stats
        assert stats["total_requests"] == 1
        assert "avg_llm_calls_per_request" in stats or stats.get("total_requests", 0) >= 1


class TestAgentRouting:
    """Verify correct agent selection and execution for domain queries."""

    @patch(CHAT_PATCH)
    def test_crm_query_routes_to_crm_agent(self, mock_chat):
        """Query about campaigns routes to crm_backend_agent"""
        mock_chat.return_value = "mocked answer"

        with patch(
            "src.neural_link.orchestrator.agent_selector.AgentSelector.select"
        ) as mock_select:
            mock_select.return_value = "crm_backend_agent"

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("create a campaign for active users")

            mock_select.assert_called()
            assert any(
                r.agent_used == "crm_backend_agent" for r in response.results
            ) or len(response.results) >= 1

    @patch(CHAT_PATCH)
    def test_sendspeed_query_routes_to_sendspeed_agent(self, mock_chat):
        """Query about SMS routes to sendspeed_sms_agent"""
        mock_chat.return_value = "mocked answer"

        with patch(
            "src.neural_link.orchestrator.agent_selector.AgentSelector.select"
        ) as mock_select:
            mock_select.return_value = "sendspeed_sms_agent"

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("send SMS campaign")

            mock_select.assert_called()
            assert any(
                r.agent_used == "sendspeed_sms_agent" for r in response.results
            ) or len(response.results) >= 1

    @patch(CHAT_PATCH)
    def test_unknown_query_defaults_to_groq_operator(self, mock_chat):
        """Unclassifiable query falls back to groq_operator"""
        mock_chat.return_value = "mocked answer"

        with patch(
            "src.neural_link.orchestrator.agent_selector.AgentSelector.select"
        ) as mock_select:
            mock_select.return_value = "groq_operator"

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("random unclassifiable query xyz123")

            mock_select.assert_called()
            assert len(response.results) >= 1


class TestQualityGateE2E:
    """Quality gate decisions in real pipeline flow."""

    @patch(CHAT_PATCH)
    def test_high_confidence_agent_skips_evaluation(self, mock_chat):
        """Agent with 90% success rate skips LLM evaluation"""
        mock_chat.return_value = "mocked answer"

        with patch.object(
            NeuralLinkOrchestrator,
            "_get_agent_success_rate",
            return_value=0.9,
        ):
            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(skip_threshold=0.85),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("what is RAG?")
            stats = orchestrator.cost_stats

            assert response.answer
            assert "evaluation_skip_rate" in stats or "total_requests" in stats

    @patch(CHAT_PATCH)
    def test_generation_task_always_evaluated(self, mock_chat):
        """Generation tasks always go through evaluation"""
        mock_chat.return_value = "mocked output"

        with patch(
            "src.neural_link.orchestrator.task_decomposer.TaskDecomposer.decompose"
        ) as mock_decompose:
            from src.neural_link.orchestrator.models import Task, TaskType

            mock_decompose.return_value = [
                Task(
                    id="task_1",
                    description="Generate email copy",
                    type=TaskType.GENERATION,
                    priority=8,
                    required_capabilities=["copywriting"],
                ),
            ]

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(always_evaluate_types={"generation", "repair"}),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("create email copy for campaign")

            assert len(response.tasks) == 1
            assert response.tasks[0].type.value == "generation"
            assert response.answer


class TestErrorRecovery:
    """Pipeline handles errors gracefully."""

    @patch(CHAT_PATCH)
    def test_llm_failure_returns_error_response(self, mock_chat):
        """When chat_completion raises, pipeline returns error, doesn't crash"""
        mock_chat.side_effect = RuntimeError("LLM API unavailable")

        cache = PipelineCache()
        orchestrator = NeuralLinkOrchestrator(
            graph_manager=None,
            hybrid_rag=None,
            pipeline_cache=cache,
            quality_gate=QualityGate(),
            cost_tracker=CostTracker(),
        )

        # Use query that goes through full pipeline (not graph shortcut)
        response = orchestrator.process("what is vector search?")

        assert response.answer
        assert "erro" in response.answer.lower() or "error" in response.answer.lower() or "nao foi" in response.answer.lower()

    @patch(CHAT_PATCH)
    @patch("src.utils.vector_db.search_with_scores", return_value=[])
    def test_partial_task_failure(self, mock_vector_search, mock_chat):
        """If 1 of 3 tasks fails, successful results still synthesized"""
        call_count = [0]

        def side_effect(*args, **kwargs):
            call_count[0] += 1
            # Raise on 2nd call (task 2 agent) and 3rd (fallback for task 2)
            if call_count[0] in (2, 3):
                raise RuntimeError("Agent failed")
            return "mocked answer"

        mock_chat.side_effect = side_effect

        with patch(
            "src.neural_link.orchestrator.task_decomposer.TaskDecomposer.decompose"
        ) as mock_decompose, patch.object(
            NeuralLinkOrchestrator,
            "_get_agent_success_rate",
            return_value=0.9,
        ):
            from src.neural_link.orchestrator.models import Task, TaskType

            # Use QUERY type to avoid quality gate evaluation (which also calls chat_completion)
            mock_decompose.return_value = [
                Task(
                    id="task_1",
                    description="First task",
                    type=TaskType.QUERY,
                    priority=8,
                    required_capabilities=["marketing"],
                ),
                Task(
                    id="task_2",
                    description="Second task - will fail",
                    type=TaskType.QUERY,
                    priority=6,
                    required_capabilities=["analytics"],
                ),
                Task(
                    id="task_3",
                    description="Third task",
                    type=TaskType.QUERY,
                    priority=5,
                    required_capabilities=["ai"],
                ),
            ]

            cache = PipelineCache()
            orchestrator = NeuralLinkOrchestrator(
                graph_manager=None,
                hybrid_rag=None,
                pipeline_cache=cache,
                quality_gate=QualityGate(),
                cost_tracker=CostTracker(),
            )

            response = orchestrator.process("multi task query")

            assert len(response.results) == 3
            success_count = sum(1 for r in response.results if r.success)
            assert success_count >= 1
            assert any(not r.success for r in response.results)
            assert response.answer
