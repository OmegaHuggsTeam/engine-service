"""
ConceptLinker - Descobre e cria relacoes entre conceitos no grafo.
Usa co-ocorrencia e similaridade para criar RELATED_TO edges.
"""

import logging

logger = logging.getLogger(__name__)


class ConceptLinker:
    """Descobre e cria relacoes entre conceitos."""

    def __init__(self, graph_manager):
        self._graph = graph_manager

    def link_cooccurring(self, concepts: list[dict]) -> int:
        """
        Cria RELATED_TO edges entre conceitos que co-ocorrem.
        Incrementa weight em edges existentes.

        Returns:
            Numero de relationships criadas/atualizadas
        """
        if len(concepts) < 2:
            return 0

        count = 0
        for i, c1 in enumerate(concepts):
            for c2 in concepts[i + 1:]:
                id1 = c1.get("id")
                id2 = c2.get("id")
                if not id1 or not id2 or id1 == id2:
                    continue

                try:
                    self._graph.execute_write(
                        "MATCH (a:Concept {id: $id1}), (b:Concept {id: $id2}) "
                        "MERGE (a)-[r:RELATED_TO]->(b) "
                        "SET r.weight = coalesce(r.weight, 0) + 0.1, "
                        "    r.type = coalesce(r.type, 'co_occurrence')",
                        {"id1": id1, "id2": id2},
                    )
                    count += 1
                except Exception as e:
                    logger.debug(f"Failed to link {id1} -> {id2}: {e}")

        return count

    def link_by_domain(self) -> int:
        """
        Cria RELATED_TO edges entre conceitos do mesmo dominio.
        Executar periodicamente como batch operation.

        Returns:
            Numero de novas relationships
        """
        try:
            result = self._graph.execute_write(
                "MATCH (a:Concept), (b:Concept) "
                "WHERE a.domain = b.domain AND a.id < b.id "
                "  AND NOT (a)-[:RELATED_TO]-(b) "
                "  AND a.domain IS NOT NULL AND a.domain <> 'general' "
                "WITH a, b LIMIT 100 "
                "CREATE (a)-[r:RELATED_TO {weight: 0.2, type: 'same_domain'}]->(b) "
                "RETURN count(r) AS created",
            )
            return result[0]["created"] if result else 0
        except Exception as e:
            logger.warning(f"Domain linking failed: {e}")
            return 0

    def find_similar_concepts(self, concept_id: str, limit: int = 5) -> list[dict]:
        """Encontra conceitos similares baseado em vizinhanca no grafo."""
        try:
            rows = self._graph.execute_read(
                "MATCH (c:Concept {id: $id})-[:RELATED_TO*1..2]-(similar:Concept) "
                "WHERE similar.id <> $id "
                "RETURN DISTINCT similar.id AS id, similar.name AS name, "
                "       similar.domain AS domain, similar.confidence AS confidence "
                "LIMIT $limit",
                {"id": concept_id, "limit": limit},
            )
            return [dict(r) for r in rows]
        except Exception as e:
            logger.warning(f"Similar concept search failed: {e}")
            return []
