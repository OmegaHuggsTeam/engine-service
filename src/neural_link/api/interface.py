"""
UnifiedInterface - Ponto de entrada unico para o Neural Link.
Singleton com metodos process, search, status, stats.
"""

import logging
import threading

logger = logging.getLogger(__name__)

_instance = None
_instance_lock = threading.Lock()


class UnifiedInterface:
    """
    Interface unificada do Neural Link.
    Singleton: compartilha orchestrator, RAG e grafo entre chamadas.
    """

    def __init__(self):
        self._orchestrator = None
        self._hybrid_rag = None
        self._graph = None
        self._initialized = False

    @classmethod
    def get_instance(cls) -> "UnifiedInterface":
        """Retorna singleton."""
        global _instance
        with _instance_lock:
            if _instance is None:
                _instance = cls()
            return _instance

    def _ensure_initialized(self):
        """Inicializa componentes lazy."""
        if self._initialized:
            return

        try:
            from ..orchestrator.core import NeuralLinkOrchestrator
            self._orchestrator = NeuralLinkOrchestrator.from_env()
            self._graph = self._orchestrator._graph
            self._hybrid_rag = self._orchestrator._rag
            self._initialized = True
            logger.info("UnifiedInterface initialized")
        except Exception as e:
            logger.error(f"UnifiedInterface init failed: {e}")
            # Inicializa com componentes minimos
            self._initialized = True

    def process(self, query: str, context: dict | None = None) -> dict:
        """
        Orquestracao completa: RAG + decomposicao + execucao + feedback.

        Args:
            query: Texto do request
            context: Contexto adicional

        Returns:
            dict com answer, tasks, results, enrichment, etc.
        """
        self._ensure_initialized()

        if not self._orchestrator:
            return {"answer": "Neural Link orchestrator not available", "error": True}

        try:
            response = self._orchestrator.process(query, context=context)
            return {
                "answer": response.answer,
                "tasks": [t.model_dump() for t in response.tasks],
                "results": [r.model_dump() for r in response.results],
                "rag_results_count": len(response.rag_results),
                "knowledge_enrichment": response.knowledge_enrichment,
                "session_id": response.session_id,
                "processing_time_ms": response.processing_time_ms,
            }
        except Exception as e:
            logger.error(f"Process failed: {e}")
            return {"answer": f"Error: {str(e)}", "error": True}

    def search(self, query: str, top_k: int = 10) -> list[dict]:
        """
        RAG hibrido direto (sem orquestracao).
        Retorna resultados de busca com scores.
        """
        self._ensure_initialized()

        if not self._hybrid_rag:
            # Fallback para ChromaDB direto
            try:
                from src.utils.vector_db import search_with_scores
                return search_with_scores(query, top_k=top_k)
            except Exception as e:
                return [{"error": str(e)}]

        try:
            return self._hybrid_rag.query(query, top_k=top_k)
        except Exception as e:
            logger.error(f"Search failed: {e}")
            return [{"error": str(e)}]

    def get_agent_status(self) -> list[dict]:
        """Retorna status de todos os agentes."""
        self._ensure_initialized()

        if self._graph:
            try:
                rows = self._graph.execute_read(
                    "MATCH (a:Agent) "
                    "RETURN a.id AS id, a.name AS name, a.type AS type, "
                    "       a.status AS status, a.success_rate AS success_rate "
                    "ORDER BY a.success_rate DESC"
                )
                return [dict(r) for r in rows]
            except Exception:
                pass

        # Fallback: registry estatico
        from ..orchestrator.agent_selector import AGENT_REGISTRY
        return [
            {
                "id": aid,
                "name": info["name"],
                "type": info["type"],
                "status": "active",
                "success_rate": None,
            }
            for aid, info in AGENT_REGISTRY.items()
        ]

    def get_graph_stats(self) -> dict:
        """Retorna estatisticas do grafo de conhecimento."""
        self._ensure_initialized()

        if not self._graph:
            return {"status": "disconnected", "message": "Neo4j not available"}

        try:
            from ..graph.enrichment import get_enrichment_stats
            return get_enrichment_stats(self._graph)
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def health(self) -> dict:
        """Health check do Neural Link."""
        self._ensure_initialized()

        return {
            "status": "ok",
            "orchestrator": self._orchestrator is not None,
            "hybrid_rag": self._hybrid_rag is not None,
            "neo4j": self._graph is not None and self._graph.verify_connectivity()
                     if self._graph else False,
        }
