"""
Tests for ModelBenchmark — Per-model performance tracking for KPI Intelligence.

Covers ModelCallRecord creation, _estimate_cost, _aggregate_bucket, record/flush
buffer mechanics, record_from_profile, and graph-less query fallbacks.
"""

import pytest
from datetime import datetime

from src.neural_link.telemetry.model_benchmark import (
    ModelBenchmark,
    ModelCallRecord,
    _estimate_cost,
)


# ==================================================================
# TestModelCallRecord
# ==================================================================


class TestModelCallRecord:
    """ModelCallRecord dataclass creation and defaults."""

    def test_create_minimal(self):
        r = ModelCallRecord(model="llama-3.1-8b-instant", latency_ms=42.5)
        assert r.model == "llama-3.1-8b-instant"
        assert r.latency_ms == 42.5

    def test_defaults(self):
        r = ModelCallRecord(model="test", latency_ms=10.0)
        assert r.input_tokens == 0
        assert r.output_tokens == 0
        assert r.cost_usd == 0.0
        assert r.quality_score is None
        assert r.success is True

    def test_timestamp_auto_set(self):
        r = ModelCallRecord(model="test", latency_ms=1.0)
        assert r.timestamp != ""
        # Should parse as ISO datetime
        dt = datetime.fromisoformat(r.timestamp)
        assert dt.year >= 2026

    def test_timestamp_explicit(self):
        r = ModelCallRecord(model="test", latency_ms=1.0, timestamp="2026-03-04T12:00:00")
        assert r.timestamp == "2026-03-04T12:00:00"

    def test_full_creation(self):
        r = ModelCallRecord(
            model="llama-3.3-70b-versatile",
            latency_ms=200.0,
            input_tokens=500,
            output_tokens=100,
            cost_usd=0.005,
            quality_score=8.5,
            success=False,
        )
        assert r.model == "llama-3.3-70b-versatile"
        assert r.input_tokens == 500
        assert r.output_tokens == 100
        assert r.cost_usd == 0.005
        assert r.quality_score == 8.5
        assert r.success is False


# ==================================================================
# TestEstimateCost
# ==================================================================


class TestEstimateCost:
    """_estimate_cost helper function."""

    def test_known_model_8b(self):
        cost = _estimate_cost("llama-3.1-8b-instant", 1_000_000)
        assert cost == pytest.approx(0.05, rel=1e-4)

    def test_known_model_70b(self):
        cost = _estimate_cost("llama-3.3-70b-versatile", 1_000_000)
        assert cost == pytest.approx(0.59, rel=1e-4)

    def test_unknown_model_uses_default(self):
        cost = _estimate_cost("some-unknown-model", 1_000_000)
        assert cost == pytest.approx(0.30, rel=1e-4)

    def test_zero_tokens(self):
        cost = _estimate_cost("llama-3.1-8b-instant", 0)
        assert cost == 0.0

    def test_small_token_count(self):
        cost = _estimate_cost("llama-3.1-8b-instant", 1000)
        assert cost == pytest.approx(0.05 * 1000 / 1_000_000, rel=1e-4)


# ==================================================================
# TestAggregateBucket
# ==================================================================


