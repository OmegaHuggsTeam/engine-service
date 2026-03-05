"""
Tests for MetricsTimeSeries — Time-series persistence and aggregation for KPI Intelligence.

Covers enqueue buffer mechanics, flush behavior, _compute_aggregate,
graph-less query fallbacks, and detect_anomalies regression detection.
"""

import pytest

from src.neural_link.telemetry.metrics_timeseries import MetricsTimeSeries


# ==================================================================
# Mock profile that implements to_request_metric_params
# ==================================================================


class MockProfile:
    """Mimics RequestCostProfile for testing enqueue."""

    def to_request_metric_params(self, **kw):
        return {
            "id": "rm_test",
            "session_id": "s1",
            "model_used": "test",
            "task_type": kw.get("task_type", "unknown"),
            "agent_used": kw.get("agent_used", ""),
            "input_tokens": 10,
            "output_tokens": 5,
            "cost_usd": 0.001,
            "latency_ms": 50.0,
            "quality_score": kw.get("quality_score", None),
            "layer_reached": 2,
            "cache_hit": False,
            "evaluation_skipped": False,
            "created_at": "2026-03-04T10:00:00",
        }


# ==================================================================
# TestEnqueue
# ==================================================================


class TestEnqueue:
    """MetricsTimeSeries.enqueue buffer mechanics."""

    def test_enqueue_adds_to_buffer(self):
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue(MockProfile())
        assert mts.buffer_size == 1

    def test_enqueue_multiple(self):
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        for _ in range(5):
            mts.enqueue(MockProfile())
        assert mts.buffer_size == 5

    def test_enqueue_auto_flush_at_threshold(self):
        """Buffer is cleared when threshold is reached (no graph = discarded)."""
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=3)
        for _ in range(3):
            mts.enqueue(MockProfile())
        # Auto-flush should have cleared buffer
        assert mts.buffer_size == 0

    def test_enqueue_ignores_invalid_profile(self):
        """Profile without to_request_metric_params is silently skipped."""
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue("not_a_profile")
        assert mts.buffer_size == 0

    def test_enqueue_passes_kwargs(self):
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue(MockProfile(), task_type="generation", agent_used="test_agent", quality_score=8.5)
        assert mts.buffer_size == 1


# ==================================================================
# TestFlush
# ==================================================================


class TestFlush:
    """MetricsTimeSeries.flush behavior."""

    def test_flush_no_graph_returns_zero(self):
        mts = MetricsTimeSeries(graph_manager=None)
        mts.enqueue(MockProfile())
        result = mts.flush()
        assert result == 0

    def test_flush_clears_buffer(self):
        mts = MetricsTimeSeries(graph_manager=None)
        mts.enqueue(MockProfile())
        mts.enqueue(MockProfile())
        mts.flush()
        assert mts.buffer_size == 0

    def test_flush_empty_buffer(self):
        mts = MetricsTimeSeries(graph_manager=None)
        result = mts.flush()
        assert result == 0


# ==================================================================
# TestBufferSize
# ==================================================================


class TestBufferSize:
    """MetricsTimeSeries.buffer_size property."""

    def test_initial_zero(self):
        mts = MetricsTimeSeries(graph_manager=None)
        assert mts.buffer_size == 0

    def test_after_enqueue(self):
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue(MockProfile())
        mts.enqueue(MockProfile())
        assert mts.buffer_size == 2

    def test_after_flush(self):
        mts = MetricsTimeSeries(graph_manager=None, flush_threshold=100)
        mts.enqueue(MockProfile())
        mts.flush()
        assert mts.buffer_size == 0


# ==================================================================
# TestComputeAggregate
# ==================================================================


