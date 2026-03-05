"""
Tests for 5-Layer Optimization Pipeline — Integration tests.

Covers: repeat query uses cache, simple query skips decomposition,
low-score results filtered, cost tracker profiles, adaptive truncation,
and GroqRouter default model.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.orchestrator.core import NeuralLinkOrchestrator, GRAPH_SHORTCUTS
from src.neural_link.orchestrator.pipeline_cache import PipelineCache
from src.neural_link.orchestrator.quality_gate import QualityGate
from src.neural_link.orchestrator.task_decomposer import TaskDecomposer
from src.neural_link.orchestrator.model_tier import select_model, TIER_MODELS, ModelTier
from src.neural_link.telemetry.cost_tracker import CostTracker, RequestCostProfile


# ==================================================================
# TestRepeatQueryCache
# ==================================================================


class TestRepeatQueryCache:
    """Layer 0: Repeat queries resolved via cache."""

    def test_cache_hit_returns_cached_answer(self):
        cache = PipelineCache()
        cache._encoder = False  # disable semantic (no sentence-transformers needed)
        cache.put("what is RAG?", "RAG is Retrieval-Augmented Generation.")

        orch = NeuralLinkOrchestrator(pipeline_cache=cache)
        response = orch.process("what is RAG?")
        assert response.answer == "RAG is Retrieval-Augmented Generation."
        assert response.tasks == []  # No decomposition needed

    def test_second_call_uses_cache(self):
        """process() caches answer, second call returns from cache."""
        cache = PipelineCache()
        cache._encoder = False  # disable semantic

        orch = NeuralLinkOrchestrator(pipeline_cache=cache)

        with patch("src.neural_link.orchestrator.task_decomposer.TaskDecomposer.decompose") as mock_decompose, \
             patch("src.neural_link.orchestrator.task_executor.TaskExecutor.execute") as mock_execute:

            from src.neural_link.orchestrator.models import Task, TaskType, TaskResult
            mock_task = Task(id="t1", description="test", type=TaskType.QUERY, priority=5)
            mock_decompose.return_value = [mock_task]
            mock_execute.return_value = TaskResult(
                task_id="t1", success=True, output="LLM answer", agent_used="test"
            )

            # First call - goes through pipeline
            r1 = orch.process("unique query xyz")

            # Second call - should hit cache
            r2 = orch.process("unique query xyz")
            assert r2.answer == r1.answer
            assert r2.tasks == []  # Cache hit


# ==================================================================
# TestSimpleRequestTriage
# ==================================================================


class TestSimpleRequestTriage:
    """Layer 1: Simple requests skip LLM decomposition."""

    def test_simple_question_is_single_task(self):
        decomposer = TaskDecomposer()
        assert decomposer._is_simple_request("What is RAG?")

    def test_simple_question_pt(self):
        decomposer = TaskDecomposer()
        assert decomposer._is_simple_request("O que e uma campanha?")

    def test_composite_request_not_simple(self):
        decomposer = TaskDecomposer()
        assert not decomposer._is_simple_request(
            "First analyze the metrics and then generate a report"
        )

    def test_composite_pt_not_simple(self):
        decomposer = TaskDecomposer()
        assert not decomposer._is_simple_request(
            "Primeiro analise os dados e depois gere um relatorio"
        )

    def test_numbered_list_not_simple(self):
        decomposer = TaskDecomposer()
        assert not decomposer._is_simple_request(
            "1) Create campaign 2) Set budget 3) Launch"
        )

    def test_short_no_composite_is_simple(self):
        decomposer = TaskDecomposer()
        assert decomposer._is_simple_request("deploy the service")

    def test_single_intent_patterns(self):
        decomposer = TaskDecomposer()
        for q in ["how does it work?", "explain RAG", "list all agents",
                   "show metrics", "get the status", "describe the pipeline"]:
            assert decomposer._is_simple_request(q), f"Expected simple: {q}"


# ==================================================================
# TestAdaptiveTruncation
# ==================================================================


class TestAdaptiveTruncation:
    """Layer 2: Agents apply score-based context filtering."""

    def test_crm_agent_filters_low_scores(self):
        from src.neural_link.agents.crm_domain_agent import CrmBackendAgent

        agent = CrmBackendAgent()

        with patch("src.utils.vector_db.search_with_scores") as mock_search:
            mock_search.return_value = [
                {"content": "relevant", "score": 0.8, "metadata": {"category": "usecase"}},
                {"content": "noise", "score": 0.1, "metadata": {"category": "usecase"}},
            ]
            result = agent._load_usecase_context("test task")
            assert "relevant" in result
            assert "noise" not in result

    def test_sendspeed_agent_filters_low_scores(self):
        from src.neural_link.agents.sendspeed_agent import SendSpeedSmsAgent

        agent = SendSpeedSmsAgent()

        with patch("src.utils.vector_db.search_with_scores") as mock_search:
            mock_search.return_value = [
                {"content": "sms pipeline", "score": 0.7, "metadata": {"category": "usecase"}},
                {"content": "irrelevant", "score": 0.2, "metadata": {"category": "usecase"}},
            ]
            result = agent._load_usecase_context("sms delivery")
            assert "sms pipeline" in result
            assert "irrelevant" not in result

    def test_empty_string_when_no_results(self):
        from src.neural_link.agents.crm_domain_agent import CrmBackendAgent

        agent = CrmBackendAgent()

        with patch("src.utils.vector_db.search_with_scores") as mock_search:
            mock_search.return_value = []
            result = agent._load_usecase_context("test")
            assert result == ""

    def test_adaptive_truncation_higher_score_more_content(self):
        from src.neural_link.agents.crm_domain_agent import CrmBackendAgent

        agent = CrmBackendAgent()
        long_content = "x" * 600

        with patch("src.utils.vector_db.search_with_scores") as mock_search:
            # High score = more content
            mock_search.return_value = [
                {"content": long_content, "score": 1.0, "metadata": {"category": "usecase"}},
            ]
            result_high = agent._load_usecase_context("test")

            mock_search.return_value = [
                {"content": long_content, "score": 0.4, "metadata": {"category": "usecase"}},
            ]
            result_low = agent._load_usecase_context("test")

            assert len(result_high) > len(result_low)


# ==================================================================
# TestCostTracker
# ==================================================================


class TestCostTracker:
    """Cost tracker profiles each request."""

    def test_profile_creation(self):
        tracker = CostTracker()
        profile = tracker.start_request("test-session")
        assert profile.session_id == "test-session"
        assert profile.llm_calls == 0

    def test_record_llm_call(self):
        profile = RequestCostProfile()
        profile.record_llm_call("llama-3.3-70b-versatile", 500, 200)
        assert profile.llm_calls == 1
        assert profile.total_tokens == 700
        assert profile.estimated_cost_usd > 0

    def test_finish_request(self):
        tracker = CostTracker()
        profile = tracker.start_request("s1")
        profile.record_llm_call("llama-3.1-8b-instant", 100, 50)
        tracker.finish_request(profile)
        assert tracker.stats["total_requests"] == 1

    def test_cache_hit_profile(self):
        profile = RequestCostProfile(cache_hit=True)
        assert profile.cache_hit is True
        assert profile.llm_calls == 0
        assert profile.estimated_cost_usd == 0.0

    def test_summary_format(self):
        profile = RequestCostProfile(cache_hit=True, session_id="s1")
        summary = profile.summary()
        assert "cache" in summary
        assert "0 calls" in summary

    def test_graph_shortcut_summary(self):
        profile = RequestCostProfile(graph_shortcut=True)
        assert "graph" in profile.summary()

    def test_aggregate_stats(self):
        tracker = CostTracker()
        for i in range(3):
            p = tracker.start_request(f"s{i}")
            p.record_llm_call("llama-3.1-8b-instant", 100, 50)
            if i == 0:
                p.cache_hit = True
            tracker.finish_request(p)
        stats = tracker.stats
        assert stats["total_requests"] == 3
        assert stats["cache_hit_rate"] == pytest.approx(1 / 3, abs=0.01)


# ==================================================================
# TestGroqRouterDefaultModel
# ==================================================================


class TestGroqRouterDefaultModel:
    """GroqRouter now defaults to 8b for cheaper classification."""

    def test_default_model_is_8b(self):
        from src.middleware.groq_router import GroqRouter

        router = GroqRouter()
        assert "8b" in router.model

    def test_custom_model_override(self):
        from src.middleware.groq_router import GroqRouter

        router = GroqRouter(model="llama-3.3-70b-versatile")
        assert "70b" in router.model


# ==================================================================
# TestGraphShortcutPatterns
# ==================================================================


class TestGraphShortcutPatterns:
    """GRAPH_SHORTCUTS regex patterns match expected queries."""

    def test_patterns_exist(self):
        assert len(GRAPH_SHORTCUTS) >= 3

    def test_list_agents_matches(self):
        import re
        matched = False
        for pattern in GRAPH_SHORTCUTS:
            if re.search(pattern, "list agents"):
                matched = True
                break
        assert matched

    def test_roadmap_matches(self):
        import re
        matched = False
        for pattern in GRAPH_SHORTCUTS:
            if re.search(pattern, "show me the roadmap"):
                matched = True
                break
        assert matched
