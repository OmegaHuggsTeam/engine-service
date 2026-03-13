"""
Tests para o EmbeddingManager - Multi-Embedding Engine.

Todos os tests usam mocks do ChromaDB (sem banco real necessario).
Segue o padrao de test_graph_manager.py.
"""

import os
import pytest
from unittest.mock import MagicMock, patch, PropertyMock


# ============================================================
# Helpers
# ============================================================


def _make_mock_collection(name="test_collection", existing_count=0):
    """Cria mock de uma collection ChromaDB."""
    collection = MagicMock()
    collection.name = name
    collection.count.return_value = existing_count
    collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    collection.query.return_value = {
        "ids": [[]],
        "documents": [[]],
        "metadatas": [[]],
        "distances": [[]],
    }
    return collection


def _make_query_result(docs, metas, distances):
    """Cria resultado de query ChromaDB para mock."""
    return {
        "ids": [[f"id_{i}" for i in range(len(docs))]],
        "documents": [docs],
        "metadatas": [metas],
        "distances": [distances],
    }


# ============================================================
# TestSingleton
# ============================================================


class TestSingleton:
    """Tests para o padrao singleton do EmbeddingManager."""

    def setup_method(self):
        """Reset singleton antes de cada teste."""
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        """Reset singleton apos cada teste."""
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "minilm"}, clear=False)
    def test_from_env_creates_singleton(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr1 = EmbeddingManager.from_env()
        mgr2 = EmbeddingManager.from_env()
        assert mgr1 is mgr2

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "minilm"}, clear=False)
    def test_reset_instance_clears_singleton(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr1 = EmbeddingManager.from_env()
        EmbeddingManager.reset_instance()
        mgr2 = EmbeddingManager.from_env()
        assert mgr1 is not mgr2

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "", "OPENAI_API_KEY": ""}, clear=False)
    def test_from_env_no_env_defaults_to_minilm(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager.from_env()
        assert "minilm" in mgr.model_names

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "", "OPENAI_API_KEY": "sk-test"}, clear=False)
    def test_from_env_no_env_with_openai_key_defaults_to_openai(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager.from_env()
        assert "openai" in mgr.model_names


# ============================================================
# TestModelRegistration
# ============================================================


class TestModelRegistration:
    """Tests para registro de modelos a partir do env var."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def test_single_model(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["openai"])
        assert mgr.model_count == 1
        assert mgr.model_names == ["openai"]

    def test_multiple_models(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["openai", "nomic", "minilm"])
        assert mgr.model_count == 3
        assert set(mgr.model_names) == {"openai", "nomic", "minilm"}

    def test_invalid_model_ignored(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["openai", "invalid_model"])
        assert mgr.model_count == 1
        assert "openai" in mgr.model_names
        assert "invalid_model" not in mgr.model_names

    def test_all_invalid_raises(self):
        from src.utils.embedding_manager import EmbeddingManager

        with pytest.raises(ValueError, match="Nenhum modelo valido"):
            EmbeddingManager(["fake1", "fake2"])

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "openai,nomic"}, clear=False)
    def test_from_env_reads_comma_separated(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager.from_env()
        assert mgr.model_count == 2
        assert set(mgr.model_names) == {"openai", "nomic"}

    def test_case_insensitive_model_names(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["OpenAI", "NOMIC"])
        assert mgr.model_count == 2
        assert "openai" in mgr.model_names
        assert "nomic" in mgr.model_names

    def test_whitespace_trimmed(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["  openai  ", " minilm "])
        assert set(mgr.model_names) == {"openai", "minilm"}


# ============================================================
# TestAddChunks
# ============================================================


class TestAddChunks:
    """Tests para add_chunks que despacha para todas as colecoes."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_add_chunks_dispatches_to_all_models(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col_openai = _make_mock_collection("course_chunks_openai")
        col_minilm = _make_mock_collection("course_chunks_minilm")

        collections = {"openai": col_openai, "minilm": col_minilm}
        mock_get_col.side_effect = lambda name: collections[name]

        mgr = EmbeddingManager(["openai", "minilm"])
        chunks = [
            {"content": "Hello world", "source_file": "test.md", "chunk_index": 0},
            {"content": "Foo bar", "source_file": "test.md", "chunk_index": 1},
        ]

        result = mgr.add_chunks(chunks)

        assert result == {"openai": 2, "minilm": 2}
        assert col_openai.add.called
        assert col_minilm.add.called

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_add_chunks_empty(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["openai"])
        result = mgr.add_chunks([])
        assert result == {"openai": 0}
        mock_get_col.assert_not_called()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_add_chunks_removes_existing_by_source_file(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col = _make_mock_collection("course_chunks_minilm")
        # Simulate existing chunks
        col.get.return_value = {"ids": ["test.md_0", "test.md_1"]}
        mock_get_col.return_value = col

        mgr = EmbeddingManager(["minilm"])
        chunks = [{"content": "Updated", "source_file": "test.md", "chunk_index": 0}]

        mgr.add_chunks(chunks)

        col.delete.assert_called_once_with(ids=["test.md_0", "test.md_1"])
        col.add.assert_called_once()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_add_chunks_batching(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col = _make_mock_collection("course_chunks_minilm")
        mock_get_col.return_value = col

        mgr = EmbeddingManager(["minilm"])
        chunks = [
            {"content": f"chunk {i}", "source_file": "batch.md", "chunk_index": i}
            for i in range(5)
        ]

        mgr.add_chunks(chunks, batch_size=2)

        # 5 chunks com batch_size=2 => 3 batches (2, 2, 1)
        assert col.add.call_count == 3

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_add_chunks_error_in_one_model_continues(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col_ok = _make_mock_collection("course_chunks_minilm")
        col_err = MagicMock()
        # Make the collection itself raise on add (simulates full connection failure)
        col_err.get.return_value = {"ids": []}
        col_err.add.side_effect = Exception("connection refused")

        collections = {"openai": col_err, "minilm": col_ok}
        mock_get_col.side_effect = lambda name: collections[name]

        mgr = EmbeddingManager(["openai", "minilm"])
        chunks = [{"content": "test", "source_file": "a.md", "chunk_index": 0}]

        result = mgr.add_chunks(chunks)

        assert result["minilm"] == 1
        assert result["openai"] == 0


# ============================================================
# TestSearch
# ============================================================


class TestSearch:
    """Tests para search que busca em todas as colecoes e faz merge."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_merges_from_all_models(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col_openai = _make_mock_collection("course_chunks_openai")
        col_openai.query.return_value = _make_query_result(
            docs=["OpenAI found this"],
            metas=[{"source_file": "a.md"}],
            distances=[0.2],  # score = 1 - 0.2/2 = 0.9
        )

        col_minilm = _make_mock_collection("course_chunks_minilm")
        col_minilm.query.return_value = _make_query_result(
            docs=["MiniLM found this"],
            metas=[{"source_file": "b.md"}],
            distances=[0.4],  # score = 1 - 0.4/2 = 0.8
        )

        collections = {"openai": col_openai, "minilm": col_minilm}
        mock_get_col.side_effect = lambda name: collections[name]

        mgr = EmbeddingManager(["openai", "minilm"])
        results = mgr.search("test query", top_k=5)

        assert len(results) == 2
        # Results should have scores
        assert all("score" in r for r in results)
        # Should be sorted by score desc
        assert results[0]["score"] >= results[1]["score"]

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_cross_model_boost(self, mock_get_col):
        """Items found by multiple models should get cross-engine boost from ResultMerger."""
        from src.utils.embedding_manager import EmbeddingManager

        # Same content in both models
        shared_doc = "Shared content across models"
        shared_meta = {"source_file": "shared.md"}

        col_openai = _make_mock_collection("course_chunks_openai")
        col_openai.query.return_value = _make_query_result(
            docs=[shared_doc],
            metas=[shared_meta],
            distances=[0.2],
        )

        col_minilm = _make_mock_collection("course_chunks_minilm")
        col_minilm.query.return_value = _make_query_result(
            docs=[shared_doc],
            metas=[shared_meta],
            distances=[0.3],
        )

        collections = {"openai": col_openai, "minilm": col_minilm}
        mock_get_col.side_effect = lambda name: collections[name]

        mgr = EmbeddingManager(["openai", "minilm"])
        results = mgr.search("test", top_k=5)

        # Should be deduplicated to 1 result
        assert len(results) == 1
        # Should have engine_count > 1 (cross-model boost applied)
        assert results[0]["engine_count"] == 2

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_empty_query(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["minilm"])
        results = mgr.search("", top_k=5)
        assert results == []
        mock_get_col.assert_not_called()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_no_results(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col = _make_mock_collection("course_chunks_minilm")
        col.query.return_value = {
            "ids": [[]],
            "documents": [[]],
            "metadatas": [[]],
            "distances": [[]],
        }
        mock_get_col.return_value = col

        mgr = EmbeddingManager(["minilm"])
        results = mgr.search("no results query", top_k=5)
        assert results == []


# ============================================================
# TestSearchWithModel
# ============================================================


class TestSearchWithModel:
    """Tests para search_with_model (modelo especifico)."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_with_model_returns_only_that_model(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col = _make_mock_collection("course_chunks_openai")
        col.query.return_value = _make_query_result(
            docs=["Result from openai"],
            metas=[{"source_file": "test.md"}],
            distances=[0.1],
        )
        mock_get_col.return_value = col

        mgr = EmbeddingManager(["openai", "minilm"])
        results = mgr.search_with_model("query", "openai", top_k=5)

        assert len(results) == 1
        assert results[0]["engine"] == "openai"
        # Must only query the openai collection, not minilm
        mock_get_col.assert_called_once_with("openai")

    def test_search_with_invalid_model(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["minilm"])
        results = mgr.search_with_model("query", "nonexistent", top_k=5)
        assert results == []

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_search_with_model_scores(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col = _make_mock_collection("course_chunks_minilm")
        col.query.return_value = _make_query_result(
            docs=["Close match", "Far match"],
            metas=[{"source_file": "a.md"}, {"source_file": "b.md"}],
            distances=[0.1, 1.5],
        )
        mock_get_col.return_value = col

        mgr = EmbeddingManager(["minilm"])
        results = mgr.search_with_model("test", "minilm", top_k=5)

        assert len(results) == 2
        # score = 1 - dist/2
        assert results[0]["score"] == pytest.approx(0.95, abs=0.01)
        assert results[1]["score"] == pytest.approx(0.25, abs=0.01)


# ============================================================
# TestListModels
# ============================================================


class TestListModels:
    """Tests para list_models."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_collection")
    def test_list_models_returns_correct_info(self, mock_get_col):
        from src.utils.embedding_manager import EmbeddingManager

        col_openai = _make_mock_collection("course_chunks_openai", existing_count=100)
        col_minilm = _make_mock_collection("course_chunks_minilm", existing_count=50)

        collections = {"openai": col_openai, "minilm": col_minilm}
        mock_get_col.side_effect = lambda name: collections[name]

        mgr = EmbeddingManager(["openai", "minilm"])
        models = mgr.list_models()

        assert len(models) == 2

        openai_info = next(m for m in models if m["name"] == "openai")
        assert openai_info["dimensions"] == 1536
        assert openai_info["collection_name"] == "course_chunks_openai"
        assert openai_info["chunk_count"] == 100

        minilm_info = next(m for m in models if m["name"] == "minilm")
        assert minilm_info["dimensions"] == 384
        assert minilm_info["collection_name"] == "course_chunks_minilm"
        assert minilm_info["chunk_count"] == 50


# ============================================================
# TestRemoveModel
# ============================================================


class TestRemoveModel:
    """Tests para remove_model."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch("src.utils.embedding_manager.EmbeddingManager._get_client")
    def test_remove_model_deletes_collection(self, mock_get_client):
        from src.utils.embedding_manager import EmbeddingManager

        mock_client = MagicMock()
        mock_get_client.return_value = mock_client

        mgr = EmbeddingManager(["openai", "minilm"])
        assert mgr.model_count == 2

        result = mgr.remove_model("minilm")

        assert result is True
        mock_client.delete_collection.assert_called_once_with("course_chunks_minilm")
        assert mgr.model_count == 1
        assert "minilm" not in mgr.model_names

    def test_remove_nonexistent_model(self):
        from src.utils.embedding_manager import EmbeddingManager

        mgr = EmbeddingManager(["openai"])
        result = mgr.remove_model("nonexistent")
        assert result is False

    @patch("src.utils.embedding_manager.EmbeddingManager._get_client")
    def test_remove_model_handles_error(self, mock_get_client):
        from src.utils.embedding_manager import EmbeddingManager

        mock_client = MagicMock()
        mock_client.delete_collection.side_effect = Exception("DB error")
        mock_get_client.return_value = mock_client

        mgr = EmbeddingManager(["openai", "minilm"])
        result = mgr.remove_model("minilm")

        assert result is False
        # Model should still be registered since removal failed
        assert mgr.model_count == 2


# ============================================================
# TestBackwardCompatibility
# ============================================================


class TestBackwardCompatibility:
    """Tests para compatibilidade retroativa com vector_db.py."""

    def setup_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    def teardown_method(self):
        from src.utils.embedding_manager import EmbeddingManager
        EmbeddingManager.reset_instance()

    @patch.dict(os.environ, {"EMBEDDING_MODELS": ""}, clear=False)
    def test_single_model_no_env_keeps_original_behavior(self):
        """Sem EMBEDDING_MODELS, vector_db deve manter comportamento original."""
        from src.utils.vector_db import _is_multi_embedding

        assert _is_multi_embedding() is False

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "openai"}, clear=False)
    def test_single_model_one_value_keeps_original_behavior(self):
        """Com 1 modelo, vector_db deve manter comportamento original."""
        from src.utils.vector_db import _is_multi_embedding

        assert _is_multi_embedding() is False

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "openai,nomic"}, clear=False)
    def test_multi_model_activates_delegation(self):
        """Com 2+ modelos, vector_db deve ativar multi-embedding."""
        from src.utils.vector_db import _is_multi_embedding

        assert _is_multi_embedding() is True

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "openai, nomic, minilm"}, clear=False)
    def test_multi_model_three_models(self):
        from src.utils.vector_db import _is_multi_embedding

        assert _is_multi_embedding() is True

    @patch.dict(os.environ, {"EMBEDDING_MODELS": "  ,  ,  "}, clear=False)
    def test_empty_commas_not_multi(self):
        """Virgulas sem conteudo nao devem ativar multi-embedding."""
        from src.utils.vector_db import _is_multi_embedding

        assert _is_multi_embedding() is False


