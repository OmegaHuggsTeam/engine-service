"""
Tests for UseCaseRegistry — query interface for UseCase nodes.

All Neo4j calls are mocked — no external dependencies required.
Follows test_graph_sync.py conventions.
"""

from unittest.mock import MagicMock, patch

import pytest

from src.neural_link.api.usecase_registry import UseCaseRegistry


# ==================================================================
# Fixtures
# ==================================================================


def _make_graph_mock():
    """Returns a MagicMock GraphManager."""
    graph = MagicMock()
    graph.verify_connectivity.return_value = True
    graph.execute_read.return_value = []
    return graph


def _sample_usecases():
    """Returns sample usecase data for roadmap tests."""
    return [
        {
            "id": "UC-CRM-001",
            "name": "Campaign Blast",
            "domain": "campaigns",
            "priority": 1,
            "complexity": "L",
            "status": "In Progress",
            "agents": ["crm_backend_agent"],
            "depends_on": [],
        },
        {
            "id": "UC-CRM-002",
            "name": "Segment Builder",
            "domain": "segments",
            "priority": 0,
            "complexity": "XL",
            "status": "Spec",
            "agents": ["crm_data_agent"],
            "depends_on": ["UC-CRM-003"],
        },
        {
            "id": "UC-CRM-003",
            "name": "Contact Import",
            "domain": "contacts",
            "priority": 2,
            "complexity": "M",
            "status": "Done",
            "agents": [],
            "depends_on": [],
        },
    ]


# ==================================================================
# TestUseCaseRegistryInit
# ==================================================================


class TestUseCaseRegistryInit:
    """UseCaseRegistry initialization."""

    def test_init_with_graph(self):
        graph = _make_graph_mock()
        registry = UseCaseRegistry(graph_manager=graph)
        assert registry._graph is graph

    def test_init_without_graph(self):
        registry = UseCaseRegistry()
        assert registry._graph is None

    @patch("src.neural_link.graph.manager.GraphManager.from_env")
    def test_ensure_graph_lazy_init(self, mock_from_env):
        mock_from_env.return_value = _make_graph_mock()
        registry = UseCaseRegistry()
        registry._ensure_graph()
        mock_from_env.assert_called_once()
        assert registry._graph is not None


# ==================================================================
# TestUseCaseRegistryQueries
# ==================================================================


class TestUseCaseRegistryQueries:
    """Query methods with mocked graph."""

    def test_get_by_domain(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [{"id": "UC-CRM-001", "name": "Test"}]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_domain("campaigns")

        assert len(result) == 1
        assert result[0]["id"] == "UC-CRM-001"
        graph.execute_read.assert_called_once()

    def test_get_by_status(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [{"id": "UC-CRM-002"}]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_status("Spec")

        assert len(result) == 1

    def test_get_by_id_found(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [{"id": "UC-CRM-001", "name": "Campaign Blast"}]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_id("UC-CRM-001")

        assert result is not None
        assert result["name"] == "Campaign Blast"

    def test_get_by_id_not_found(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = []
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_id("UC-NONEXISTENT")

        assert result is None

    def test_get_roadmap(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = _sample_usecases()
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_roadmap()

        assert len(result) == 3

    def test_get_agent_coverage(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [
            {"agent_id": "crm_backend_agent", "usecase_count": 5},
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_agent_coverage()

        assert len(result) == 1
        assert result[0]["usecase_count"] == 5

    def test_get_skill_gaps(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [
            {"usecase_id": "UC-CRM-010", "skill_id": "new_skill"},
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_skill_gaps()

        assert len(result) == 1

    def test_search(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = [{"id": "UC-CRM-001"}]
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.search("campaign")

        assert len(result) == 1

    def test_get_all(self):
        graph = _make_graph_mock()
        graph.execute_read.return_value = _sample_usecases()
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_all()

        assert len(result) == 3


# ==================================================================
# TestQueryErrorHandling
# ==================================================================


class TestQueryErrorHandling:
    """Query methods return safe defaults on error."""

    def test_get_by_domain_error(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = RuntimeError("Neo4j down")
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_domain("campaigns")

        assert result == []

    def test_get_by_id_error(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = RuntimeError("Neo4j down")
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.get_by_id("UC-CRM-001")

        assert result is None

    def test_search_error(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = RuntimeError("Neo4j down")
        registry = UseCaseRegistry(graph_manager=graph)

        result = registry.search("test")

        assert result == []


# ==================================================================
# TestExportRoadmapMd
# ==================================================================


class TestExportRoadmapMd:
    """export_roadmap_md generates valid Markdown."""

    def test_basic_roadmap_structure(self):
        graph = _make_graph_mock()
        # get_roadmap call
        graph.execute_read.side_effect = [
            _sample_usecases(),  # roadmap
            [],  # coverage
            [],  # gaps
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "# ROADMAP AI-First" in md
        assert "## Use Cases por Dominio" in md
        assert "UC-CRM-001" in md
        assert "Campaign Blast" in md

    def test_roadmap_groups_by_domain(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            _sample_usecases(),
            [],
            [],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "### Campaigns" in md
        assert "### Segments" in md
        assert "### Contacts" in md

    def test_roadmap_includes_table_header(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            _sample_usecases(),
            [],
            [],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "| ID | Nome | Priority" in md
        assert "|---|---|" in md

    def test_roadmap_with_coverage(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            _sample_usecases(),
            [{"agent_name": "crm_backend_agent", "usecase_ids": ["UC-CRM-001"], "usecase_count": 1}],
            [],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "## Cobertura de Agentes" in md
        assert "crm_backend_agent" in md

    def test_roadmap_with_gaps(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            _sample_usecases(),
            [],
            [{"usecase_name": "Segment Builder", "skill_name": "clickhouse_query", "criticality": "required"}],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "## Skill Gaps" in md
        assert "clickhouse_query" in md

    def test_roadmap_writes_to_file(self, tmp_path):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            _sample_usecases(),
            [],
            [],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        out = tmp_path / "roadmap.md"
        md = registry.export_roadmap_md(output_path=out)

        assert out.exists()
        assert out.read_text(encoding="utf-8") == md

    def test_empty_roadmap(self):
        graph = _make_graph_mock()
        graph.execute_read.side_effect = [
            [],  # no usecases
            [],
            [],
        ]
        registry = UseCaseRegistry(graph_manager=graph)

        md = registry.export_roadmap_md()

        assert "# ROADMAP AI-First" in md
        # No domain tables, but header still present
        assert "UC-CRM" not in md
