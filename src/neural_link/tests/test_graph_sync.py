"""
Tests for GraphSynergy — n8n Service/Node graph sync.

Tests sync_modules_to_graph() and the github_ingestor graph hook.
All Neo4j calls are mocked — no real Neo4j required.
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from src.extractors.n8n_extractor import sync_modules_to_graph


# ==================================================================
# Fixtures
# ==================================================================


def _make_modules():
    """Returns a minimal set of extracted modules for testing."""
    return [
        {
            "node_name": "Webhook",
            "node_type": "n8n-nodes-base.webhook",
            "service": "Webhook",
            "type_version": 2,
            "parameters": {"path": "hook"},
            "connections": {"outputs": ["Google Sheets"], "inputs_from": []},
            "credential_types": [],
            "content": "n8n Node: Webhook",
            "source_file": "n8n/TestFlow",
            "chunk_index": 0,
            "category": "n8n_workflow",
            "agent_specialty": "automation",
        },
        {
            "node_name": "Google Sheets",
            "node_type": "n8n-nodes-base.googleSheets",
            "service": "Google Sheets",
            "type_version": 4,
            "parameters": {"operation": "append"},
            "connections": {"outputs": ["Groq"], "inputs_from": ["Webhook"]},
            "credential_types": ["googleSheetsOAuth2Api"],
            "content": "n8n Node: Google Sheets",
            "source_file": "n8n/TestFlow",
            "chunk_index": 1,
            "category": "n8n_workflow",
            "agent_specialty": "automation",
        },
        {
            "node_name": "Groq",
            "node_type": "@n8n/n8n-nodes-langchain.lmChatGroq",
            "service": "Groq",
            "type_version": 1,
            "parameters": {"model": "llama3"},
            "connections": {"outputs": [], "inputs_from": ["Google Sheets"]},
            "credential_types": ["groqApi"],
            "content": "n8n Node: Groq",
            "source_file": "n8n/TestFlow",
            "chunk_index": 2,
            "category": "n8n_workflow",
            "agent_specialty": "automation",
        },
    ]


def _make_graph_mock():
    """Returns a MagicMock GraphManager with connectivity."""
    graph = MagicMock()
    graph.verify_connectivity.return_value = True
    graph.execute_write_batch.return_value = 0
    return graph


# ==================================================================
# TestSyncModulesToGraph
# ==================================================================


class TestSyncModulesToGraph:
    """sync_modules_to_graph behavior."""

    def test_creates_services(self):
        """Each unique service produces an UPSERT_SERVICE in the batch."""
        graph = _make_graph_mock()
        modules = _make_modules()

        stats = sync_modules_to_graph(modules, graph=graph)

        assert stats["services"] == 3  # Webhook, Google Sheets, Groq

    def test_creates_nodes(self):
        """Each module produces an UPSERT_N8N_NODE in the batch."""
        graph = _make_graph_mock()
        modules = _make_modules()

        stats = sync_modules_to_graph(modules, graph=graph)

        assert stats["nodes"] == 3

    def test_creates_uses_edges(self):
        """Each node gets a (Service)-[:USES]->(N8nNode) edge."""
        graph = _make_graph_mock()
        modules = _make_modules()

        stats = sync_modules_to_graph(modules, graph=graph)

        assert stats["uses_edges"] == 3

    def test_creates_connects_edges(self):
        """Output connections become CONNECTS_TO edges."""
        graph = _make_graph_mock()
        modules = _make_modules()

        stats = sync_modules_to_graph(modules, graph=graph)

        # Webhook->Google Sheets, Google Sheets->Groq = 2 edges
        assert stats["connects_edges"] == 2

    def test_batch_executed_once(self):
        """All operations sent in a single execute_write_batch call."""
        graph = _make_graph_mock()
        modules = _make_modules()

        sync_modules_to_graph(modules, graph=graph)

        graph.execute_write_batch.assert_called_once()

    def test_batch_contains_all_operations(self):
        """Batch size = services + nodes + uses + connects."""
        graph = _make_graph_mock()
        modules = _make_modules()

        sync_modules_to_graph(modules, graph=graph)

        batch = graph.execute_write_batch.call_args[0][0]
        # 3 services + 3 nodes + 3 uses + 2 connects = 11
        assert len(batch) == 11

    def test_node_ids_are_unique(self):
        """N8nNode ids include workflow prefix for uniqueness."""
        graph = _make_graph_mock()
        modules = _make_modules()

        sync_modules_to_graph(modules, graph=graph)

        batch = graph.execute_write_batch.call_args[0][0]
        node_upserts = [
            params for query, params in batch
            if "N8nNode" in query and "name" in params and "node_type" in params
        ]
        node_ids = [p["id"] for p in node_upserts]
        assert len(node_ids) == len(set(node_ids))
        assert all(id.startswith("n8n/TestFlow/") for id in node_ids)

    def test_service_ids_are_lowercase_slug(self):
        """Service ids are lowercase with underscores."""
        graph = _make_graph_mock()
        modules = _make_modules()

        sync_modules_to_graph(modules, graph=graph)

        batch = graph.execute_write_batch.call_args[0][0]
        service_upserts = [
            params for query, params in batch
            if "Service" in query and "name" in params and "node_type" not in params
        ]
        service_ids = [p["id"] for p in service_upserts]
        assert "google_sheets" in service_ids
        assert "groq" in service_ids
        assert "webhook" in service_ids

    def test_idempotent_no_duplicates(self):
        """Running twice produces no duplicates (MERGE-based)."""
        graph = _make_graph_mock()
        modules = _make_modules()

        stats1 = sync_modules_to_graph(modules, graph=graph)
        stats2 = sync_modules_to_graph(modules, graph=graph)

        # Same counts — MERGE ensures no graph-level duplicates
        assert stats1["services"] == stats2["services"]
        assert stats1["nodes"] == stats2["nodes"]

    def test_empty_modules(self):
        """Empty module list produces no batch call."""
        graph = _make_graph_mock()

        stats = sync_modules_to_graph([], graph=graph)

        assert stats["services"] == 0
        assert stats["nodes"] == 0
        graph.execute_write_batch.assert_not_called()

    def test_batch_error_captured(self):
        """Batch execution failure is captured, not raised."""
        graph = _make_graph_mock()
        graph.execute_write_batch.side_effect = RuntimeError("Neo4j down")
        modules = _make_modules()

        stats = sync_modules_to_graph(modules, graph=graph)

        assert len(stats["errors"]) == 1
        assert "Neo4j down" in stats["errors"][0]


# ==================================================================
# TestSyncGracefulFallback
# ==================================================================


class TestSyncGracefulFallback:
    """Graph sync never blocks if Neo4j is unavailable."""

    @patch("src.neural_link.graph.manager.GraphManager.from_env")
    def test_no_connectivity_returns_skipped(self, mock_from_env):
        """If Neo4j is unreachable, returns skipped=True."""
        mock_instance = MagicMock()
        mock_instance.verify_connectivity.return_value = False
        mock_from_env.return_value = mock_instance

        stats = sync_modules_to_graph(_make_modules())

        assert stats["skipped"] is True

    @patch("src.neural_link.graph.manager.GraphManager.from_env")
    def test_from_env_exception_returns_skipped(self, mock_from_env):
        """If GraphManager.from_env() throws, returns skipped=True."""
        mock_from_env.side_effect = Exception("No .env")

        stats = sync_modules_to_graph(_make_modules())

        assert stats["skipped"] is True


# ==================================================================
# TestSyncConnectsToResolution
# ==================================================================


class TestSyncConnectsToResolution:
    """CONNECTS_TO edges resolve target names within the same workflow."""

    def test_cross_workflow_targets_ignored(self):
        """Output targets not found in the same workflow are skipped."""
        graph = _make_graph_mock()
        modules = [
            {
                "node_name": "A",
                "node_type": "n8n-nodes-base.webhook",
                "service": "Webhook",
                "type_version": 1,
                "parameters": {},
                "connections": {"outputs": ["NonExistent"], "inputs_from": []},
                "credential_types": [],
                "content": "",
                "source_file": "n8n/Flow1",
                "chunk_index": 0,
                "category": "n8n_workflow",
                "agent_specialty": "automation",
            },
        ]

        stats = sync_modules_to_graph(modules, graph=graph)

        assert stats["connects_edges"] == 0

    def test_multiple_workflows_isolated(self):
        """Nodes from different workflows don't create cross-edges."""
        graph = _make_graph_mock()
        modules = [
            {
                "node_name": "Sender",
                "node_type": "n8n-nodes-base.httpRequest",
                "service": "HTTP Request",
                "type_version": 1,
                "parameters": {},
                "connections": {"outputs": ["Target"], "inputs_from": []},
                "credential_types": [],
                "content": "",
                "source_file": "n8n/Flow1",
                "chunk_index": 0,
                "category": "n8n_workflow",
                "agent_specialty": "automation",
            },
            {
                "node_name": "Target",
                "node_type": "n8n-nodes-base.set",
                "service": "Set",
                "type_version": 1,
                "parameters": {},
                "connections": {"outputs": [], "inputs_from": []},
                "credential_types": [],
                "content": "",
                "source_file": "n8n/Flow2",  # Different workflow!
                "chunk_index": 0,
                "category": "n8n_workflow",
                "agent_specialty": "automation",
            },
        ]

        stats = sync_modules_to_graph(modules, graph=graph)

        # "Target" is in Flow2 but Sender is in Flow1 — no edge
        assert stats["connects_edges"] == 0