class TestAggregateBucket:
    """ModelBenchmark._aggregate_bucket static method."""

    def test_basic_aggregation(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=100.0, input_tokens=50, output_tokens=10, cost_usd=0.001, quality_score=8.0, success=True, timestamp="2026-03-04T10:00:00"),
            ModelCallRecord(model="m1", latency_ms=200.0, input_tokens=60, output_tokens=20, cost_usd=0.002, quality_score=9.0, success=True, timestamp="2026-03-04T11:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["id"] == "mm_m1_2026-03-04"
        assert result["model_id"] == "m1"
        assert result["date"] == "2026-03-04"
        assert result["requests_delta"] == 2

    def test_latency_stats(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=100.0, timestamp="2026-03-04T10:00:00"),
            ModelCallRecord(model="m1", latency_ms=200.0, timestamp="2026-03-04T11:00:00"),
            ModelCallRecord(model="m1", latency_ms=300.0, timestamp="2026-03-04T12:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["p50_latency_ms"] == 200.0  # median of [100, 200, 300]
        # p95: sorted=[100,200,300], index=int(3*0.95)=2 -> 300
        assert result["p95_latency_ms"] == 300.0
        assert result["avg_latency_ms"] == pytest.approx(200.0, rel=1e-4)

    def test_quality_avg(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=10.0, quality_score=7.0, timestamp="2026-03-04T10:00:00"),
            ModelCallRecord(model="m1", latency_ms=10.0, quality_score=9.0, timestamp="2026-03-04T11:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["avg_quality_score"] == pytest.approx(8.0, rel=1e-4)

    def test_quality_none_when_no_scores(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=10.0, timestamp="2026-03-04T10:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["avg_quality_score"] is None

    def test_failure_count(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=10.0, success=True, timestamp="2026-03-04T10:00:00"),
            ModelCallRecord(model="m1", latency_ms=10.0, success=False, timestamp="2026-03-04T11:00:00"),
            ModelCallRecord(model="m1", latency_ms=10.0, success=False, timestamp="2026-03-04T12:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["failure_delta"] == 2

    def test_token_sums(self):
        calls = [
            ModelCallRecord(model="m1", latency_ms=10.0, input_tokens=100, output_tokens=20, cost_usd=0.01, timestamp="2026-03-04T10:00:00"),
            ModelCallRecord(model="m1", latency_ms=10.0, input_tokens=200, output_tokens=30, cost_usd=0.02, timestamp="2026-03-04T11:00:00"),
        ]
        result = ModelBenchmark._aggregate_bucket("m1", "2026-03-04", calls)
        assert result["tokens_in_delta"] == 300
        assert result["tokens_out_delta"] == 50
        assert result["cost_delta"] == pytest.approx(0.03, rel=1e-4)


# ==================================================================
# TestRecordAndBuffer
# ==================================================================


class TestRecordAndBuffer:
    """ModelBenchmark.record() and buffer mechanics."""

    def test_record_adds_to_buffer(self):
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        r = ModelCallRecord(model="test", latency_ms=10.0)
        mb.record(r)
        assert mb.buffer_size == 1

    def test_record_multiple(self):
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        for _ in range(5):
            mb.record(ModelCallRecord(model="test", latency_ms=10.0))
        assert mb.buffer_size == 5

    def test_auto_flush_at_threshold(self):
        """Buffer is cleared when threshold is reached (no graph = discarded)."""
        mb = ModelBenchmark(graph_manager=None, flush_threshold=3)
        for _ in range(3):
            mb.record(ModelCallRecord(model="test", latency_ms=10.0))
        # Auto-flush should have cleared buffer (no graph = 0 flushed but buffer cleared)
        assert mb.buffer_size == 0

    def test_buffer_size_property(self):
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        assert mb.buffer_size == 0
        mb.record(ModelCallRecord(model="test", latency_ms=10.0))
        assert mb.buffer_size == 1


# ==================================================================
# TestFlush
# ==================================================================


class TestFlush:
    """ModelBenchmark.flush() behavior."""

    def test_flush_no_graph_returns_zero(self):
        mb = ModelBenchmark(graph_manager=None)
        mb.record(ModelCallRecord(model="test", latency_ms=10.0))
        result = mb.flush()
        assert result == 0

    def test_flush_clears_buffer(self):
        mb = ModelBenchmark(graph_manager=None)
        mb.record(ModelCallRecord(model="test", latency_ms=10.0))
        mb.flush()
        assert mb.buffer_size == 0

    def test_flush_empty_buffer(self):
        mb = ModelBenchmark(graph_manager=None)
        result = mb.flush()
        assert result == 0


# ==================================================================
# TestRecordFromProfile
# ==================================================================


class TestRecordFromProfile:
    """ModelBenchmark.record_from_profile() behavior."""

    def test_with_per_call_latencies(self):
        from types import SimpleNamespace
        profile = SimpleNamespace(
            per_call_latencies=[("llama-3.1-8b-instant", 50.0), ("llama-3.3-70b-versatile", 120.0)],
            model_tiers_used=["llama-3.1-8b-instant"],
        )
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        mb.record_from_profile(profile)
        assert mb.buffer_size == 2

    def test_fallback_no_latencies(self):
        from types import SimpleNamespace
        profile = SimpleNamespace(
            per_call_latencies=[],
            model_tiers_used=["llama-3.1-8b-instant"],
            elapsed_ms=100.0,
            total_input_tokens=500,
            total_output_tokens=50,
            estimated_cost_usd=0.003,
        )
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        mb.record_from_profile(profile)
        assert mb.buffer_size == 1

    def test_fallback_no_models_no_record(self):
        """If no latencies and no models, nothing is recorded."""
        from types import SimpleNamespace
        profile = SimpleNamespace(
            per_call_latencies=[],
            model_tiers_used=[],
        )
        mb = ModelBenchmark(graph_manager=None, flush_threshold=100)
        mb.record_from_profile(profile)
        assert mb.buffer_size == 0


# ==================================================================
# TestQueryMethods
# ==================================================================


class TestQueryMethods:
    """ModelBenchmark query methods with no graph."""

    def test_get_leaderboard_no_graph(self):
        mb = ModelBenchmark(graph_manager=None)
        assert mb.get_leaderboard() == []

    def test_get_model_history_no_graph(self):
        mb = ModelBenchmark(graph_manager=None)
        assert mb.get_model_history("llama-3.1-8b-instant") == []
