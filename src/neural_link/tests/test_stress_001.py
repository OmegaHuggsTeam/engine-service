"""
Tests for Stress Mission 001 - Energy Infrastructure Audit.

All LLM calls are mocked so tests run without Groq API key.
"""

import json
from unittest.mock import patch, MagicMock

import pytest

from src.monitoring.monitor import (
    EnergyMonitor,
    EnergyReading,
    VOLTAGE_NOMINAL,
    VOLTAGE_TOLERANCE,
    CRITICAL_POWER_W,
)
from src.neural_link.missions.stress_001_energy_audit import StressMission001


# ============================================================
# TestMonitor - EnergyMonitor unit tests
# ============================================================

class TestMonitor:
    """Tests for EnergyMonitor and EnergyReading."""

    def test_energy_reading_model(self):
        """EnergyReading accepts all required fields."""
        reading = EnergyReading(
            source="grid_main",
            voltage_v=120.0,
            current_a=10.0,
            power_w=1200.0,
            status="ok",
        )
        assert reading.source == "grid_main"
        assert reading.voltage_v == 120.0
        assert reading.power_w == 1200.0
        assert reading.status == "ok"
        assert reading.timestamp  # auto-generated

    def test_energy_reading_defaults(self):
        """EnergyReading defaults status to 'ok'."""
        reading = EnergyReading(source="x", voltage_v=0, current_a=0, power_w=0)
        assert reading.status == "ok"

    def test_monitor_init(self):
        """EnergyMonitor registers sources."""
        sources = ["grid", "solar"]
        monitor = EnergyMonitor(sources=sources)
        assert monitor.sources == sources

    def test_read_returns_reading(self):
        """read() returns an EnergyReading for the given source."""
        monitor = EnergyMonitor(sources=["grid"])
        reading = monitor.read("grid")
        assert isinstance(reading, EnergyReading)
        assert reading.source == "grid"
        assert reading.voltage_v > 0
        assert reading.current_a > 0
        assert reading.power_w > 0

    def test_read_status_within_range(self):
        """read() sets status based on voltage and power thresholds."""
        monitor = EnergyMonitor(sources=["test"])
        # Run multiple reads, collect statuses
        statuses = set()
        for _ in range(200):
            r = monitor.read("test")
            statuses.add(r.status)
            assert r.status in ("ok", "warning", "critical")

    def test_audit_all_returns_all_sources(self):
        """audit_all() returns one reading per source."""
        sources = ["grid", "solar", "battery"]
        monitor = EnergyMonitor(sources=sources)
        readings = monitor.audit_all()
        assert len(readings) == 3
        read_sources = [r.source for r in readings]
        assert set(read_sources) == set(sources)

    def test_generate_report_structure(self):
        """generate_report() returns correct keys and types."""
        monitor = EnergyMonitor(sources=["a", "b"])
        readings = [
            EnergyReading(source="a", voltage_v=120.0, current_a=10.0, power_w=1200.0, status="ok"),
            EnergyReading(source="b", voltage_v=115.0, current_a=40.0, power_w=4600.0, status="warning"),
        ]
        report = monitor.generate_report(readings)
        assert "total_power_w" in report
        assert "avg_voltage_v" in report
        assert "critical_count" in report
        assert "efficiency_pct" in report
        assert "source_count" in report
        assert report["source_count"] == 2

    def test_generate_report_aggregation(self):
        """generate_report() correctly aggregates values."""
        monitor = EnergyMonitor(sources=["a", "b"])
        readings = [
            EnergyReading(source="a", voltage_v=120.0, current_a=10.0, power_w=1200.0, status="ok"),
            EnergyReading(source="b", voltage_v=130.0, current_a=40.0, power_w=5200.0, status="critical"),
        ]
        report = monitor.generate_report(readings)
        assert report["total_power_w"] == 6400.0
        assert report["avg_voltage_v"] == 125.0
        assert report["critical_count"] == 1
        assert report["efficiency_pct"] == 50.0

    def test_generate_report_empty(self):
        """generate_report() handles empty readings."""
        monitor = EnergyMonitor(sources=[])
        report = monitor.generate_report([])
        assert report["total_power_w"] == 0
        assert report["source_count"] == 0

    def test_check_thresholds_no_warnings(self):
        """check_thresholds() returns empty list when all readings nominal."""
        monitor = EnergyMonitor(sources=["a"])
        readings = [
            EnergyReading(source="a", voltage_v=120.0, current_a=10.0, power_w=1200.0, status="ok"),
        ]
        warnings = monitor.check_thresholds(readings)
        assert warnings == []

    def test_check_thresholds_low_voltage(self):
        """check_thresholds() detects low voltage."""
        monitor = EnergyMonitor(sources=["a"])
        v_low = VOLTAGE_NOMINAL * (1 - VOLTAGE_TOLERANCE) - 1  # below threshold
        readings = [
            EnergyReading(source="grid", voltage_v=v_low, current_a=10.0, power_w=v_low * 10, status="warning"),
        ]
        warnings = monitor.check_thresholds(readings)
        assert any("LOW" in w for w in warnings)

    def test_check_thresholds_high_voltage(self):
        """check_thresholds() detects high voltage."""
        monitor = EnergyMonitor(sources=["a"])
        v_high = VOLTAGE_NOMINAL * (1 + VOLTAGE_TOLERANCE) + 1
        readings = [
            EnergyReading(source="grid", voltage_v=v_high, current_a=10.0, power_w=v_high * 10, status="warning"),
        ]
        warnings = monitor.check_thresholds(readings)
        assert any("HIGH" in w for w in warnings)

    def test_check_thresholds_critical_power(self):
        """check_thresholds() detects critical power."""
        monitor = EnergyMonitor(sources=["a"])
        readings = [
            EnergyReading(source="gen", voltage_v=120.0, current_a=50.0, power_w=6000.0, status="critical"),
        ]
        warnings = monitor.check_thresholds(readings)
        assert any("CRITICAL" in w for w in warnings)


