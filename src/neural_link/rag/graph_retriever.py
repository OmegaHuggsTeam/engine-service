"""
GraphRetriever - Busca no grafo Neo4j para o RAG hibrido.
Oferece busca por conceitos, resolucao de erros e expansao de contexto.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GraphRetriever:
    """Recupera informacao do grafo Neo4j para o pipeline RAG."""

    def __init__(self, graph_manager):
        self._graph = graph_manager

    def search_by_concepts(self, concepts: list[str], top_k: int = 10) -> list[dict]:
        """
        Busca chunks que mencionam os conceitos dados.
        Expande para conceitos relacionados.
        """
        if not concepts:
            return []

        results = []
        seen_ids = set()

        for concept_name in concepts:
            # Busca conceito no grafo
            concept_rows = self._graph.execute_read(
                "MATCH (c:Concept) WHERE toLower(c.name) = toLower($name) "
                "RETURN c.id AS id LIMIT 1",
                {"name": concept_name},
            )

            if not concept_rows:
                continue

            concept_id = concept_rows[0]["id"]

            # Busca chunks que mencionam este conceito
            chunk_rows = self._graph.execute_read(
                "MATCH (ch:Chunk)-[r:MENTIONS]->(c:Concept {id: $concept_id}) "
                "RETURN ch.id AS id, ch.content AS content, ch.source_file AS source_file, "
                "       ch.category AS category, r.confidence AS confidence "
                "ORDER BY r.confidence DESC LIMIT $limit",
                {"concept_id": concept_id, "limit": top_k},
            )

            for row in chunk_rows:
                if row["id"] not in seen_ids:
                    seen_ids.add(row["id"])
                    results.append({
                        "content": row.get("content", ""),
                        "source_file": row.get("source_file", ""),
                        "category": row.get("category", ""),
                        "score": float(row.get("confidence", 0.5)),
                        "engine": "neo4j",
                        "matched_concept": concept_name,
                    })

            # Expande para conceitos relacionados
            related_rows = self._graph.execute_read(
                "MATCH (c:Concept {id: $concept_id})-[r:RELATED_TO]-(related:Concept) "
                "RETURN related.id AS id, related.name AS name, r.weight AS weight "
                "ORDER BY r.weight DESC LIMIT 3",
                {"concept_id": concept_id},
            )

            for related in related_rows:
                related_chunks = self._graph.execute_read(
                    "MATCH (ch:Chunk)-[r:MENTIONS]->(c:Concept {id: $concept_id}) "
                    "RETURN ch.id AS id, ch.content AS content, ch.source_file AS source_file, "
                    "       ch.category AS category, r.confidence AS confidence "
                    "ORDER BY r.confidence DESC LIMIT 3",
                    {"concept_id": related["id"]},
                )

                for row in related_chunks:
                    if row["id"] not in seen_ids:
                        seen_ids.add(row["id"])
                        weight = float(related.get("weight", 0.3))
                        results.append({
                            "content": row.get("content", ""),
                            "source_file": row.get("source_file", ""),
                            "category": row.get("category", ""),
                            "score": float(row.get("confidence", 0.3)) * weight,
                            "engine": "neo4j",
                            "matched_concept": related["name"],
                            "via_relation": True,
                        })

        return sorted(results, key=lambda x: x["score"], reverse=True)[:top_k]

    def search_fulltext(self, query: str, top_k: int = 10) -> list[dict]:
        """Busca fulltext no conteudo dos chunks via Neo4j."""
        try:
            # Escapa caracteres especiais do Lucene
            safe_query = self._escape_lucene(query)
            rows = self._graph.execute_read(
                "CALL db.index.fulltext.queryNodes('chunk_content', $query) "
                "YIELD node, score "
                "RETURN node.id AS id, node.content AS content, "
                "       node.source_file AS source_file, node.category AS category, "
                "       score "
                "ORDER BY score DESC LIMIT $limit",
                {"query": safe_query, "limit": top_k},
            )

            return [
                {
                    "content": row.get("content", ""),
                    "source_file": row.get("source_file", ""),
                    "category": row.get("category", ""),
                    "score": min(1.0, float(row.get("score", 0)) / 5.0),  # Normaliza
                    "engine": "neo4j",
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Neo4j fulltext search failed: {e}")
            return []

    def search_error_resolution(
        self, error_type: str, error_message: str, top_k: int = 5
    ) -> list[dict]:
        """Busca resolucoes de erros similares no grafo."""
        try:
            rows = self._graph.execute_read(
                "MATCH (e:Error)-[:RESOLVED_BY]->(s:Skill) "
                "WHERE toLower(e.error_type) CONTAINS toLower($error_type) "
                "   OR toLower(e.message) CONTAINS toLower($error_message) "
                "RETURN e.error_type AS error_type, e.message AS message, "
                "       s.name AS skill_name, s.code AS skill_code, "
                "       e.frequency AS frequency "
                "ORDER BY e.frequency DESC LIMIT $limit",
                {
                    "error_type": error_type,
                    "error_message": error_message[:200],
                    "limit": top_k,
                },
            )

            return [
                {
                    "content": f"Error: {row.get('error_type', '')} - {row.get('message', '')}\n"
                               f"Resolution: {row.get('skill_name', '')} - {row.get('skill_code', '')}",
                    "source_file": "error_resolution",
                    "score": min(1.0, float(row.get("frequency", 1)) / 10.0),
                    "engine": "neo4j",
                    "error_type": row.get("error_type", ""),
                    "skill_name": row.get("skill_name", ""),
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Error resolution search failed: {e}")
            return []

    def expand_context(self, chunk_id: str, window: int = 2) -> list[dict]:
        """Expande contexto buscando chunks adjacentes via NEXT_CHUNK."""
        try:
            # Busca chunks anteriores e posteriores
            rows = self._graph.execute_read(
                "MATCH path = (start:Chunk {id: $chunk_id})-[:NEXT_CHUNK*0.." + str(window) + "]->(following:Chunk) "
                "RETURN following.id AS id, following.content AS content, "
                "       following.source_file AS source_file, following.chunk_index AS chunk_index "
                "UNION "
                "MATCH path = (preceding:Chunk)-[:NEXT_CHUNK*1.." + str(window) + "]->(end:Chunk {id: $chunk_id}) "
                "RETURN preceding.id AS id, preceding.content AS content, "
                "       preceding.source_file AS source_file, preceding.chunk_index AS chunk_index",
                {"chunk_id": chunk_id},
            )

            return [
                {
                    "content": row.get("content", ""),
                    "source_file": row.get("source_file", ""),
                    "chunk_index": row.get("chunk_index", 0),
                    "engine": "neo4j_context",
                }
                for row in rows
            ]
        except Exception as e:
            logger.warning(f"Context expansion failed for {chunk_id}: {e}")
            return []

    @staticmethod
    def _escape_lucene(query: str) -> str:
        """Escapa caracteres especiais do Lucene query parser."""
        special = ['+', '-', '&&', '||', '!', '(', ')', '{', '}', '[', ']', '^', '"', '~', '*', '?', ':', '\\', '/']
        result = query
        for char in special:
            result = result.replace(char, f'\\{char}')
        return result or "*"