class TestComputeAggregate:
    """MetricsTimeSeries._compute_aggregate static method."""

    def test_correct_id_format(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": 8.0, "latency_ms": 100.0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "llama-8b", rows)
        assert result["id"] == "da_model_llama-8b_2026-03-04"

    def test_quality_avg(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": 7.0, "latency_ms": 100.0, "cache_hit": False},
            {"cost_usd": 0.02, "quality_score": 9.0, "latency_ms": 200.0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["avg_quality"] == pytest.approx(8.0, rel=1e-4)

    def test_latency_avg(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 100.0, "cache_hit": False},
            {"cost_usd": 0.02, "quality_score": None, "latency_ms": 300.0, "cache_hit": True},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["avg_latency_ms"] == pytest.approx(200.0, rel=1e-4)

    def test_cache_hit_rate(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": True},
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": True},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["cache_hit_rate"] == pytest.approx(2 / 3, abs=0.001)

    def test_no_quality_data_returns_none(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 100.0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["avg_quality"] is None

    def test_no_latency_data_returns_zero(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": 8.0, "latency_ms": 0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["avg_latency_ms"] == 0.0

    def test_total_cost(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
            {"cost_usd": 0.02, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["total_cost_usd"] == pytest.approx(0.03, rel=1e-4)

    def test_total_requests(self):
        rows = [
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
            {"cost_usd": 0.01, "quality_score": None, "latency_ms": 10.0, "cache_hit": False},
        ]
        result = MetricsTimeSeries._compute_aggregate("2026-03-04", "model", "test", rows)
        assert result["total_requests"] == 3


# ==================================================================
# TestQueryMethods
# ==================================================================


class TestQueryMethods:
    """MetricsTimeSeries query methods with no graph."""

    def test_get_trends_no_graph(self):
        mts = MetricsTimeSeries(graph_manager=None)
        assert mts.get_trends() == []

    def test_get_value_trends_no_graph(self):
        mts = MetricsTimeSeries(graph_manager=None)
        assert mts.get_value_trends("model", "llama-8b") == []

    def test_detect_anomalies_no_graph(self):
        mts = MetricsTimeSeries(graph_manager=None)
        assert mts.detect_anomalies() == []


# ==================================================================
# TestDetectAnomalies
# ==================================================================


class TestDetectAnomalies:
    """MetricsTimeSeries.detect_anomalies regression detection logic."""

    def _make_graph(self, rows):
        """Create a mock graph that returns the given rows."""

        class MockGraph:
            def __init__(self, data):
                self._data = data

            def execute_read(self, query, params=None):
                return self._data

        return MockGraph(rows)

    def test_quality_regression_detected(self):
        """Quality drop >20% should be flagged."""
        # Recent: quality=6.0, Historical: quality=8.0 => drop = (8-6)/8 = 25%
        rows = [
            {"dimension_value": "llama-8b", "date": "2026-03-04", "avg_quality": 6.0, "avg_latency_ms": 100.0},
            {"dimension_value": "llama-8b", "date": "2026-03-03", "avg_quality": 6.0, "avg_latency_ms": 100.0},
            # Historical (past window)
            {"dimension_value": "llama-8b", "date": "2026-02-20", "avg_quality": 8.0, "avg_latency_ms": 100.0},
            {"dimension_value": "llama-8b", "date": "2026-02-19", "avg_quality": 8.0, "avg_latency_ms": 100.0},
        ]
        # window_days=2 => recent=[03-04, 03-03], historical=[02-20, 02-19]
        mts = MetricsTimeSeries(graph_manager=self._make_graph(rows))
        anomalies = mts.detect_anomalies(window_days=2)
        types = [a["type"] for a in anomalies]
        assert "quality_regression" in types

    def test_latency_regression_detected(self):
        """Latency increase >50% should be flagged."""
        rows = [
            {"dimension_value": "llama-8b", "date": "2026-03-04", "avg_quality": None, "avg_latency_ms": 200.0},
            # Historical
            {"dimension_value": "llama-8b", "date": "2026-02-20", "avg_quality": None, "avg_latency_ms": 100.0},
        ]
        mts = MetricsTimeSeries(graph_manager=self._make_graph(rows))
        anomalies = mts.detect_anomalies(window_days=1)
        types = [a["type"] for a in anomalies]
        assert "latency_regression" in types

    def test_ignores_small_quality_change(self):
        """Quality drop of <20% should NOT be flagged."""
        rows = [
            {"dimension_value": "llama-8b", "date": "2026-03-04", "avg_quality": 7.5, "avg_latency_ms": 100.0},
            # Historical
            {"dimension_value": "llama-8b", "date": "2026-02-20", "avg_quality": 8.0, "avg_latency_ms": 100.0},
        ]
        mts = MetricsTimeSeries(graph_manager=self._make_graph(rows))
        anomalies = mts.detect_anomalies(window_days=1)
        quality_regressions = [a for a in anomalies if a["type"] == "quality_regression"]
        assert len(quality_regressions) == 0

    def test_ignores_small_latency_change(self):
        """Latency increase of <50% should NOT be flagged."""
        rows = [
            {"dimension_value": "llama-8b", "date": "2026-03-04", "avg_quality": None, "avg_latency_ms": 130.0},
            # Historical
            {"dimension_value": "llama-8b", "date": "2026-02-20", "avg_quality": None, "avg_latency_ms": 100.0},
        ]
        mts = MetricsTimeSeries(graph_manager=self._make_graph(rows))
        anomalies = mts.detect_anomalies(window_days=1)
        latency_regressions = [a for a in anomalies if a["type"] == "latency_regression"]
        assert len(latency_regressions) == 0

    def test_empty_rows_returns_empty(self):
        mts = MetricsTimeSeries(graph_manager=self._make_graph([]))
        anomalies = mts.detect_anomalies()
        assert anomalies == []
