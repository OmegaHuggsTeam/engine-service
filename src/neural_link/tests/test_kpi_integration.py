"""
Tests for KPI Intelligence integration — cross-module tests.

Covers KpiProvider lifecycle, EventType.KPI_ANOMALY_DETECTED existence,
RequestCostProfile latency extensions, CostTracker with new fields,
module coexistence without graph, and Pydantic gateway models.
"""

import pytest
import time

from src.neural_link.telemetry.kpi_provider import KpiProvider
from src.neural_link.telemetry.provider import EventType, TelemetryEvent
from src.neural_link.telemetry.cost_tracker import RequestCostProfile, CostTracker
from src.neural_link.telemetry.model_benchmark import ModelBenchmark
from src.neural_link.telemetry.tool_scorecard import ToolScorecard
from src.neural_link.telemetry.cost_quality_analyzer import CostQualityAnalyzer
from src.neural_link.telemetry.metrics_timeseries import MetricsTimeSeries


# ==================================================================
# TestKpiProvider
# ==================================================================


class TestKpiProvider:
    """KpiProvider creation, push/poll lifecycle, and health."""

    def test_provider_id(self):
        kp = KpiProvider()
        assert kp.provider_id == "kpi"

    def test_display_name(self):
        kp = KpiProvider()
        assert kp.display_name == "KPI Intelligence"

    def test_push_anomaly_and_poll(self):
        kp = KpiProvider()
        anomaly = {"type": "quality_regression", "value": "llama-8b", "drop_pct": 25.0}
        kp.push_anomaly(anomaly)
        events = kp.poll()
        assert len(events) == 1
        assert events[0].event_type == EventType.KPI_ANOMALY_DETECTED
        assert "quality_regression" in events[0].message
        assert events[0].data == anomaly

    def test_poll_drains_buffer(self):
        kp = KpiProvider()
        kp.push_anomaly({"type": "test"})
        first_poll = kp.poll()
        assert len(first_poll) == 1
        second_poll = kp.poll()
        assert len(second_poll) == 0

    def test_push_anomalies_multiple(self):
        kp = KpiProvider()
        anomalies = [
            {"type": "quality_regression", "value": "m1"},
            {"type": "latency_regression", "value": "m2"},
            {"type": "quality_regression", "value": "m3"},
        ]
        kp.push_anomalies(anomalies)
        events = kp.poll()
        assert len(events) == 3

    def test_health_check(self):
        kp = KpiProvider()
        assert kp.health_check() is True


# ==================================================================
# TestEventType
# ==================================================================


class TestEventType:
    """EventType enum includes KPI_ANOMALY_DETECTED."""

    def test_kpi_anomaly_detected_exists(self):
        assert hasattr(EventType, "KPI_ANOMALY_DETECTED")
        assert EventType.KPI_ANOMALY_DETECTED.value == "kpi_anomaly_detected"


# ==================================================================
# TestRequestCostProfileLatency
# ==================================================================


class TestRequestCostProfileLatency:
    """RequestCostProfile per_call_latencies and to_request_metric_params."""

    def test_per_call_latencies_default_empty(self):
        p = RequestCostProfile()
        assert p.per_call_latencies == []

    def test_record_llm_call_with_latency(self):
        p = RequestCostProfile()
        p.record_llm_call_with_latency("llama-3.1-8b-instant", input_tokens=100, output_tokens=50, latency_ms=75.0)
        assert len(p.per_call_latencies) == 1
        assert p.per_call_latencies[0] == ("llama-3.1-8b-instant", 75.0)
        assert p.llm_calls == 1
        assert p.total_input_tokens == 100
        assert p.total_output_tokens == 50

    def test_record_llm_call_with_zero_latency_not_added(self):
        p = RequestCostProfile()
        p.record_llm_call_with_latency("test", latency_ms=0.0)
        assert len(p.per_call_latencies) == 0
        assert p.llm_calls == 1  # Call still recorded

    def test_to_request_metric_params_keys(self):
        p = RequestCostProfile(session_id="sess_1")
        p.record_llm_call("llama-3.1-8b-instant", input_tokens=100, output_tokens=50)
        params = p.to_request_metric_params(task_type="generation", agent_used="test_agent", quality_score=8.5)
        expected_keys = {
            "id", "session_id", "model_used", "task_type", "agent_used",
            "input_tokens", "output_tokens", "cost_usd", "latency_ms",
            "quality_score", "layer_reached", "cache_hit", "evaluation_skipped",
            "created_at",
        }
        assert set(params.keys()) == expected_keys
        assert params["session_id"] == "sess_1"
        assert params["model_used"] == "llama-3.1-8b-instant"
        assert params["task_type"] == "generation"
        assert params["agent_used"] == "test_agent"
        assert params["quality_score"] == 8.5


# ==================================================================
# TestCostTrackerWithLatency
# ==================================================================


