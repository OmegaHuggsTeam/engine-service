"""
Tests for the TaskEvaluator scoreboard module.

All chat_completion calls are mocked - no real LLM or Neo4j needed.
"""

import json
import pytest
from unittest.mock import MagicMock, patch, call

from src.neural_link.graph.evaluator import (
    EvaluationResult,
    EvaluationSummary,
    TaskEvaluator,
)
from src.neural_link.orchestrator.models import Task, TaskResult, TaskType, TaskStatus


def _make_task(task_id="task_1", description="Write a summary of AI trends"):
    return Task(id=task_id, description=description, type=TaskType.QUERY)


def _make_result(task_id="task_1", output="AI is evolving rapidly.", success=True, agent="ai_engineer_agent"):
    return TaskResult(task_id=task_id, success=success, output=output, agent_used=agent)


def _llm_eval_response(score=8.5, feedback="Good output"):
    return json.dumps({"score": score, "feedback": feedback})


# ============================================================
# TestEvaluationModels
# ============================================================

class TestEvaluationModels:
    """Tests for EvaluationResult and EvaluationSummary Pydantic models."""

    def test_evaluation_result_defaults(self):
        r = EvaluationResult()
        assert r.task_id == ""
        assert r.quality_score == 0.0
        assert r.feedback == ""
        assert r.passed is False
        assert r.refinement_count == 0
        assert r.refinement_prompt is None

    def test_evaluation_result_with_values(self):
        r = EvaluationResult(
            task_id="t1", quality_score=9.0, feedback="Great",
            passed=True, refinement_count=1, refinement_prompt="Be more specific",
        )
        assert r.task_id == "t1"
        assert r.quality_score == 9.0
        assert r.passed is True
        assert r.refinement_prompt == "Be more specific"

    def test_score_clamped_at_boundaries(self):
        r = EvaluationResult(quality_score=0.0)
        assert r.quality_score == 0.0
        r2 = EvaluationResult(quality_score=10.0)
        assert r2.quality_score == 10.0

    def test_summary_defaults(self):
        s = EvaluationSummary()
        assert s.task_id == ""
        assert s.final_score == 0.0
        assert s.final_output is None
        assert s.total_refinements == 0
        assert s.passed is False
        assert s.history == []

    def test_summary_with_history(self):
        h = [EvaluationResult(task_id="t1", quality_score=5.0)]
        s = EvaluationSummary(task_id="t1", final_score=8.0, history=h, passed=True)
        assert len(s.history) == 1
        assert s.history[0].quality_score == 5.0


# ============================================================
# TestEvaluate
# ============================================================

class TestEvaluate:
    """Tests for TaskEvaluator.evaluate()."""

    @patch("src.utils.llm_client.chat_completion")
    def test_high_score_passes(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=8.5, feedback="Excellent")
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.passed is True
        assert result.quality_score == 8.5
        assert result.feedback == "Excellent"

    @patch("src.utils.llm_client.chat_completion")
    def test_low_score_fails(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=4.0, feedback="Incomplete")
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.passed is False
        assert result.quality_score == 4.0

    @patch("src.utils.llm_client.chat_completion")
    def test_exact_threshold_passes(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=7.0)
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.passed is True

    @patch("src.utils.llm_client.chat_completion")
    def test_persists_to_graph(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=9.0, feedback="Perfect")
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.8}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())
        # Should call execute_write for score persistence + agent success update
        assert graph.execute_write.call_count == 2

    @patch("src.utils.llm_client.chat_completion")
    def test_skips_graph_when_none(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=8.0)
        evaluator = TaskEvaluator(graph_manager=None)
        result = evaluator.evaluate(_make_task(), _make_result())
        # No crash, still returns result
        assert result.quality_score == 8.0

    @patch("src.utils.llm_client.chat_completion")
    def test_updates_agent_success_rate(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=9.0)
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.8}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result(agent="test_agent"))
        # Verify agent success update was called
        write_calls = graph.execute_write.call_args_list
        assert len(write_calls) == 2  # persist_score + update_agent_success

    @patch("src.utils.llm_client.chat_completion")
    def test_handles_llm_parse_failure(self, mock_llm):
        mock_llm.return_value = "not valid json at all"
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 0.0
        assert result.passed is False
        assert "Parse failure" in result.feedback

    @patch("src.utils.llm_client.chat_completion")
    def test_handles_llm_exception(self, mock_llm):
        mock_llm.side_effect = RuntimeError("API down")
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 0.0
        assert result.passed is False

    @patch("src.utils.llm_client.chat_completion")
    def test_strips_markdown_fences(self, mock_llm):
        mock_llm.return_value = '```json\n{"score": 8.0, "feedback": "Good"}\n```'
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 8.0
        assert result.passed is True

    @patch("src.utils.llm_client.chat_completion")
    def test_clamps_out_of_range_score(self, mock_llm):
        mock_llm.return_value = json.dumps({"score": 15.0, "feedback": "Over"})
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 10.0

    @patch("src.utils.llm_client.chat_completion")
    def test_clamps_negative_score(self, mock_llm):
        mock_llm.return_value = json.dumps({"score": -3.0, "feedback": "Neg"})
        evaluator = TaskEvaluator(threshold=7)
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 0.0

    @patch("src.utils.llm_client.chat_completion")
    def test_no_agent_skips_success_update(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=8.0)
        graph = MagicMock()
        result_no_agent = TaskResult(task_id="t1", success=True, output="out", agent_used=None)
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), result_no_agent)
        # Only persist_score, no agent update
        assert graph.execute_write.call_count == 1


