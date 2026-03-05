"""
HybridRAG - Orquestra 3 motores de busca: ChromaDB, Neo4j e TF-IDF.
Usa QueryRouter para definir pesos e ResultMerger para combinar resultados.
"""

import logging
from typing import Optional

from .query_router import QueryRouter
from .result_merger import ResultMerger
from .concept_extractor import extract_concepts, get_known_concept_names

logger = logging.getLogger(__name__)


class HybridRAG:
    """
    RAG hibrido que combina ChromaDB (semantico), Neo4j (grafo) e TF-IDF (exato).
    """

    def __init__(
        self,
        graph_manager=None,
        graph_retriever=None,
        router: QueryRouter | None = None,
        merger: ResultMerger | None = None,
    ):
        self._graph = graph_manager
        self._graph_retriever = graph_retriever
        self._router = router or QueryRouter()
        self._merger = merger or ResultMerger()
        self._tfidf_system = None
        self._neo4j_available = graph_manager is not None

    @classmethod
    def from_env(cls) -> "HybridRAG":
        """Cria HybridRAG a partir do ambiente. Neo4j e opcional."""
        graph_manager = None
        graph_retriever = None

        try:
            from ..graph.manager import GraphManager
            from .graph_retriever import GraphRetriever

            gm = GraphManager.from_env()
            if gm.verify_connectivity():
                graph_manager = gm
                graph_retriever = GraphRetriever(gm)
                logger.info("HybridRAG: Neo4j connected")
            else:
                logger.warning("HybridRAG: Neo4j not available, running without graph")
        except Exception as e:
            logger.warning(f"HybridRAG: Neo4j not available ({e}), running without graph")

        return cls(
            graph_manager=graph_manager,
            graph_retriever=graph_retriever,
        )

    def query(
        self,
        query_text: str,
        top_k: int = 10,
        context: Optional[dict] = None,
    ) -> list[dict]:
        """
        Busca hibrida em todos os motores disponiveis.

        Args:
            query_text: Texto da query
            top_k: Numero maximo de resultados
            context: Contexto adicional (ex: error_type para error resolution)

        Returns:
            Lista de resultados ordenados por relevancia, com score normalizado
        """
        if not query_text or not query_text.strip():
            return []

        # Rotear query para definir pesos
        routing = self._router.route(query_text)
        weights = {
            "chroma": routing["chroma"],
            "neo4j": routing["neo4j"],
            "tfidf": routing["tfidf"],
        }

        logger.info(
            f"HybridRAG query: type={routing['query_type']}, "
            f"weights=chroma:{weights['chroma']:.2f} neo4j:{weights['neo4j']:.2f} tfidf:{weights['tfidf']:.2f}"
        )

        # Buscar em paralelo (sequencialmente por simplicidade, mas isolado)
        results_by_engine = {}

        # Motor 1: ChromaDB (semantico)
        chroma_results = self._search_chroma(query_text, top_k)
        if chroma_results:
            results_by_engine["chroma"] = chroma_results

        # Motor 2: Neo4j (grafo)
        if self._neo4j_available and self._graph_retriever:
            neo4j_results = self._search_neo4j(query_text, top_k, routing, context)
            if neo4j_results:
                results_by_engine["neo4j"] = neo4j_results

        # Motor 3: TF-IDF (exato)
        tfidf_results = self._search_tfidf(query_text, top_k)
        if tfidf_results:
            results_by_engine["tfidf"] = tfidf_results

        if not results_by_engine:
            logger.warning("HybridRAG: No results from any engine")
            return []

        # Merge e rerank
        merged = self._merger.merge(results_by_engine, weights, top_k)

        logger.info(f"HybridRAG: {len(merged)} results (engines used: {list(results_by_engine.keys())})")
        return merged

    def _search_chroma(self, query_text: str, top_k: int) -> list[dict]:
        """Busca semantica via ChromaDB."""
        try:
            from src.utils.vector_db import search_with_scores

            results = search_with_scores(query_text, top_k=top_k)
            for r in results:
                r["engine"] = "chroma"
            return results
        except Exception as e:
            logger.warning(f"ChromaDB search failed: {e}")
            return []

    def _search_neo4j(
        self, query_text: str, top_k: int, routing: dict, context: Optional[dict]
    ) -> list[dict]:
        """Busca no grafo Neo4j - conceitos + fulltext + error resolution."""
        results = []

        try:
            # Extrair conceitos da query
            known = get_known_concept_names(self._graph) if self._graph else []
            concepts = extract_concepts(query_text, known_concepts=known)
            concept_names = [c["name"] for c in concepts]

            if concept_names:
                concept_results = self._graph_retriever.search_by_concepts(
                    concept_names, top_k=top_k
                )
                results.extend(concept_results)

            # Fulltext search tambem
            fulltext_results = self._graph_retriever.search_fulltext(query_text, top_k=top_k)
            results.extend(fulltext_results)

            # Error resolution se query parece ser sobre erros
            if routing.get("query_type") == "error_resolution":
                error_type = (context or {}).get("error_type", query_text[:50])
                error_msg = (context or {}).get("error_message", query_text)
                error_results = self._graph_retriever.search_error_resolution(
                    error_type, error_msg, top_k=5
                )
                results.extend(error_results)

        except Exception as e:
            logger.warning(f"Neo4j search failed: {e}")

        return results

    def _search_tfidf(self, query_text: str, top_k: int) -> list[dict]:
        """Busca TF-IDF via RAGQuerySystem existente."""
        try:
            if self._tfidf_system is None:
                from src.rag.rag_query_system import RAGQuerySystem
                self._tfidf_system = RAGQuerySystem()

            return self._tfidf_system.query_with_scores(query_text, top_k=top_k)
        except Exception as e:
            logger.warning(f"TF-IDF search failed: {e}")
            return []