class TestCostTrackerWithLatency:
    """CostTracker.finish_request works with per_call_latencies."""

    def test_finish_request_with_latency_fields(self):
        tracker = CostTracker()
        profile = tracker.start_request(session_id="test_sess")
        profile.record_llm_call_with_latency("llama-3.1-8b-instant", input_tokens=200, output_tokens=50, latency_ms=80.0)
        tracker.finish_request(profile)
        assert tracker.stats["total_requests"] == 1
        assert profile.per_call_latencies == [("llama-3.1-8b-instant", 80.0)]


# ==================================================================
# TestModuleCoexistence
# ==================================================================


class TestModuleCoexistence:
    """All KPI modules can be instantiated together without graph."""

    def test_all_modules_coexist(self):
        mb = ModelBenchmark(graph_manager=None)
        ts = ToolScorecard(graph_manager=None)
        cqa = CostQualityAnalyzer(graph_manager=None)
        assert mb.buffer_size == 0
        assert ts.get_all_reviews() == []
        assert cqa.get_by_model() == []

    def test_scorecard_submit_and_calculate_pipeline(self):
        ts = ToolScorecard(graph_manager=None)
        result = ts.submit_review(
            tool_name="kiro",
            sprint_date="2026-03-04",
            score_correto=92,
            score_completo=88,
            score_qualidade=95,
        )
        expected_nota = ToolScorecard.calculate_nota_geral(92, 88, 95)
        assert result["nota_geral"] == expected_nota


# ==================================================================
# TestFullPipeline
# ==================================================================


class TestFullPipeline:
    """End-to-end pipeline: CostTracker profile -> MetricsTimeSeries enqueue."""

    def test_profile_to_timeseries_enqueue(self):
        tracker = CostTracker()
        profile = tracker.start_request(session_id="pipeline_test")
        profile.record_llm_call("llama-3.1-8b-instant", input_tokens=300, output_tokens=60)
        tracker.finish_request(profile)

        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue(profile, task_type="query", agent_used="crm_agent")
        assert mts.buffer_size == 1

    def test_profile_to_benchmark_record(self):
        tracker = CostTracker()
        profile = tracker.start_request(session_id="bench_test")
        profile.record_llm_call_with_latency("llama-3.1-8b-instant", input_tokens=100, output_tokens=20, latency_ms=45.0)
        tracker.finish_request(profile)

        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        mb.record_from_profile(profile)
        assert mb.buffer_size == 1


# ==================================================================
# TestSovereignGatewayModels
# ==================================================================


class TestSovereignGatewayModels:
    """Sovereign Gateway KPI Pydantic models."""

    def test_kpi_tool_review_submit_fields(self):
        from src.neural_link.api.sovereign_gateway import KpiToolReviewSubmit
        review = KpiToolReviewSubmit(
            tool_name="kiro",
            sprint_date="2026-03-04",
            score_correto=90,
            score_completo=85,
            score_qualidade=80,
        )
        assert review.tool_name == "kiro"
        assert review.sprint_date == "2026-03-04"
        assert review.score_correto == 90
        assert review.score_completo == 85
        assert review.score_qualidade == 80
        assert review.reviewer == "claude_code"  # default
        assert review.notes == ""  # default

    def test_kpi_tool_review_submit_defaults(self):
        from src.neural_link.api.sovereign_gateway import KpiToolReviewSubmit
        review = KpiToolReviewSubmit(
            tool_name="cursor",
            sprint_date="2026-03-04",
            score_correto=50,
            score_completo=50,
            score_qualidade=50,
        )
        assert review.deliverables_done == 0
        assert review.deliverables_total == 0
        assert review.issues_critical == 0
        assert review.issues_medium == 0
        assert review.issues_low == 0

    def test_kpi_recommend_response_fields(self):
        from src.neural_link.api.sovereign_gateway import KpiRecommendResponse
        resp = KpiRecommendResponse(
            model="llama-3.1-8b-instant",
            avg_quality=8.5,
            total_cost=0.05,
            total_requests=100,
            cost_per_quality_point=0.006,
            reason="Cheapest model with avg quality >= 7.0",
        )
        assert resp.model == "llama-3.1-8b-instant"
        assert resp.avg_quality == 8.5
        assert resp.total_cost == 0.05
        assert resp.total_requests == 100
        assert resp.cost_per_quality_point == 0.006
        assert "Cheapest" in resp.reason

    def test_kpi_recommend_response_defaults(self):
        from src.neural_link.api.sovereign_gateway import KpiRecommendResponse
        resp = KpiRecommendResponse()
        assert resp.model == ""
        assert resp.avg_quality == 0.0
        assert resp.total_cost == 0.0
        assert resp.total_requests == 0
        assert resp.cost_per_quality_point == 0.0
        assert resp.reason == ""
