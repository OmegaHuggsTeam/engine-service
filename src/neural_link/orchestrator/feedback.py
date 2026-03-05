"""
FeedbackLoop - Registra outcomes, extrai conceitos, atualiza scores.

Cada interacao enriquece o grafo com:
1. Conceitos extraidos da query + resposta
2. Relationships entre conceitos
3. Agent success rate updates
4. Error pattern learning
"""

import hashlib
import logging
import uuid
from datetime import datetime

from .models import Task, TaskResult

logger = logging.getLogger(__name__)


class FeedbackLoop:
    """Enriquece o grafo de conhecimento apos cada interacao."""

    def __init__(self, graph_manager):
        self._graph = graph_manager

    def process_interaction(
        self,
        query: str,
        answer: str,
        tasks: list[Task],
        results: list[TaskResult],
        rag_results: list[dict],
    ) -> dict:
        """
        Processa uma interacao completa e enriquece o grafo.

        Returns:
            dict com metricas de enriquecimento
        """
        enrichment = {
            "nodes_added": 0,
            "relationships_added": 0,
            "concepts_extracted": 0,
            "agents_updated": 0,
        }

        # 1. Extrair conceitos da query + resposta
        concepts = self._extract_and_store_concepts(query, answer, enrichment)

        # 2. Linkar conceitos entre si
        self._link_concepts(concepts, enrichment)

        # 3. Linkar chunks usados aos conceitos
        self._link_chunks_to_concepts(rag_results, concepts, enrichment)

        # 4. Atualizar agent success rates
        self._update_agent_performance(tasks, results, enrichment)

        logger.info(
            f"Feedback: +{enrichment['nodes_added']} nodes, "
            f"+{enrichment['relationships_added']} rels, "
            f"{enrichment['concepts_extracted']} concepts"
        )

        return enrichment

    def _extract_and_store_concepts(
        self, query: str, answer: str, enrichment: dict
    ) -> list[dict]:
        """Extrai conceitos e armazena no grafo."""
        try:
            from ..rag.concept_extractor import extract_concepts, get_known_concept_names

            known = get_known_concept_names(self._graph)
            combined_text = f"{query}\n{answer[:500]}"
            concepts = extract_concepts(combined_text, known_concepts=known)

            for concept in concepts:
                concept_id = f"concept_{hashlib.md5(concept['name'].lower().encode()).hexdigest()[:12]}"

                self._graph.execute_write(
                    "MERGE (c:Concept {id: $id}) "
                    "SET c.name = $name, "
                    "    c.domain = coalesce($domain, c.domain, 'general'), "
                    "    c.confidence = CASE WHEN c.confidence IS NULL THEN $confidence "
                    "                        ELSE (c.confidence + $confidence) / 2.0 END, "
                    "    c.source = coalesce(c.source, $source), "
                    "    c.last_accessed = datetime()",
                    {
                        "id": concept_id,
                        "name": concept["name"],
                        "domain": concept.get("domain", "general"),
                        "confidence": concept.get("confidence", 0.7),
                        "source": concept.get("source", "extracted"),
                    },
                )
                concept["id"] = concept_id
                enrichment["nodes_added"] += 1

            enrichment["concepts_extracted"] = len(concepts)
            return concepts

        except Exception as e:
            logger.warning(f"Concept extraction failed: {e}")
            return []

    def _link_concepts(self, concepts: list[dict], enrichment: dict):
        """Cria RELATED_TO edges entre conceitos co-ocorrentes."""
        if len(concepts) < 2:
            return

        try:
            from ..rag.concept_linker import ConceptLinker
            linker = ConceptLinker(self._graph)
            rels = linker.link_cooccurring(concepts)
            enrichment["relationships_added"] += rels
        except ImportError:
            # ConceptLinker nao disponivel: linking basico por co-ocorrencia
            for i, c1 in enumerate(concepts):
                for c2 in concepts[i + 1:]:
                    if c1.get("id") and c2.get("id"):
                        try:
                            self._graph.execute_write(
                                "MATCH (a:Concept {id: $id1}), (b:Concept {id: $id2}) "
                                "MERGE (a)-[r:RELATED_TO]->(b) "
                                "SET r.weight = coalesce(r.weight, 0) + 0.1, "
                                "    r.type = 'co_occurrence'",
                                {"id1": c1["id"], "id2": c2["id"]},
                            )
                            enrichment["relationships_added"] += 1
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Concept linking failed: {e}")

    def _link_chunks_to_concepts(
        self, rag_results: list[dict], concepts: list[dict], enrichment: dict
    ):
        """Cria MENTIONS edges de chunks para conceitos."""
        if not rag_results or not concepts:
            return

        try:
            for result in rag_results[:5]:
                content = result.get("content", "").lower()
                source = result.get("source_file", "")
                chunk_id = f"{source}_{hash(content[:100]) % 10**8}"

                for concept in concepts:
                    if concept["name"].lower() in content:
                        try:
                            self._graph.execute_write(
                                "MATCH (ch:Chunk {id: $chunk_id}) "
                                "MATCH (co:Concept {id: $concept_id}) "
                                "MERGE (ch)-[r:MENTIONS]->(co) "
                                "SET r.confidence = coalesce(r.confidence, 0.5)",
                                {
                                    "chunk_id": chunk_id,
                                    "concept_id": concept.get("id", ""),
                                },
                            )
                            enrichment["relationships_added"] += 1
                        except Exception:
                            pass
        except Exception as e:
            logger.warning(f"Chunk-concept linking failed: {e}")

    def _update_agent_performance(
        self, tasks: list[Task], results: list[TaskResult], enrichment: dict
    ):
        """Atualiza success rate dos agentes (rolling average)."""
        agent_outcomes: dict[str, list[bool]] = {}

        for task, result in zip(tasks, results):
            agent_id = result.agent_used
            if agent_id:
                if agent_id not in agent_outcomes:
                    agent_outcomes[agent_id] = []
                agent_outcomes[agent_id].append(result.success)

        for agent_id, outcomes in agent_outcomes.items():
            try:
                # Buscar success rate atual
                rows = self._graph.execute_read(
                    "MATCH (a:Agent {id: $id}) RETURN a.success_rate AS rate, a.task_count AS task_count",
                    {"id": agent_id},
                )

                current_rate = float(rows[0]["rate"]) if rows and rows[0].get("rate") is not None else 0.8
                session_rate = sum(outcomes) / len(outcomes)

                # Rolling average: 80% historico + 20% novo
                new_rate = current_rate * 0.8 + session_rate * 0.2

                # MERGE: create Agent node if not exists, persist success_rate to Neo4j
                self._graph.execute_write(
                    "MERGE (a:Agent {id: $agent_id}) "
                    "SET a.success_rate = $rate, "
                    "    a.task_count = coalesce(a.task_count, 0) + 1, "
                    "    a.updated_at = datetime()",
                    {"agent_id": agent_id, "rate": new_rate},
                )
                enrichment["agents_updated"] += 1

            except Exception as e:
                logger.debug(f"Agent performance update failed for {agent_id}: {e}")
