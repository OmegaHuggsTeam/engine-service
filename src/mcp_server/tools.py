"""
MCP Tools for engine-service.

8 tools exposed via FastMCP:
    rag_search        — HybridRAG semantic + graph + keyword fusion search
    graph_query       — Read-only Cypher against Neo4j (write ops blocked)
    graph_concepts    — List concepts with domains and connection counts
    ingest_document   — Ingest a file into the knowledge base
    list_agents       — List registered AI agents
    agent_execute     — Dispatch a task to a specific agent
    search_errors     — Search the error resolution graph
    pipeline_stats    — Pipeline telemetry (cache, latency, cost, agents)
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path

logger = logging.getLogger(__name__)

# Import the shared FastMCP instance and lazy-init helpers from server.py.
from .server import mcp, _ensure_rag, _ensure_graph, _ensure_graph_retriever

# ---------------------------------------------------------------------------
# Security: blocked keywords for graph_query
# ---------------------------------------------------------------------------

BLOCKED_KEYWORDS = {
    "create", "merge", "delete", "set", "remove", "drop", "call", "detach",
}


def _validate_cypher_readonly(cypher: str) -> None:
    """Raise ValueError if the Cypher query contains write operations."""
    query_lower = cypher.strip().lower()
    for kw in BLOCKED_KEYWORDS:
        if kw in query_lower.split():
            raise ValueError(f"Write operations not allowed. Blocked keyword: {kw}")


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


@mcp.tool()
async def rag_search(query: str, top_k: int = 5) -> str:
    """Search the knowledge base using HybridRAG (semantic + graph + keyword fusion).

    Returns ranked results with source, score, and engine attribution.
    """
    try:
        rag = _ensure_rag()
        # HybridRAG.query() is synchronous — run in thread to avoid blocking
        results = await asyncio.to_thread(rag.query, query, top_k)
        return json.dumps(results, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("rag_search failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def graph_query(cypher: str) -> str:
    """Execute a read-only Cypher query against Neo4j knowledge graph.

    Returns list of records as JSON.
    SECURITY: Write operations (CREATE, MERGE, DELETE, SET, REMOVE, DROP, CALL, DETACH) are blocked.
    """
    _validate_cypher_readonly(cypher)

    gm = _ensure_graph()
    if gm is None:
        return json.dumps({"error": "Neo4j is not available"})

    try:
        records = await asyncio.to_thread(gm.execute_read, cypher)
        return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("graph_query failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def graph_concepts(limit: int = 50) -> str:
    """List concepts in the knowledge graph with their domains and connection counts."""
    gm = _ensure_graph()
    if gm is None:
        return json.dumps({"error": "Neo4j is not available"})

    cypher = (
        "MATCH (c:Concept) "
        "OPTIONAL MATCH (c)<-[r:MENTIONS]-() "
        "RETURN c.name AS name, c.domain AS domain, count(r) AS connection_count "
        "ORDER BY connection_count DESC "
        "LIMIT $limit"
    )

    try:
        records = await asyncio.to_thread(gm.execute_read, cypher, {"limit": limit})
        return json.dumps(records, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("graph_concepts failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def ingest_document(file_path: str, category: str = "documents") -> str:
    """Ingest a document into the knowledge base.

    Supports: PDF, DOCX, PPTX, HTML, PNG, JPG, TXT, MD, JSON.
    Returns chunk count and metadata.
    """
    fp = Path(file_path)
    if not fp.exists():
        return json.dumps({"error": f"File not found: {file_path}"})

    chunks: list[dict] = []

    # Try Docling extractor first for complex document types
    try:
        from src.extractors.docling_extractor import is_docling_compatible, extract_with_docling

        if is_docling_compatible(fp):
            chunks = await extract_with_docling(fp, category=category)
    except Exception as exc:
        logger.warning("Docling extraction failed for %s: %s — falling back to text chunking", fp.name, exc)

    # Fallback: simple text-based chunking for TXT / MD / JSON or when Docling fails
    if not chunks:
        try:
            text = fp.read_text(encoding="utf-8", errors="replace")
            if not text.strip():
                return json.dumps({"error": "File is empty", "file": fp.name})

            # Simple fixed-size chunking
            chunk_size = 2000
            overlap = 200
            idx = 0
            pos = 0
            while pos < len(text):
                end = min(pos + chunk_size, len(text))
                chunk_text = text[pos:end]
                if chunk_text.strip():
                    chunks.append({
                        "content": chunk_text,
                        "source_file": fp.name,
                        "category": category,
                        "chunk_index": idx,
                        "char_count": len(chunk_text),
                    })
                    idx += 1
                pos += chunk_size - overlap
        except Exception as exc:
            return json.dumps({"error": f"Failed to read file: {exc}", "file": fp.name})

    if not chunks:
        return json.dumps({"error": "No content extracted", "file": fp.name})

    # Persist to ChromaDB
    try:
        from src.utils.vector_db import add_chunks

        inserted = await asyncio.to_thread(add_chunks, chunks)
        return json.dumps({
            "status": "ok",
            "file": fp.name,
            "chunks_ingested": inserted,
            "category": category,
        })
    except Exception as exc:
        logger.error("ChromaDB ingestion failed: %s", exc)
        return json.dumps({"error": f"Ingestion failed: {exc}", "file": fp.name})


@mcp.tool()
async def list_agents() -> str:
    """List all available AI agents with capabilities and status."""
    try:
        from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

        agents = []
        for agent_id, info in AGENT_REGISTRY.items():
            agents.append({
                "id": agent_id,
                "name": info.get("name", agent_id),
                "type": info.get("type", "unknown"),
                "capabilities": sorted(info.get("capabilities", set())),
                "status": "active",
            })

        return json.dumps(agents, ensure_ascii=False)
    except Exception as exc:
        logger.error("list_agents failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def agent_execute(agent_id: str, task: str) -> str:
    """Dispatch a task to a specific agent.

    Returns response with execution metadata.
    Timeout: 30 seconds.
    """
    try:
        from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

        info = AGENT_REGISTRY.get(agent_id)
        if not info:
            return json.dumps({"error": f"Agent '{agent_id}' not found in registry"})

        module_path = info.get("module_path", "")
        agent_class = info.get("agent_class")
        invoke_method = info.get("invoke", "execute")

        if not module_path:
            return json.dumps({"error": f"Agent '{agent_id}' has no module_path configured"})

        import importlib

        mod = importlib.import_module(module_path)
        if agent_class:
            cls = getattr(mod, agent_class)
            agent_instance = cls()
        else:
            agent_instance = mod

        fn = getattr(agent_instance, invoke_method)

        start = time.time()

        # Run with timeout
        if asyncio.iscoroutinefunction(fn):
            result = await asyncio.wait_for(fn(task), timeout=30)
        else:
            result = await asyncio.wait_for(asyncio.to_thread(fn, task), timeout=30)

        elapsed_ms = (time.time() - start) * 1000

        return json.dumps({
            "agent_id": agent_id,
            "agent_name": info.get("name", agent_id),
            "result": str(result),
            "execution_time_ms": round(elapsed_ms, 1),
        }, ensure_ascii=False, default=str)

    except asyncio.TimeoutError:
        return json.dumps({"error": f"Agent '{agent_id}' timed out after 30s"})
    except Exception as exc:
        logger.error("agent_execute failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def search_errors(error_type: str, error_message: str = "") -> str:
    """Search the error resolution graph for known fixes.

    Uses Error->RESOLVED_BY->Skill relationships in Neo4j.
    """
    gr = _ensure_graph_retriever()
    if gr is None:
        return json.dumps({"error": "Neo4j / GraphRetriever is not available"})

    try:
        results = await asyncio.to_thread(
            gr.search_error_resolution, error_type, error_message, 5,
        )
        return json.dumps(results, ensure_ascii=False, default=str)
    except Exception as exc:
        logger.error("search_errors failed: %s", exc)
        return json.dumps({"error": str(exc)})


@mcp.tool()
async def pipeline_stats() -> str:
    """Get pipeline statistics: cache hit rate, latency, cost, active agents."""
    stats: dict = {
        "neo4j_connected": False,
        "chromadb_chunks": 0,
        "active_agents": 0,
        "cache": {},
        "cost": {},
    }

    # Neo4j status
    gm = _ensure_graph()
    if gm is not None:
        stats["neo4j_connected"] = True

    # ChromaDB chunk count
    try:
        from src.utils.vector_db import count

        stats["chromadb_chunks"] = await asyncio.to_thread(count)
    except Exception as exc:
        stats["chromadb_error"] = str(exc)

    # Agent count
    try:
        from src.neural_link.orchestrator.agent_selector import AGENT_REGISTRY

        stats["active_agents"] = len(AGENT_REGISTRY)
    except Exception:
        pass

    # Pipeline cache stats
    try:
        from src.neural_link.orchestrator.pipeline_cache import PipelineCache

        cache = PipelineCache()
        stats["cache"] = {
            "size": cache._cache_size if hasattr(cache, "_cache_size") else len(getattr(cache, "_cache", {})),
        }
    except Exception:
        pass

    # Cost tracker stats
    try:
        from src.neural_link.telemetry.cost_tracker import CostTracker

        tracker = CostTracker()
        stats["cost"] = tracker.stats
    except Exception:
        pass

    return json.dumps(stats, ensure_ascii=False, default=str)
