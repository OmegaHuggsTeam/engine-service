"""
TaskEvaluator - Scoreboard module for agent output quality assessment.

Scores each agent output (0-10) against the task spec via Groq LLM,
persists the score to Neo4j, and auto-retries low-scoring tasks with
a refinement prompt. Hard cap (max_refinements=2) prevents infinite loops.
"""

import json
import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ============================================================
# Models
# ============================================================

class EvaluationResult(BaseModel):
    """Single evaluation pass result."""
    task_id: str = ""
    quality_score: float = Field(default=0.0, ge=0.0, le=10.0)
    feedback: str = ""
    passed: bool = False
    refinement_count: int = 0
    refinement_prompt: Optional[str] = None


class EvaluationSummary(BaseModel):
    """Full evaluate-and-refine cycle summary."""
    task_id: str = ""
    final_score: float = 0.0
    final_output: Any = None
    total_refinements: int = 0
    passed: bool = False
    history: list[EvaluationResult] = Field(default_factory=list)


# ============================================================
# Prompts
# ============================================================

EVALUATION_SYSTEM_PROMPT = (
    "You are a strict quality evaluator. Score the agent output against the task specification.\n"
    "\n"
    "Evaluate on 4 axes (each 0-2.5 points, total 0-10):\n"
    "1. Completeness - Does the output address all parts of the task?\n"
    "2. Accuracy - Is the information correct and relevant?\n"
    "3. Clarity - Is the output well-structured and easy to understand?\n"
    "4. Actionability - Can the user act on this output directly?\n"
    "\n"
    "Respond with pure JSON (no markdown fences):\n"
    '{"score": <0-10 float>, "feedback": "<concise critique>"}'
)

REFINEMENT_SYSTEM_PROMPT = (
    "You are a task refinement assistant. Given the original task, the previous output, "
    "and evaluator feedback with score, produce a refined instruction that addresses the "
    "feedback. Output only the refined instruction as plain text, no JSON."
)


# ============================================================
# TaskEvaluator
# ============================================================

