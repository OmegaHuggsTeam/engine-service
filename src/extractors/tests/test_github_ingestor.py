"""
Tests for GitHub Ingestor.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from src.extractors.github_ingestor import _parse_repo_url, ingest_repository


class TestParseRepoUrl:
    """Parsing de URLs GitHub."""

    def test_https_url(self):
        assert _parse_repo_url("https://github.com/zie619/zie619.github.io") == ("zie619", "zie619.github.io")

    def test_https_with_trailing_slash(self):
        assert _parse_repo_url("https://github.com/owner/repo/") == ("owner", "repo")

    def test_ssh_url(self):
        assert _parse_repo_url("git@github.com:owner/repo.git") == ("owner", "repo")

    def test_invalid_url_raises(self):
        with pytest.raises(ValueError, match="inválida"):
            _parse_repo_url("https://gitlab.com/owner/repo")


class TestIngestRepository:
    """Ingestão com mocks."""

    @pytest.fixture
    def mock_n8n_workflow(self, tmp_path):
        """Arquivo JSON que simula workflow n8n."""
        wf = {
            "name": "Test Workflow",
            "nodes": [
                {"type": "n8n-nodes-base.webhook", "name": "Webhook", "parameters": {}},
                {"type": "n8n-nodes-base.httpRequest", "name": "HTTP", "parameters": {}},
            ],
            "connections": {
                "Webhook": {"main": [[{"node": "HTTP", "type": "main", "index": 0}]]},
            },
        }
        (tmp_path / "workflow.json").write_text(json.dumps(wf), encoding="utf-8")
        return tmp_path / "workflow.json"

    def test_ingest_with_mocked_api(self, mock_n8n_workflow):
        """Ingest com API e download mockados."""
        wf_content = mock_n8n_workflow.read_text(encoding="utf-8")
        with (
            patch("src.extractors.github_ingestor._get_default_branch", return_value="main"),
            patch(
                "src.extractors.github_ingestor._list_json_files",
                return_value=["workflows/workflow.json"],
            ),
            patch(
                "src.extractors.github_ingestor._download_file",
                return_value=wf_content,
            ),
            patch("src.utils.vector_db.add_chunks", return_value=5) as mock_add,
        ):
            stats = ingest_repository(
                "https://github.com/zie619/zie619.github.io",
                save_to_chromadb=True,
            )

        assert stats["total_files"] == 1
        assert stats["workflows_processed"] >= 1
        if stats["workflows_processed"] > 0:
            mock_add.assert_called_once()
            chunks = mock_add.call_args[0][0]
            for c in chunks:
                assert c.get("category") == "external_template"
                assert "source_url" in c
