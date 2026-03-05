"""
QualityGate - Smart evaluation decision logic.

Instead of evaluating 100% of task results, decides based on:
- Agent success rate (high confidence → skip)
- Sampling rate (medium confidence → evaluate 30%)
- Task type (generation/repair → always evaluate)
"""

import logging
import random

logger = logging.getLogger(__name__)


class QualityGate:
    """Decides whether a task result needs LLM evaluation."""

    def __init__(
        self,
        skip_threshold: float = 0.85,
        sample_rate: float = 0.3,
        always_evaluate_types: set[str] | None = None,
    ):
        """
        Args:
            skip_threshold: Agent success rate above this → skip evaluation.
            sample_rate: For medium confidence, probability of evaluating (0.0-1.0).
            always_evaluate_types: Task types that always get evaluated.
        """
        self._skip_threshold = skip_threshold
        self._sample_rate = sample_rate
        self._always_evaluate = always_evaluate_types or {"generation", "repair"}
        self._total_decisions = 0
        self._skipped = 0

    @property
    def skip_rate(self) -> float:
        """Percentage of evaluations skipped."""
        return self._skipped / self._total_decisions if self._total_decisions > 0 else 0.0

    @property
    def stats(self) -> dict:
        return {
            "total_decisions": self._total_decisions,
            "skipped": self._skipped,
            "evaluated": self._total_decisions - self._skipped,
            "skip_rate": round(self.skip_rate, 3),
        }

    def should_evaluate(
        self,
        task_type: str,
        success: bool,
        agent_success_rate: float = 0.5,
    ) -> bool:
        """
        Determine if this result needs LLM evaluation.

        Args:
            task_type: Task type string (query, generation, repair, etc.)
            success: Whether the task execution succeeded.
            agent_success_rate: Rolling average success rate of the agent (0.0-1.0).

        Returns:
            True if evaluation should be performed.
        """
        self._total_decisions += 1

        # Failed tasks don't need quality evaluation
        if not success:
            self._skipped += 1
            return False

        # Always evaluate generation and repair tasks
        if task_type in self._always_evaluate:
            logger.debug("Quality gate: EVALUATE (always-evaluate type: %s)", task_type)
            return True

        # High-confidence agent → skip evaluation
        if agent_success_rate >= self._skip_threshold:
            self._skipped += 1
            logger.debug(
                "Quality gate: SKIP (agent rate %.2f >= threshold %.2f)",
                agent_success_rate,
                self._skip_threshold,
            )
            return False

        # Medium confidence → sample
        should = random.random() < self._sample_rate
        if not should:
            self._skipped += 1
            logger.debug("Quality gate: SKIP (sampling, rate=%.2f)", self._sample_rate)
        else:
            logger.debug("Quality gate: EVALUATE (sampling hit)")
        return should
