"""
Tests for QualityGate — Layer 4: Smart evaluation decisions.

Covers should_evaluate with various success rates, always-evaluate types,
sampling distribution, and stats tracking.
"""

import pytest

from src.neural_link.orchestrator.quality_gate import QualityGate


# ==================================================================
# TestShouldEvaluate
# ==================================================================


class TestShouldEvaluate:
    """QualityGate.should_evaluate logic."""

    def test_always_evaluate_generation(self):
        gate = QualityGate()
        assert gate.should_evaluate(
            task_type="generation",
            success=True,
            agent_success_rate=0.99,
        ) is True

    def test_always_evaluate_repair(self):
        gate = QualityGate()
        assert gate.should_evaluate(
            task_type="repair",
            success=True,
            agent_success_rate=0.99,
        ) is True

    def test_skip_high_success_rate_query(self):
        gate = QualityGate(skip_threshold=0.85, sample_rate=0.0)
        assert gate.should_evaluate(
            task_type="query",
            success=True,
            agent_success_rate=0.90,
        ) is False

    def test_skip_high_success_rate_automation(self):
        gate = QualityGate(skip_threshold=0.85, sample_rate=0.0)
        assert gate.should_evaluate(
            task_type="automation",
            success=True,
            agent_success_rate=0.95,
        ) is False

    def test_failed_tasks_never_evaluated(self):
        gate = QualityGate()
        assert gate.should_evaluate(
            task_type="generation",
            success=False,
            agent_success_rate=0.5,
        ) is False

    def test_medium_rate_uses_sampling(self):
        """With sample_rate=1.0, medium confidence should always evaluate."""
        gate = QualityGate(skip_threshold=0.85, sample_rate=1.0)
        assert gate.should_evaluate(
            task_type="query",
            success=True,
            agent_success_rate=0.5,
        ) is True

    def test_medium_rate_zero_sampling(self):
        """With sample_rate=0.0, medium confidence should never evaluate."""
        gate = QualityGate(skip_threshold=0.85, sample_rate=0.0)
        assert gate.should_evaluate(
            task_type="query",
            success=True,
            agent_success_rate=0.5,
        ) is False


# ==================================================================
# TestStats
# ==================================================================


class TestQualityGateStats:
    """QualityGate statistics tracking."""

    def test_stats_initial(self):
        gate = QualityGate()
        assert gate.stats["total_decisions"] == 0
        assert gate.stats["skipped"] == 0

    def test_stats_after_decisions(self):
        gate = QualityGate(skip_threshold=0.85, sample_rate=0.0)
        gate.should_evaluate("query", True, 0.90)  # skip
        gate.should_evaluate("generation", True, 0.90)  # always eval
        gate.should_evaluate("query", False, 0.5)  # skip (failed)
        stats = gate.stats
        assert stats["total_decisions"] == 3
        assert stats["skipped"] == 2  # query skip + failed skip

    def test_skip_rate(self):
        gate = QualityGate(skip_threshold=0.85, sample_rate=0.0)
        gate.should_evaluate("query", True, 0.90)  # skip
        gate.should_evaluate("query", True, 0.90)  # skip
        gate.should_evaluate("generation", True, 0.90)  # eval
        assert gate.stats["skip_rate"] == pytest.approx(2.0 / 3.0, abs=0.01)


# ==================================================================
# TestCustomConfig
# ==================================================================


class TestCustomConfig:
    """QualityGate with custom configuration."""

    def test_custom_always_evaluate_types(self):
        gate = QualityGate(always_evaluate_types={"analysis"})
        assert gate.should_evaluate("analysis", True, 0.99) is True
        # "generation" not in custom set, high rate, sample=0 → skip
        gate2 = QualityGate(
            always_evaluate_types={"analysis"},
            skip_threshold=0.85,
            sample_rate=0.0,
        )
        assert gate2.should_evaluate("generation", True, 0.99) is False

    def test_low_skip_threshold(self):
        gate = QualityGate(skip_threshold=0.50, sample_rate=0.0)
        assert gate.should_evaluate("query", True, 0.55) is False