# ============================================================
# TestRefinement
# ============================================================

class TestRefinement:
    """Tests for refinement LLM call."""

    @patch("src.utils.llm_client.chat_completion")
    def test_returns_plain_text(self, mock_llm):
        mock_llm.return_value = "Focus more on recent 2025-2026 developments"
        evaluator = TaskEvaluator()
        prompt = evaluator._call_refinement_llm("Write about AI", "Old output", "Too vague")
        assert prompt == "Focus more on recent 2025-2026 developments"

    @patch("src.utils.llm_client.chat_completion")
    def test_prompt_includes_feedback_and_output(self, mock_llm):
        mock_llm.return_value = "Refined instruction"
        evaluator = TaskEvaluator()
        evaluator._call_refinement_llm("task desc", "prev output", "needs detail")
        call_args = mock_llm.call_args[0][0]
        user_msg = call_args[1]["content"]
        assert "prev output" in user_msg
        assert "needs detail" in user_msg
        assert "task desc" in user_msg


# ============================================================
# TestEvaluateAndRefine
# ============================================================

class TestEvaluateAndRefine:
    """Tests for the full evaluate-and-refine loop."""

    @patch("src.utils.llm_client.chat_completion")
    def test_passes_on_first_try(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=9.0, feedback="Great")
        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        executor = MagicMock()
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is True
        assert summary.total_refinements == 0
        assert summary.final_score == 9.0
        assert len(summary.history) == 1
        executor.execute.assert_not_called()

    @patch("src.utils.llm_client.chat_completion")
    def test_retries_once_then_passes(self, mock_llm):
        # First call: evaluation (low score), second: refinement prompt,
        # third: evaluation (high score)
        mock_llm.side_effect = [
            _llm_eval_response(score=4.0, feedback="Incomplete"),
            "Add more detail about transformers",
            _llm_eval_response(score=8.5, feedback="Much better"),
        ]
        executor = MagicMock()
        executor.execute.return_value = _make_result(output="Improved output about transformers")

        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is True
        assert summary.total_refinements == 1
        assert len(summary.history) == 2
        assert executor.execute.call_count == 1

    @patch("src.utils.llm_client.chat_completion")
    def test_exhausts_max_refinements(self, mock_llm):
        # All evaluations return low scores
        mock_llm.side_effect = [
            _llm_eval_response(score=3.0, feedback="Bad"),
            "Try again",
            _llm_eval_response(score=4.0, feedback="Still bad"),
            "Try harder",
            _llm_eval_response(score=5.0, feedback="Not enough"),
        ]
        executor = MagicMock()
        executor.execute.return_value = _make_result(output="Still not great")

        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is False
        assert summary.total_refinements == 2
        assert len(summary.history) == 3
        assert executor.execute.call_count == 2

    @patch("src.utils.llm_client.chat_completion")
    def test_max_refinements_zero_no_retries(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=3.0, feedback="Poor")
        evaluator = TaskEvaluator(threshold=7, max_refinements=0)
        executor = MagicMock()
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is False
        assert summary.total_refinements == 0
        assert len(summary.history) == 1
        executor.execute.assert_not_called()

    @patch("src.utils.llm_client.chat_completion")
    def test_summary_contains_full_history(self, mock_llm):
        mock_llm.side_effect = [
            _llm_eval_response(score=3.0, feedback="V1 bad"),
            "Refine v1",
            _llm_eval_response(score=9.0, feedback="V2 great"),
        ]
        executor = MagicMock()
        executor.execute.return_value = _make_result(output="V2 output")

        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(output="V1 output"), executor, "agent_1"
        )
        assert len(summary.history) == 2
        assert summary.history[0].quality_score == 3.0
        assert summary.history[1].quality_score == 9.0

    @patch("src.utils.llm_client.chat_completion")
    def test_original_task_not_mutated(self, mock_llm):
        mock_llm.side_effect = [
            _llm_eval_response(score=3.0, feedback="Bad"),
            "Refine it",
            _llm_eval_response(score=9.0, feedback="Good"),
        ]
        executor = MagicMock()
        executor.execute.return_value = _make_result(output="Refined")

        task = _make_task(description="Original description")
        original_desc = task.description

        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        evaluator.evaluate_and_refine(task, _make_result(), executor, "agent_1")

        assert task.description == original_desc

    @patch("src.utils.llm_client.chat_completion")
    def test_refinement_llm_failure_stops_loop(self, mock_llm):
        mock_llm.side_effect = [
            _llm_eval_response(score=3.0, feedback="Bad"),
            RuntimeError("Refinement API down"),
        ]
        executor = MagicMock()
        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is False
        assert len(summary.history) == 1
        executor.execute.assert_not_called()

    @patch("src.utils.llm_client.chat_completion")
    def test_executor_failure_stops_loop(self, mock_llm):
        mock_llm.side_effect = [
            _llm_eval_response(score=3.0, feedback="Bad"),
            "Refine it",
        ]
        executor = MagicMock()
        executor.execute.side_effect = RuntimeError("Agent crashed")

        evaluator = TaskEvaluator(threshold=7, max_refinements=2)
        summary = evaluator.evaluate_and_refine(
            _make_task(), _make_result(), executor, "agent_1"
        )
        assert summary.passed is False
        assert len(summary.history) == 1


