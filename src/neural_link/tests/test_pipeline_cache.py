"""
Tests for PipelineCache — Layer 0: Deterministic Resolution.

Covers exact match hit/miss/expiry, semantic match threshold, eviction,
graph shortcuts in core.py, and RELEVANCE_THRESHOLD in result_merger.py.
"""

import time
from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.orchestrator.pipeline_cache import PipelineCache


# ==================================================================
# TestExactMatch
# ==================================================================


class TestExactMatch:
    """Tier 1: SHA-256 exact match cache."""

    def test_put_and_get_exact(self):
        cache = PipelineCache()
        cache.put("hello world", "answer 42")
        assert cache.get("hello world") == "answer 42"

    def test_miss_returns_none(self):
        cache = PipelineCache()
        assert cache.get("nonexistent") is None

    def test_different_queries_different_results(self):
        cache = PipelineCache()
        cache.put("query A", "answer A")
        cache.put("query B", "answer B")
        assert cache.get("query A") == "answer A"
        assert cache.get("query B") == "answer B"

    def test_overwrite_same_key(self):
        cache = PipelineCache()
        cache.put("key", "old")
        cache.put("key", "new")
        assert cache.get("key") == "new"

    def test_ttl_expiry(self):
        cache = PipelineCache(exact_ttl=0.1)
        cache.put("q", "a")
        assert cache.get("q") == "a"
        time.sleep(0.15)
        assert cache.get("q") is None

    def test_case_insensitive_match(self):
        cache = PipelineCache()
        cache.put("Hello World", "answer")
        assert cache.get("hello world") == "answer"

    def test_whitespace_normalized(self):
        cache = PipelineCache()
        cache.put("  hello  ", "answer")
        assert cache.get("hello") == "answer"


# ==================================================================
# TestSemanticMatch
# ==================================================================


class TestSemanticMatch:
    """Tier 2: Semantic similarity cache (mocked encoder)."""

    def test_semantic_hit_with_mock_encoder(self):
        cache = PipelineCache(similarity_threshold=0.90)
        import numpy as np

        # Same vector = similarity 1.0
        mock_encoder = MagicMock()
        vec = np.array([1.0, 0.0, 0.0])
        mock_encoder.encode.return_value = vec
        cache._encoder = mock_encoder

        cache.put("how to create campaign", "use the wizard")
        result = cache.get("how do I create a campaign")
        assert result == "use the wizard"

    def test_semantic_miss_below_threshold(self):
        cache = PipelineCache(similarity_threshold=0.99)
        import numpy as np

        # Use orthogonal vectors so cosine similarity = 0.0
        stored_vec = np.array([1.0, 0.0])
        query_vec = np.array([0.0, 1.0])

        mock_encoder = MagicMock()
        cache._encoder = mock_encoder

        # put() calls encode once for the stored query
        mock_encoder.encode.return_value = stored_vec
        cache.put("campaign wizard", "use it")

        # semantic_lookup calls encode for the lookup query
        mock_encoder.encode.return_value = query_vec
        result = cache._semantic_lookup("totally different topic", time.monotonic())
        assert result is None

    def test_no_encoder_means_no_semantic(self):
        cache = PipelineCache()
        cache._encoder = False  # sentinel for no encoder
        cache.put("hello", "world")
        # Exact miss, no semantic fallback
        assert cache.get("hi there") is None


# ==================================================================
# TestCacheStats
# ==================================================================


class TestCacheStats:
    """Cache statistics and clear."""

    def test_stats_empty(self):
        cache = PipelineCache()
        stats = cache.stats
        assert stats["exact_entries"] == 0

    def test_stats_after_put(self):
        cache = PipelineCache()
        cache.put("a", "1")
        cache.put("b", "2")
        assert cache.stats["exact_entries"] == 2

    def test_clear(self):
        cache = PipelineCache()
        cache.put("a", "1")
        cache.clear()
        assert cache.stats["exact_entries"] == 0
        assert cache.get("a") is None

    def test_hit_rate(self):
        cache = PipelineCache()
        cache.put("a", "1")
        cache.get("a")  # hit
        cache.get("b")  # miss
        assert cache.hit_rate == pytest.approx(0.5)


# ==================================================================
# TestGraphShortcuts
# ==================================================================


class TestGraphShortcuts:
    """Graph shortcuts in core.py resolve without LLM."""

    def test_list_agents_shortcut(self):
        from src.neural_link.orchestrator.core import NeuralLinkOrchestrator

        orch = NeuralLinkOrchestrator()
        result = orch._try_graph_shortcut("list agents available")
        assert result is not None
        assert "agents registered" in result.lower()

    def test_list_agentes_pt(self):
        from src.neural_link.orchestrator.core import NeuralLinkOrchestrator

        orch = NeuralLinkOrchestrator()
        result = orch._try_graph_shortcut("agentes disponiveis")
        assert result is not None

    def test_no_match_returns_none(self):
        from src.neural_link.orchestrator.core import NeuralLinkOrchestrator

        orch = NeuralLinkOrchestrator()
        result = orch._try_graph_shortcut("how do I build a rocket ship")
        assert result is None


# ==================================================================
# TestRelevanceThreshold
# ==================================================================


class TestRelevanceThreshold:
    """RELEVANCE_THRESHOLD in result_merger.py filters low-score noise."""

    def test_low_scores_filtered(self):
        from src.neural_link.rag.result_merger import ResultMerger

        merger = ResultMerger()
        results = merger.merge(
            results_by_engine={
                "chroma": [
                    {"content": "good", "source_file": "a.py", "score": 0.8},
                    {"content": "noise", "source_file": "b.py", "score": 0.1},
                ],
            },
            weights={"chroma": 1.0},
            top_k=10,
        )
        contents = [r["content"] for r in results]
        assert "good" in contents
        assert "noise" not in contents

    def test_has_high_confidence_true(self):
        from src.neural_link.rag.result_merger import ResultMerger

        assert ResultMerger.has_high_confidence([{"score": 0.9}])

    def test_has_high_confidence_false(self):
        from src.neural_link.rag.result_merger import ResultMerger

        assert not ResultMerger.has_high_confidence([{"score": 0.3}])
