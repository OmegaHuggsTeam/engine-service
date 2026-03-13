"""
Tests for the MCP Server component (src/mcp_server).

All external dependencies (HybridRAG, GraphManager, GraphRetriever, ChromaDB,
agent modules) are mocked so tests run without Neo4j, ChromaDB, or LLM keys.
"""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch, AsyncMock

import pytest


# ==================================================================
# Helpers — mock the lazy-init singletons before importing tools
# ==================================================================


def _reset_server_singletons():
    """Reset module-level singletons in server.py between tests."""
    import src.mcp_server.server as srv
    srv._hybrid_rag = None
    srv._graph_manager = None
    srv._graph_retriever = None


@pytest.fixture(autouse=True)
def _clean_singletons():
    """Ensure singletons are reset before and after every test."""
    _reset_server_singletons()
    yield
    _reset_server_singletons()


# ==================================================================
# TestRagSearch
# ==================================================================


class TestRagSearch:
    """Tests for rag_search tool."""

    @pytest.mark.asyncio
    async def test_returns_valid_json(self):
        """rag_search returns a JSON-serialized list of results."""
        mock_rag = MagicMock()
        mock_rag.query.return_value = [
            {"content": "chunk1", "score": 0.9, "engine": "chroma"},
            {"content": "chunk2", "score": 0.7, "engine": "neo4j"},
        ]

        import src.mcp_server.server as srv
        srv._hybrid_rag = mock_rag

        from src.mcp_server.tools import rag_search

        result = await rag_search("what is RAG?", top_k=3)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["score"] == 0.9

    @pytest.mark.asyncio
    async def test_returns_error_on_failure(self):
        """rag_search returns JSON error when HybridRAG raises."""
        mock_rag = MagicMock()
        mock_rag.query.side_effect = RuntimeError("connection lost")

        import src.mcp_server.server as srv
        srv._hybrid_rag = mock_rag

        from src.mcp_server.tools import rag_search

        result = await rag_search("test query")
        parsed = json.loads(result)
        assert "error" in parsed

    @pytest.mark.asyncio
    async def test_calls_query_with_top_k(self):
        """rag_search passes top_k to HybridRAG.query()."""
        mock_rag = MagicMock()
        mock_rag.query.return_value = []

        import src.mcp_server.server as srv
        srv._hybrid_rag = mock_rag

        from src.mcp_server.tools import rag_search

        await rag_search("q", top_k=7)
        mock_rag.query.assert_called_once_with("q", 7)


# ==================================================================
# TestGraphQuery
# ==================================================================


