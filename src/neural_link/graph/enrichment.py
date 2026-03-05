"""
Batch enrichment operations para o grafo.
Operacoes periodicas de manutencao e enriquecimento.
"""

import logging
from datetime import datetime

from .manager import GraphManager

logger = logging.getLogger(__name__)


def decay_concept_confidence(
    graph: GraphManager | None = None,
    days_threshold: int = 30,
    decay_factor: float = 0.95,
) -> int:
    """
    Decai confidence de conceitos nao acessados recentemente.
    Conceitos nao acessados por days_threshold+ dias decaem decay_factor por execucao.

    Returns:
        Numero de conceitos afetados
    """
    if graph is None:
        graph = GraphManager.from_env()

    try:
        result = graph.execute_write(
            "MATCH (c:Concept) "
            "WHERE c.confidence > 0.1 "
            "  AND (c.last_accessed IS NULL OR "
            "       c.last_accessed < datetime() - duration({days: $days})) "
            "SET c.confidence = c.confidence * $factor "
            "RETURN count(c) AS decayed",
            {"days": days_threshold, "factor": decay_factor},
        )
        count = result[0]["decayed"] if result else 0
        logger.info(f"Confidence decay: {count} concepts affected")
        return count
    except Exception as e:
        logger.warning(f"Confidence decay failed: {e}")
        return 0


def flag_underperforming_agents(
    graph: GraphManager | None = None,
    threshold: float = 0.5,
) -> list[str]:
    """
    Flag agentes com success_rate abaixo do threshold.

    Returns:
        Lista de agent_ids flagged
    """
    if graph is None:
        graph = GraphManager.from_env()

    try:
        result = graph.execute_write(
            "MATCH (a:Agent) "
            "WHERE a.success_rate < $threshold AND a.status = 'active' "
            "SET a.status = 'underperforming' "
            "RETURN a.id AS id, a.name AS name, a.success_rate AS rate",
            {"threshold": threshold},
        )
        flagged = [r["id"] for r in result]
        if flagged:
            logger.warning(f"Underperforming agents flagged: {flagged}")
        return flagged
    except Exception as e:
        logger.warning(f"Agent flagging failed: {e}")
        return []


def group_similar_errors(graph: GraphManager | None = None) -> int:
    """
    Agrupa erros similares criando SIMILAR_TO edges.
    Usa similaridade de error_type e message.

    Returns:
        Numero de novas SIMILAR_TO relationships
    """
    if graph is None:
        graph = GraphManager.from_env()

    try:
        result = graph.execute_write(
            "MATCH (e1:Error), (e2:Error) "
            "WHERE e1.id < e2.id "
            "  AND (e1.error_type = e2.error_type OR e1.library = e2.library) "
            "  AND NOT (e1)-[:SIMILAR_TO]-(e2) "
            "WITH e1, e2 LIMIT 50 "
            "CREATE (e1)-[r:SIMILAR_TO]->(e2) "
            "RETURN count(r) AS created",
        )
        count = result[0]["created"] if result else 0
        logger.info(f"Similar errors grouped: {count} new relationships")
        return count
    except Exception as e:
        logger.warning(f"Error grouping failed: {e}")
        return 0


def propagate_error_resolutions(graph: GraphManager | None = None) -> int:
    """
    Propaga resolucoes de erros para erros similares nao resolvidos.

    Returns:
        Numero de resolucoes propagadas
    """
    if graph is None:
        graph = GraphManager.from_env()

    try:
        result = graph.execute_write(
            "MATCH (resolved:Error {resolved: true})-[:RESOLVED_BY]->(skill:Skill) "
            "MATCH (resolved)-[:SIMILAR_TO]-(unresolved:Error {resolved: false}) "
            "WHERE NOT (unresolved)-[:RESOLVED_BY]->() "
            "WITH unresolved, skill LIMIT 20 "
            "CREATE (unresolved)-[:RESOLVED_BY]->(skill) "
            "SET unresolved.resolved = true "
            "RETURN count(unresolved) AS propagated",
        )
        count = result[0]["propagated"] if result else 0
        logger.info(f"Error resolutions propagated: {count}")
        return count
    except Exception as e:
        logger.warning(f"Resolution propagation failed: {e}")
        return 0


def get_enrichment_stats(graph: GraphManager | None = None) -> dict:
    """Retorna estatisticas de enriquecimento do grafo."""
    if graph is None:
        graph = GraphManager.from_env()

    try:
        stats = {}

        # Contagem por tipo de node
        node_counts = graph.execute_read(
            "MATCH (n) "
            "WITH labels(n) AS lbls, count(n) AS cnt "
            "UNWIND lbls AS label "
            "RETURN label, sum(cnt) AS count ORDER BY count DESC"
        )
        stats["nodes"] = {r["label"]: r["count"] for r in node_counts}

        # Contagem de relationships
        rel_counts = graph.execute_read(
            "MATCH ()-[r]->() "
            "RETURN type(r) AS type, count(r) AS count ORDER BY count DESC"
        )
        stats["relationships"] = {r["type"]: r["count"] for r in rel_counts}

        # Conceitos com maior confidence
        top_concepts = graph.execute_read(
            "MATCH (c:Concept) "
            "RETURN c.name AS name, c.confidence AS confidence, c.domain AS domain "
            "ORDER BY c.confidence DESC LIMIT 10"
        )
        stats["top_concepts"] = [dict(r) for r in top_concepts]

        return stats

    except Exception as e:
        logger.warning(f"Stats query failed: {e}")
        return {"error": str(e)}


def run_maintenance(graph: GraphManager | None = None) -> dict:
    """Executa todas as operacoes de manutencao."""
    if graph is None:
        graph = GraphManager.from_env()

    return {
        "decayed_concepts": decay_concept_confidence(graph),
        "flagged_agents": flag_underperforming_agents(graph),
        "grouped_errors": group_similar_errors(graph),
        "propagated_resolutions": propagate_error_resolutions(graph),
        "stats": get_enrichment_stats(graph),
    }