# ==================================================================
# TestGitHubIngestorGraphHook
# ==================================================================


class TestGitHubIngestorGraphHook:
    """Graph sync is called during GitHub ingestion."""

    @patch("src.extractors.github_ingestor.sync_modules_to_graph")
    @patch("src.extractors.github_ingestor._list_json_files", return_value=["wf.json"])
    @patch("src.extractors.github_ingestor._get_default_branch", return_value="main")
    @patch("src.extractors.github_ingestor._download_file")
    def test_graph_sync_called_after_ingestion(
        self, mock_download, mock_branch, mock_list, mock_sync
    ):
        """sync_modules_to_graph is called with all_chunks after extraction."""
        from src.extractors.github_ingestor import ingest_repository

        workflow = {
            "name": "TestWF",
            "nodes": [
                {
                    "name": "Hook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "parameters": {},
                }
            ],
            "connections": {},
        }
        mock_download.return_value = json.dumps(workflow)
        mock_sync.return_value = {"services": 1, "nodes": 1, "uses_edges": 1, "connects_edges": 0, "errors": []}

        stats = ingest_repository(
            "https://github.com/test/repo",
            save_to_chromadb=False,
        )

        mock_sync.assert_called_once()
        assert "graph_sync" in stats

    @patch("src.extractors.github_ingestor.sync_modules_to_graph")
    @patch("src.extractors.github_ingestor._list_json_files", return_value=["wf.json"])
    @patch("src.extractors.github_ingestor._get_default_branch", return_value="main")
    @patch("src.extractors.github_ingestor._download_file")
    def test_graph_sync_failure_non_blocking(
        self, mock_download, mock_branch, mock_list, mock_sync
    ):
        """Graph sync failure does not prevent ingestion from returning."""
        from src.extractors.github_ingestor import ingest_repository

        workflow = {
            "name": "TestWF",
            "nodes": [
                {
                    "name": "Hook",
                    "type": "n8n-nodes-base.webhook",
                    "typeVersion": 1,
                    "parameters": {},
                }
            ],
            "connections": {},
        }
        mock_download.return_value = json.dumps(workflow)
        mock_sync.side_effect = RuntimeError("Neo4j exploded")

        stats = ingest_repository(
            "https://github.com/test/repo",
            save_to_chromadb=False,
        )

        # Ingestion completes despite graph sync failure
        assert stats["workflows_processed"] == 1
        assert stats["graph_sync"]["skipped"] is True

    @patch("src.extractors.github_ingestor.sync_modules_to_graph")
    @patch("src.extractors.github_ingestor._list_json_files", return_value=["not_n8n.json"])
    @patch("src.extractors.github_ingestor._get_default_branch", return_value="main")
    @patch("src.extractors.github_ingestor._download_file")
    def test_no_workflows_skips_graph_sync(
        self, mock_download, mock_branch, mock_list, mock_sync
    ):
        """If no workflows are found, graph sync is not called."""
        from src.extractors.github_ingestor import ingest_repository

        mock_download.return_value = '{"not": "a workflow"}'

        stats = ingest_repository(
            "https://github.com/test/repo",
            save_to_chromadb=False,
        )

        mock_sync.assert_not_called()
