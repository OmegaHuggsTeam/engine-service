"""
Tests for CostQualityAnalyzer — $/quality-point analysis for KPI Intelligence.

Covers graph-less query fallbacks, get_combined structure, recommend_model
logic, and compute_from_profiles with mock profile objects.
"""

import pytest
from types import SimpleNamespace

from src.neural_link.telemetry.cost_quality_analyzer import CostQualityAnalyzer


# ==================================================================
# TestGraphlessQueries
# ==================================================================


class TestGraphlessQueries:
    """CostQualityAnalyzer methods with no graph return empty results."""

    def test_get_by_model_no_graph(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        assert cqa.get_by_model() == []

    def test_get_by_agent_no_graph(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        assert cqa.get_by_agent() == []

    def test_get_by_task_type_no_graph(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        assert cqa.get_by_task_type() == []


# ==================================================================
# TestGetCombined
# ==================================================================


class TestGetCombined:
    """CostQualityAnalyzer.get_combined structure."""

    def test_returns_dict_with_three_keys(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        result = cqa.get_combined()
        assert isinstance(result, dict)
        assert "by_model" in result
        assert "by_agent" in result
        assert "by_task_type" in result

    def test_all_values_are_lists(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        result = cqa.get_combined()
        assert isinstance(result["by_model"], list)
        assert isinstance(result["by_agent"], list)
        assert isinstance(result["by_task_type"], list)


# ==================================================================
# TestRecommendModel
# ==================================================================


class TestRecommendModel:
    """CostQualityAnalyzer.recommend_model logic."""

    def test_no_graph_returns_none(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        result = cqa.recommend_model()
        assert result is None

    def test_filters_by_min_quality(self):
        """When all candidates are below min_quality, returns None."""

        class MockGraph:
            def execute_read(self, query, params=None):
                return [
                    {"model": "cheap", "avg_quality": 3.0, "cost_per_quality_point": 0.01, "total_cost": 0.1, "total_requests": 10},
                    {"model": "medium", "avg_quality": 5.0, "cost_per_quality_point": 0.02, "total_cost": 0.2, "total_requests": 20},
                ]

        cqa = CostQualityAnalyzer(graph_manager=MockGraph())
        result = cqa.recommend_model(min_quality=7.0)
        assert result is None

    def test_selects_cheapest_qualified(self):
        """Selects the cheapest model that meets min_quality."""

        class MockGraph:
            def execute_read(self, query, params=None):
                return [
                    {"model": "expensive", "avg_quality": 9.0, "cost_per_quality_point": 0.10, "total_cost": 0.9, "total_requests": 10},
                    {"model": "cheap", "avg_quality": 7.5, "cost_per_quality_point": 0.02, "total_cost": 0.15, "total_requests": 10},
                    {"model": "mid", "avg_quality": 8.0, "cost_per_quality_point": 0.05, "total_cost": 0.4, "total_requests": 10},
                ]

        cqa = CostQualityAnalyzer(graph_manager=MockGraph())
        result = cqa.recommend_model(min_quality=7.0)
        assert result is not None
        assert result["model"] == "cheap"
        assert result["avg_quality"] == 7.5


# ==================================================================
# TestComputeFromProfiles
# ==================================================================


class TestComputeFromProfiles:
    """CostQualityAnalyzer.compute_from_profiles with mock profiles."""

    def test_empty_list_returns_empty_structure(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        result = cqa.compute_from_profiles([])
        assert result == {"by_model": [], "by_agent": [], "summary": {}}

    def test_single_profile(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        p = SimpleNamespace(
            model_tiers_used=["llama-3.1-8b-instant"],
            estimated_cost_usd=0.001,
            total_tokens=100,
        )
        result = cqa.compute_from_profiles([p])
        assert len(result["by_model"]) == 1
        assert result["by_model"][0]["model"] == "llama-3.1-8b-instant"
        assert result["by_model"][0]["total_requests"] == 1
        assert result["by_model"][0]["total_tokens"] == 100

    def test_groups_by_model(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        p1 = SimpleNamespace(model_tiers_used=["llama-3.1-8b-instant"], estimated_cost_usd=0.001, total_tokens=100)
        p2 = SimpleNamespace(model_tiers_used=["llama-3.1-8b-instant"], estimated_cost_usd=0.002, total_tokens=200)
        p3 = SimpleNamespace(model_tiers_used=["llama-3.3-70b-versatile"], estimated_cost_usd=0.01, total_tokens=500)
        result = cqa.compute_from_profiles([p1, p2, p3])
        assert len(result["by_model"]) == 2
        models = {m["model"] for m in result["by_model"]}
        assert "llama-3.1-8b-instant" in models
        assert "llama-3.3-70b-versatile" in models

    def test_calculates_correct_totals(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        p1 = SimpleNamespace(model_tiers_used=["llama-3.1-8b-instant"], estimated_cost_usd=0.001, total_tokens=100)
        p2 = SimpleNamespace(model_tiers_used=["llama-3.1-8b-instant"], estimated_cost_usd=0.002, total_tokens=200)
        result = cqa.compute_from_profiles([p1, p2])
        model_entry = result["by_model"][0]
        assert model_entry["total_requests"] == 2
        assert model_entry["total_cost"] == pytest.approx(0.003, rel=1e-4)
        assert model_entry["total_tokens"] == 300
        assert model_entry["avg_cost_per_request"] == pytest.approx(0.0015, rel=1e-4)

    def test_summary_totals(self):
        cqa = CostQualityAnalyzer(graph_manager=None)
        p1 = SimpleNamespace(model_tiers_used=["m1"], estimated_cost_usd=0.01, total_tokens=500)
        p2 = SimpleNamespace(model_tiers_used=["m2"], estimated_cost_usd=0.02, total_tokens=1000)
        result = cqa.compute_from_profiles([p1, p2])
        summary = result["summary"]
        assert summary["total_profiles"] == 2
        assert summary["total_cost"] == pytest.approx(0.03, rel=1e-4)
        assert summary["models_seen"] == 2

    def test_unknown_model_fallback(self):
        """Profile with empty model_tiers_used maps to 'unknown'."""
        cqa = CostQualityAnalyzer(graph_manager=None)
        p = SimpleNamespace(model_tiers_used=[], estimated_cost_usd=0.001, total_tokens=100)
        result = cqa.compute_from_profiles([p])
        assert result["by_model"][0]["model"] == "unknown"