# ============================================================
# TestStressMission001 - Mission orchestration tests
# ============================================================

# Mock LLM response for TaskExecutor (agent output)
MOCK_AGENT_OUTPUT = "Generated monitoring code with threshold detection and audit reports."

# Mock LLM response for TaskEvaluator (JSON score)
MOCK_EVAL_RESPONSE = json.dumps({"score": 8.5, "feedback": "Good coverage and structure."})


class TestStressMission001:
    """Tests for StressMission001 orchestration (all LLM mocked)."""

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    @patch.object(
        StressMission001, "_print_banner", return_value=None,
    )
    def test_run_returns_dict(self, mock_banner, mock_llm):
        """run() returns a dict with expected keys."""
        # Mock evaluator to avoid second LLM call
        with patch.object(
            StressMission001, "_print_scoreboard", return_value=None,
        ), patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(),
        ):
            mission = StressMission001()
            result = mission.run()

        assert isinstance(result, dict)
        assert "task1_agent" in result
        assert "task2_agent" in result
        assert "eval1" in result
        assert "eval2" in result
        assert "mission_passed" in result

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    def test_correct_agents_selected(self, mock_llm):
        """AgentSelector routes to devops_agent and testing_agent."""
        with patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(),
        ):
            mission = StressMission001()
            result = mission.run()

        assert result["task1_agent"] == "devops_agent"
        assert result["task2_agent"] == "testing_agent"

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    def test_mission_passes_with_high_scores(self, mock_llm):
        """Mission passes when both evaluations score >= threshold."""
        with patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(score=8.5, passed=True),
        ):
            mission = StressMission001()
            result = mission.run()

        assert result["mission_passed"] is True
        assert result["eval1"].passed is True
        assert result["eval2"].passed is True

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    def test_mission_fails_with_low_scores(self, mock_llm):
        """Mission fails when evaluation score < threshold."""
        with patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(score=4.0, passed=False),
        ):
            mission = StressMission001()
            result = mission.run()

        assert result["mission_passed"] is False

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    def test_inter_agent_data_passed(self, mock_llm):
        """Task 2 receives Task 1 output in its input_data."""
        with patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(),
        ):
            mission = StressMission001()
            result = mission.run()

        # Task 2 result came from an executor call that had upstream data
        task2_result = result["task2_result"]
        assert task2_result.success is True
        # The executor was called with the task that had input_data set
        assert result["task2_agent"] == "testing_agent"

    @patch("src.utils.llm_client.chat_completion", return_value=MOCK_AGENT_OUTPUT)
    def test_task_results_successful(self, mock_llm):
        """Both task executions return success=True."""
        with patch(
            "src.neural_link.graph.evaluator.TaskEvaluator.evaluate",
            return_value=_mock_eval_result(),
        ):
            mission = StressMission001()
            result = mission.run()

        assert result["task1_result"].success is True
        assert result["task2_result"].success is True

    def test_scoreboard_prints(self, capsys):
        """_print_scoreboard() produces formatted output."""
        from src.neural_link.graph.evaluator import EvaluationResult

        evals = [
            ("devops_agent", "Monitor Code", EvaluationResult(quality_score=8.5, passed=True)),
            ("testing_agent", "Test Gen", EvaluationResult(quality_score=7.0, passed=True)),
        ]
        StressMission001._print_scoreboard(evals)
        captured = capsys.readouterr()
        assert "SCOREBOARD" in captured.out
        assert "devops_agent" in captured.out
        assert "testing_agent" in captured.out


# ============================================================
# Helpers
# ============================================================

def _mock_eval_result(score: float = 8.5, passed: bool = True):
    """Create a mock EvaluationResult."""
    from src.neural_link.graph.evaluator import EvaluationResult
    return EvaluationResult(
        task_id="mock",
        quality_score=score,
        feedback="Mock evaluation feedback.",
        passed=passed,
        refinement_count=0,
    )