class TaskEvaluator:
    """
    Quality gate for agent outputs.

    Scores outputs via Groq LLM, persists to Neo4j, and optionally
    retries low-scoring tasks with refinement prompts.
    """

    def __init__(self, graph_manager=None, threshold: float = 7, max_refinements: int = 2):
        self._graph = graph_manager
        self._threshold = threshold
        self._max_refinements = max_refinements

    def evaluate(self, task, result) -> EvaluationResult:
        """
        Score a single task result against its spec.

        Args:
            task: Task model with description and input_data
            result: TaskResult model with output

        Returns:
            EvaluationResult with score, feedback, and pass/fail
        """
        description = task.description
        input_data = str(task.input_data) if task.input_data else ""
        output = str(result.output) if result.output else ""

        try:
            parsed = self._call_evaluation_llm(description, input_data, output)
            score = parsed["score"]
            feedback = parsed["feedback"]
        except Exception as e:
            logger.warning(f"Evaluation LLM failed for task {task.id}: {e}")
            score = 0.0
            feedback = f"Evaluation failed: {e}"

        passed = score >= self._threshold

        eval_result = EvaluationResult(
            task_id=task.id,
            quality_score=score,
            feedback=feedback,
            passed=passed,
            refinement_count=0,
            refinement_prompt=None,
        )

        # Persist to Neo4j
        self._persist_score(task.id, score, feedback, 0)

        # Update agent success rate
        if result.agent_used:
            self._update_agent_success(result.agent_used, score)

        return eval_result

    def evaluate_and_refine(self, task, result, executor, agent_id) -> EvaluationSummary:
        """
        Full evaluate-refine loop.

        Evaluates the result; if score < threshold and retries remain,
        generates a refinement prompt, re-executes, and loops.

        Args:
            task: Task model
            result: Initial TaskResult
            executor: TaskExecutor instance for re-execution
            agent_id: Agent to use for re-execution

        Returns:
            EvaluationSummary with final output and full history
        """
        history = []
        current_result = result
        current_output = result.output

        for attempt in range(self._max_refinements + 1):
            # Evaluate current output
            eval_result = self.evaluate(task, current_result)
            eval_result.refinement_count = attempt
            history.append(eval_result)

            if eval_result.passed or attempt >= self._max_refinements:
                break

            # Generate refinement prompt
            try:
                refinement_prompt = self._call_refinement_llm(
                    task.description,
                    str(current_output),
                    eval_result.feedback,
                )
                eval_result.refinement_prompt = refinement_prompt
            except Exception as e:
                logger.warning(f"Refinement LLM failed for task {task.id}: {e}")
                break

            # Re-execute with enriched task description
            from ..orchestrator.models import Task as TaskModel
            refined_task = TaskModel(
                id=task.id,
                description=f"{task.description}\n\nRefinement instruction: {refinement_prompt}",
                type=task.type,
                priority=task.priority,
                required_capabilities=task.required_capabilities,
                input_data=task.input_data,
                status=task.status,
            )

            try:
                current_result = executor.execute(refined_task, agent_id)
                current_output = current_result.output
            except Exception as e:
                logger.warning(f"Re-execution failed for task {task.id}: {e}")
                break

        last_eval = history[-1] if history else EvaluationResult(task_id=task.id)

        return EvaluationSummary(
            task_id=task.id,
            final_score=last_eval.quality_score,
            final_output=current_output,
            total_refinements=len(history) - 1,
            passed=last_eval.passed,
            history=history,
        )

    def _call_evaluation_llm(self, description: str, input_data: str, output: str) -> dict:
        """Build eval prompt, call chat_completion, parse JSON response."""
        from src.utils.llm_client import chat_completion

        user_content = (
            f"Task description: {description}\n"
            f"Task input: {input_data}\n"
            f"Agent output:\n{output}"
        )

        raw = chat_completion([
            {"role": "system", "content": EVALUATION_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ])

        return self._parse_evaluation(raw)

    def _call_refinement_llm(self, description: str, output: str, feedback: str) -> str:
        """Build refinement prompt, call chat_completion, return plain text instruction."""
        from src.utils.llm_client import chat_completion

        user_content = (
            f"Original task: {description}\n\n"
            f"Previous output:\n{output}\n\n"
            f"Evaluator feedback: {feedback}"
        )

        return chat_completion([
            {"role": "system", "content": REFINEMENT_SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ])

    @staticmethod
    def _parse_evaluation(raw: str) -> dict:
        """
        Parse JSON evaluation response.

        Strips markdown fences, clamps score to [0, 10].
        Falls back to score=0 on parse failure.
        """
        try:
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                lines = cleaned.split("\n")
                lines = [l for l in lines if not l.strip().startswith("```")]
                cleaned = "\n".join(lines).strip()

            data = json.loads(cleaned)

            score = float(data.get("score", 0))
            score = max(0.0, min(10.0, score))

            feedback = str(data.get("feedback", ""))

            return {"score": score, "feedback": feedback}

        except (json.JSONDecodeError, KeyError, TypeError, ValueError) as e:
            logger.warning(f"Evaluation parse failed ({e}), defaulting to score=0")
            return {"score": 0.0, "feedback": f"Parse failure: {e}"}

    def _persist_score(self, task_id: str, score: float, feedback: str, refinement_count: int):
        """Write evaluation score to Neo4j. Silent skip if graph unavailable."""
        if not self._graph:
            return

        try:
            from . import queries
            self._graph.execute_write(queries.UPDATE_TASK_QUALITY_SCORE, {
                "task_id": task_id,
                "quality_score": score,
                "evaluation_feedback": feedback[:500],
                "refinement_count": refinement_count,
            })
        except Exception as e:
            logger.debug(f"Failed to persist evaluation score: {e}")

    def _update_agent_success(self, agent_id: str, score: float):
        """
        Update agent success rate using rolling average (0.8/0.2).

        Maps score >= threshold to 1.0, else 0.0.
        """
        if not self._graph:
            return

        try:
            from . import queries

            # Read current rate
            rows = self._graph.execute_read(
                "MATCH (a:Agent {id: $id}) RETURN a.success_rate AS rate",
                {"id": agent_id},
            )
            current_rate = float(rows[0]["rate"]) if rows and rows[0].get("rate") else 0.8

            # Map score to binary outcome
            session_rate = 1.0 if score >= self._threshold else 0.0

            # Rolling average: 80% historic + 20% new
            new_rate = current_rate * 0.8 + session_rate * 0.2

            self._graph.execute_write(queries.UPDATE_AGENT_SUCCESS_RATE, {
                "agent_id": agent_id,
                "success_rate": new_rate,
            })
        except Exception as e:
            logger.debug(f"Failed to update agent success rate for {agent_id}: {e}")