# ============================================================
# TestCollectionNaming
# ============================================================


class TestCollectionNaming:
    """Tests para o esquema de nomes das colecoes."""

    def test_collection_name_format(self):
        from src.utils.embedding_manager import _make_collection_name

        assert _make_collection_name("openai") == "course_chunks_openai"
        assert _make_collection_name("nomic") == "course_chunks_nomic"
        assert _make_collection_name("minilm") == "course_chunks_minilm"


# ============================================================
# TestModelRegistry
# ============================================================


class TestModelRegistry:
    """Tests para o registro de modelos suportados."""

    def test_openai_model_info(self):
        from src.utils.embedding_manager import MODEL_REGISTRY

        assert "openai" in MODEL_REGISTRY
        assert MODEL_REGISTRY["openai"]["dimensions"] == 1536
        assert MODEL_REGISTRY["openai"]["type"] == "openai"

    def test_nomic_model_info(self):
        from src.utils.embedding_manager import MODEL_REGISTRY

        assert "nomic" in MODEL_REGISTRY
        assert MODEL_REGISTRY["nomic"]["dimensions"] == 768
        assert MODEL_REGISTRY["nomic"]["type"] == "sentence_transformer"

    def test_minilm_model_info(self):
        from src.utils.embedding_manager import MODEL_REGISTRY

        assert "minilm" in MODEL_REGISTRY
        assert MODEL_REGISTRY["minilm"]["dimensions"] == 384
        assert MODEL_REGISTRY["minilm"]["type"] == "sentence_transformer"