# ============================================================
# TestScorePersistence
# ============================================================

class TestScorePersistence:
    """Tests for Neo4j score persistence."""

    @patch("src.utils.llm_client.chat_completion")
    def test_correct_cypher_params(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=7.5, feedback="Decent")
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.9}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(task_id="task_42"), _make_result(task_id="task_42"))

        # First write call is persist_score
        persist_call = graph.execute_write.call_args_list[0]
        params = persist_call[0][1]
        assert params["task_id"] == "task_42"
        assert params["quality_score"] == 7.5
        assert params["evaluation_feedback"] == "Decent"
        assert params["refinement_count"] == 0

    @patch("src.utils.llm_client.chat_completion")
    def test_graph_failure_doesnt_crash(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=8.0)
        graph = MagicMock()
        graph.execute_write.side_effect = RuntimeError("Neo4j down")
        graph.execute_read.side_effect = RuntimeError("Neo4j down")
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        # Should not raise
        result = evaluator.evaluate(_make_task(), _make_result())
        assert result.quality_score == 8.0

    @patch("src.utils.llm_client.chat_completion")
    def test_feedback_truncated_to_500(self, mock_llm):
        long_feedback = "x" * 600
        mock_llm.return_value = json.dumps({"score": 5.0, "feedback": long_feedback})
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.8}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())
        persist_call = graph.execute_write.call_args_list[0]
        assert len(persist_call[0][1]["evaluation_feedback"]) <= 500


# ============================================================
# TestAgentSuccessIntegration
# ============================================================

class TestAgentSuccessIntegration:
    """Tests for agent success rate updates via rolling average."""

    @patch("src.utils.llm_client.chat_completion")
    def test_high_score_increases_rate(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=9.0)
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.6}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())

        # agent update is second write call
        agent_call = graph.execute_write.call_args_list[1]
        new_rate = agent_call[0][1]["success_rate"]
        # 0.6 * 0.8 + 1.0 * 0.2 = 0.48 + 0.2 = 0.68
        assert abs(new_rate - 0.68) < 0.001

    @patch("src.utils.llm_client.chat_completion")
    def test_low_score_decreases_rate(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=3.0)
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.9}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())

        agent_call = graph.execute_write.call_args_list[1]
        new_rate = agent_call[0][1]["success_rate"]
        # 0.9 * 0.8 + 0.0 * 0.2 = 0.72
        assert abs(new_rate - 0.72) < 0.001

    @patch("src.utils.llm_client.chat_completion")
    def test_rolling_average_formula(self, mock_llm):
        """Verify: new_rate = current * 0.8 + session * 0.2"""
        mock_llm.return_value = _llm_eval_response(score=7.0)  # exactly threshold
        graph = MagicMock()
        graph.execute_read.return_value = [{"rate": 0.5}]
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())

        agent_call = graph.execute_write.call_args_list[1]
        new_rate = agent_call[0][1]["success_rate"]
        # score=7 >= threshold=7 -> session_rate=1.0
        # 0.5 * 0.8 + 1.0 * 0.2 = 0.4 + 0.2 = 0.6
        assert abs(new_rate - 0.6) < 0.001

    @patch("src.utils.llm_client.chat_completion")
    def test_default_rate_when_agent_not_found(self, mock_llm):
        mock_llm.return_value = _llm_eval_response(score=8.0)
        graph = MagicMock()
        graph.execute_read.return_value = []  # no agent found
        evaluator = TaskEvaluator(graph_manager=graph, threshold=7)
        evaluator.evaluate(_make_task(), _make_result())

        agent_call = graph.execute_write.call_args_list[1]
        new_rate = agent_call[0][1]["success_rate"]
        # default 0.8 * 0.8 + 1.0 * 0.2 = 0.64 + 0.2 = 0.84
        assert abs(new_rate - 0.84) < 0.001
