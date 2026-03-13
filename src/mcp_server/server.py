"""
MCP Server for engine-service — Exposes HybridRAG, GraphManager, and agent
orchestration via the Model Context Protocol.

Usage:
    python -m src.mcp_server.server

The server lazily initializes all heavy dependencies (Neo4j, ChromaDB,
HybridRAG) on the first tool call so importing this module is cheap.
"""

import logging

from mcp.server.fastmcp import FastMCP

logger = logging.getLogger(__name__)

mcp = FastMCP(
    "engine-service",
    description=(
        "HybridRAG knowledge base with multi-agent orchestration, "
        "graph-augmented retrieval, and 4-layer cost-optimized pipeline"
    ),
)

# ---------------------------------------------------------------------------
# Lazy singletons — populated on first tool invocation
# ---------------------------------------------------------------------------

_hybrid_rag = None
_graph_manager = None
_graph_retriever = None


def _ensure_rag():
    """Initialize HybridRAG (+ Neo4j if available) once."""
    global _hybrid_rag
    if _hybrid_rag is not None:
        return _hybrid_rag

    try:
        from src.neural_link.rag.hybrid_rag import HybridRAG

        _hybrid_rag = HybridRAG.from_env()
        logger.info("MCP: HybridRAG initialized")
    except Exception as exc:
        logger.warning("MCP: HybridRAG init failed (%s), creating minimal instance", exc)
        from src.neural_link.rag.hybrid_rag import HybridRAG

        _hybrid_rag = HybridRAG()

    return _hybrid_rag


def _ensure_graph():
    """Initialize GraphManager once. Returns None when Neo4j is unavailable."""
    global _graph_manager
    if _graph_manager is not None:
        return _graph_manager

    try:
        from src.neural_link.graph.manager import GraphManager

        gm = GraphManager.from_env()
        if gm.verify_connectivity():
            _graph_manager = gm
            logger.info("MCP: GraphManager connected")
        else:
            logger.warning("MCP: Neo4j connectivity check failed")
    except Exception as exc:
        logger.warning("MCP: GraphManager init failed: %s", exc)

    return _graph_manager


def _ensure_graph_retriever():
    """Initialize GraphRetriever (requires GraphManager)."""
    global _graph_retriever
    if _graph_retriever is not None:
        return _graph_retriever

    gm = _ensure_graph()
    if gm is None:
        return None

    try:
        from src.neural_link.rag.graph_retriever import GraphRetriever

        _graph_retriever = GraphRetriever(gm)
        logger.info("MCP: GraphRetriever initialized")
    except Exception as exc:
        logger.warning("MCP: GraphRetriever init failed: %s", exc)

    return _graph_retriever


# ---------------------------------------------------------------------------
# Register tool module — tools.py decorates @mcp.tool() on import
# ---------------------------------------------------------------------------

# Import tools so they register themselves with the mcp instance above.
from . import tools  # noqa: E402, F401

# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mcp.run()