class TestGraphQuery:
    """Tests for graph_query tool — security and read-only enforcement."""

    @pytest.mark.asyncio
    async def test_blocks_create(self):
        """CREATE keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: create"):
            await graph_query("CREATE (n:Node {name: 'test'})")

    @pytest.mark.asyncio
    async def test_blocks_merge(self):
        """MERGE keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: merge"):
            await graph_query("MERGE (n:Node {id: 1})")

    @pytest.mark.asyncio
    async def test_blocks_delete(self):
        """DELETE keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: delete"):
            await graph_query("MATCH (n) DELETE n")

    @pytest.mark.asyncio
    async def test_blocks_set(self):
        """SET keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: set"):
            await graph_query("MATCH (n) SET n.name = 'x'")

    @pytest.mark.asyncio
    async def test_blocks_remove(self):
        """REMOVE keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: remove"):
            await graph_query("MATCH (n) REMOVE n.name")

    @pytest.mark.asyncio
    async def test_blocks_drop(self):
        """DROP keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: drop"):
            await graph_query("DROP INDEX my_index")

    @pytest.mark.asyncio
    async def test_blocks_call(self):
        """CALL keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: call"):
            await graph_query("CALL db.schema.visualization()")

    @pytest.mark.asyncio
    async def test_blocks_detach(self):
        """DETACH keyword is blocked."""
        from src.mcp_server.tools import graph_query

        with pytest.raises(ValueError, match="Blocked keyword: detach"):
            await graph_query("MATCH (n) DETACH DELETE n")

    @pytest.mark.asyncio
    async def test_allows_match_return(self):
        """MATCH ... RETURN is allowed (read-only)."""
        mock_gm = MagicMock()
        mock_gm.execute_read.return_value = [{"name": "test"}]

        import src.mcp_server.server as srv
        srv._graph_manager = mock_gm

        from src.mcp_server.tools import graph_query

        result = await graph_query("MATCH (n:Concept) RETURN n.name AS name LIMIT 10")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert parsed[0]["name"] == "test"

    @pytest.mark.asyncio
    async def test_allows_match_where_return(self):
        """MATCH ... WHERE ... RETURN is allowed."""
        mock_gm = MagicMock()
        mock_gm.execute_read.return_value = []

        import src.mcp_server.server as srv
        srv._graph_manager = mock_gm

        from src.mcp_server.tools import graph_query

        result = await graph_query(
            "MATCH (n:Concept) WHERE n.domain = 'CRM' RETURN n.name"
        )
        parsed = json.loads(result)
        assert isinstance(parsed, list)

    @pytest.mark.asyncio
    async def test_returns_error_when_neo4j_unavailable(self):
        """Returns JSON error when graph manager is None."""
        import src.mcp_server.server as srv
        srv._graph_manager = None

        # Patch _ensure_graph to return None
        with patch("src.mcp_server.tools._ensure_graph", return_value=None):
            from src.mcp_server.tools import graph_query

            result = await graph_query("MATCH (n) RETURN n LIMIT 1")
            parsed = json.loads(result)
            assert "error" in parsed
            assert "not available" in parsed["error"]


# ==================================================================
# TestGraphConcepts
# ==================================================================


class TestGraphConcepts:
    """Tests for graph_concepts tool."""

    @pytest.mark.asyncio
    async def test_returns_structured_data(self):
        """graph_concepts returns list with name, domain, connection_count."""
        mock_gm = MagicMock()
        mock_gm.execute_read.return_value = [
            {"name": "RAG", "domain": "AI", "connection_count": 15},
            {"name": "Campaign", "domain": "CRM", "connection_count": 8},
        ]

        import src.mcp_server.server as srv
        srv._graph_manager = mock_gm

        from src.mcp_server.tools import graph_concepts

        result = await graph_concepts(limit=10)
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 2
        assert parsed[0]["name"] == "RAG"
        assert parsed[0]["connection_count"] == 15

    @pytest.mark.asyncio
    async def test_returns_error_when_neo4j_unavailable(self):
        """Returns error JSON when Neo4j is not connected."""
        with patch("src.mcp_server.tools._ensure_graph", return_value=None):
            from src.mcp_server.tools import graph_concepts

            result = await graph_concepts()
            parsed = json.loads(result)
            assert "error" in parsed


# ==================================================================
# TestIngestDocument
# ==================================================================


class TestIngestDocument:
    """Tests for ingest_document tool."""

    @pytest.mark.asyncio
    async def test_validates_file_existence(self):
        """Returns error when file does not exist."""
        from src.mcp_server.tools import ingest_document

        result = await ingest_document("/nonexistent/path/doc.pdf")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"].lower()

    @pytest.mark.asyncio
    async def test_ingests_text_file(self, tmp_path):
        """Successfully ingests a text file with simple chunking."""
        txt_file = tmp_path / "notes.txt"
        txt_file.write_text("Hello world. " * 50, encoding="utf-8")

        mock_add_chunks = MagicMock(return_value=1)

        with patch("src.mcp_server.tools.add_chunks", mock_add_chunks):
            # We also need to patch the import inside the function
            from src.mcp_server.tools import ingest_document

            with patch("src.mcp_server.tools.add_chunks", mock_add_chunks):
                result = await ingest_document(str(txt_file), category="notes")

        parsed = json.loads(result)
        assert parsed.get("status") == "ok" or "chunks_ingested" in parsed or "error" not in parsed

    @pytest.mark.asyncio
    async def test_empty_file_returns_error(self, tmp_path):
        """Empty file returns error."""
        empty = tmp_path / "empty.txt"
        empty.write_text("", encoding="utf-8")

        from src.mcp_server.tools import ingest_document

        result = await ingest_document(str(empty))
        parsed = json.loads(result)
        assert "error" in parsed


# ==================================================================
# TestListAgents
# ==================================================================


class TestListAgents:
    """Tests for list_agents tool."""

    @pytest.mark.asyncio
    async def test_returns_agent_info(self):
        """list_agents returns structured list with id, name, type, capabilities."""
        from src.mcp_server.tools import list_agents

        result = await list_agents()
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) > 0

        # Check first agent has required fields
        agent = parsed[0]
        assert "id" in agent
        assert "name" in agent
        assert "type" in agent
        assert "capabilities" in agent
        assert "status" in agent

    @pytest.mark.asyncio
    async def test_capabilities_are_sorted(self):
        """Agent capabilities are sorted alphabetically."""
        from src.mcp_server.tools import list_agents

        result = await list_agents()
        parsed = json.loads(result)

        for agent in parsed:
            caps = agent["capabilities"]
            assert caps == sorted(caps), f"Capabilities not sorted for {agent['id']}"

    @pytest.mark.asyncio
    async def test_contains_known_agents(self):
        """Registry contains known agents like marketing_agent and ai_engineer_agent."""
        from src.mcp_server.tools import list_agents

        result = await list_agents()
        parsed = json.loads(result)
        ids = {a["id"] for a in parsed}
        assert "marketing_agent" in ids
        assert "ai_engineer_agent" in ids


# ==================================================================
# TestAgentExecute
# ==================================================================


class TestAgentExecute:
    """Tests for agent_execute tool."""

    @pytest.mark.asyncio
    async def test_unknown_agent_returns_error(self):
        """Dispatching to nonexistent agent returns error."""
        from src.mcp_server.tools import agent_execute

        result = await agent_execute("nonexistent_agent_xyz", "do something")
        parsed = json.loads(result)
        assert "error" in parsed
        assert "not found" in parsed["error"]

    @pytest.mark.asyncio
    async def test_successful_execution(self):
        """Successful agent execution returns result with metadata."""
        mock_agent_instance = MagicMock()
        mock_agent_instance.execute.return_value = "task completed"

        mock_module = MagicMock()
        mock_module.MarketingDomainAgent.return_value = mock_agent_instance

        with patch("importlib.import_module", return_value=mock_module):
            from src.mcp_server.tools import agent_execute

            result = await agent_execute("marketing_agent", "write a campaign")

        parsed = json.loads(result)
        assert parsed["agent_id"] == "marketing_agent"
        assert "task completed" in parsed["result"]
        assert "execution_time_ms" in parsed


# ==================================================================
# TestSearchErrors
# ==================================================================


class TestSearchErrors:
    """Tests for search_errors tool."""

    @pytest.mark.asyncio
    async def test_uses_graph_retriever(self):
        """search_errors delegates to GraphRetriever.search_error_resolution."""
        mock_gr = MagicMock()
        mock_gr.search_error_resolution.return_value = [
            {
                "content": "Error: TypeError\nResolution: fix_types",
                "source_file": "error_resolution",
                "score": 0.8,
                "engine": "neo4j",
                "error_type": "TypeError",
                "skill_name": "fix_types",
            }
        ]

        import src.mcp_server.server as srv
        srv._graph_retriever = mock_gr

        from src.mcp_server.tools import search_errors

        result = await search_errors("TypeError", "unexpected NoneType")
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["error_type"] == "TypeError"

        mock_gr.search_error_resolution.assert_called_once_with("TypeError", "unexpected NoneType", 5)

    @pytest.mark.asyncio
    async def test_returns_error_when_neo4j_unavailable(self):
        """Returns error when GraphRetriever is None."""
        import src.mcp_server.server as srv
        srv._graph_retriever = None

        with patch("src.mcp_server.tools._ensure_graph_retriever", return_value=None):
            from src.mcp_server.tools import search_errors

            result = await search_errors("KeyError")
            parsed = json.loads(result)
            assert "error" in parsed


# ==================================================================
# TestPipelineStats
# ==================================================================


class TestPipelineStats:
    """Tests for pipeline_stats tool."""

    @pytest.mark.asyncio
    async def test_returns_stats_dict(self):
        """pipeline_stats returns a dict with expected keys."""
        mock_gm = MagicMock()
        mock_gm.verify_connectivity.return_value = True

        import src.mcp_server.server as srv
        srv._graph_manager = mock_gm

        with patch("src.mcp_server.tools.count", return_value=42):
            from src.mcp_server.tools import pipeline_stats

            result = await pipeline_stats()

        parsed = json.loads(result)
        assert isinstance(parsed, dict)
        assert parsed["neo4j_connected"] is True
        assert parsed["chromadb_chunks"] == 42
        assert parsed["active_agents"] > 0

    @pytest.mark.asyncio
    async def test_graceful_when_neo4j_down(self):
        """pipeline_stats works even when Neo4j is unavailable."""
        import src.mcp_server.server as srv
        srv._graph_manager = None

        with (
            patch("src.mcp_server.tools._ensure_graph", return_value=None),
            patch("src.mcp_server.tools.count", side_effect=Exception("chromadb down")),
        ):
            from src.mcp_server.tools import pipeline_stats

            result = await pipeline_stats()

        parsed = json.loads(result)
        assert parsed["neo4j_connected"] is False


# ==================================================================
# TestCypherValidation
# ==================================================================


class TestCypherValidation:
    """Tests for _validate_cypher_readonly helper."""

    def test_blocked_keywords_all_rejected(self):
        """Every keyword in BLOCKED_KEYWORDS raises ValueError."""
        from src.mcp_server.tools import _validate_cypher_readonly, BLOCKED_KEYWORDS

        for kw in BLOCKED_KEYWORDS:
            with pytest.raises(ValueError, match=f"Blocked keyword: {kw}"):
                _validate_cypher_readonly(f"MATCH (n) {kw.upper()} n")

    def test_read_queries_pass(self):
        """Standard read queries pass validation."""
        from src.mcp_server.tools import _validate_cypher_readonly

        # These should NOT raise
        _validate_cypher_readonly("MATCH (n) RETURN n")
        _validate_cypher_readonly("MATCH (n:Concept)-[r]->(m) RETURN n, r, m")
        _validate_cypher_readonly("MATCH (n) WHERE n.name = 'test' RETURN n LIMIT 10")
        _validate_cypher_readonly("MATCH (n) WITH n ORDER BY n.name RETURN n")

    def test_keyword_in_string_literal_not_blocked(self):
        """Keywords inside string values are NOT blocked (word-boundary check).

        The split()-based check only blocks standalone tokens, so 'created_at'
        is fine but 'CREATE (n)' is blocked.
        """
        from src.mcp_server.tools import _validate_cypher_readonly

        # 'created_at' contains 'create' as substring but not as a standalone word
        _validate_cypher_readonly("MATCH (n) WHERE n.created_at > '2024-01-01' RETURN n")
        # 'settings' contains 'set' as substring
        _validate_cypher_readonly("MATCH (n:Settings) RETURN n")
